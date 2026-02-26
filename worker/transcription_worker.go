package worker

import (
	"os/exec"
	"regexp"
	"strings"
	"time"
	"zapmeow/api/model"
	"zapmeow/api/queue"
	"zapmeow/api/service"
	"zapmeow/pkg/http"
	"zapmeow/pkg/logger"
	"zapmeow/pkg/zapmeow"
)

var whisperTimestampRegex = regexp.MustCompile(`^\[[\d:\.]+\s*-->\s*[\d:\.]+\]\s*(.*)$`)

type transcriptionWorker struct {
	app                  *zapmeow.ZapMeow
	transcriptionService service.TranscriptionService
}

type TranscriptionWorker interface {
	ProcessQueue()
}

func NewTranscriptionWorker(
	app *zapmeow.ZapMeow,
	transcriptionService service.TranscriptionService,
) *transcriptionWorker {
	return &transcriptionWorker{
		app:                  app,
		transcriptionService: transcriptionService,
	}
}

func (w *transcriptionWorker) ProcessQueue() {
	q := queue.NewTranscriptionQueue(w.app)
	defer w.app.Wg.Done()
	for {
		select {
		case <-*w.app.StopCh:
			return
		default:
			if err := w.processTranscription(q); err != nil {
				logger.Error("Error processing transcription. ", err)
			}
		}
		time.Sleep(3 * time.Second)
	}
}

func (w *transcriptionWorker) processTranscription(q queue.TranscriptionQueue) error {
	data, err := q.Dequeue()
	if err != nil {
		return err
	}
	if data == nil {
		return nil
	}

	t := &model.Transcription{
		MessageID:  data.MessageID,
		InstanceID: data.InstanceID,
		Status:     "pending",
	}
	if err := w.transcriptionService.CreateTranscription(t); err != nil {
		return err
	}

	text, transcribeErr := w.runWhisper(data.MediaPath)
	updates := map[string]interface{}{}
	status := "done"
	if transcribeErr != nil {
		logger.Error("Whisper transcription failed for message ", data.MessageID, ". ", transcribeErr)
		status = "failed"
	} else {
		updates["Text"] = text
	}
	updates["Status"] = status

	if err := w.transcriptionService.UpdateTranscription(t.ID, updates); err != nil {
		logger.Error("Failed to update transcription record. ", err)
	}

	w.sendWebhook(data.InstanceID, data.MessageID, text, status)
	return nil
}

func (w *transcriptionWorker) runWhisper(mediaPath string) (string, error) {
	cmd := exec.Command(
		w.app.Config.WhisperCLIPath,
		"-m", w.app.Config.WhisperModelPath,
		mediaPath,
	)
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return w.parseWhisperOutput(string(output)), nil
}

func (w *transcriptionWorker) parseWhisperOutput(output string) string {
	var segments []string
	for _, line := range strings.Split(output, "\n") {
		if m := whisperTimestampRegex.FindStringSubmatch(strings.TrimSpace(line)); m != nil {
			text := strings.TrimSpace(m[1])
			if text != "" {
				segments = append(segments, text)
			}
		}
	}
	return strings.Join(segments, " ")
}

func (w *transcriptionWorker) sendWebhook(instanceID, messageID, text, status string) {
	body := map[string]interface{}{
		"instanceId": instanceID,
		"transcription": map[string]interface{}{
			"messageId":  messageID,
			"instanceId": instanceID,
			"text":       text,
			"status":     status,
		},
	}
	for _, webhookURL := range w.app.Config.WebhookURLs {
		if err := http.Request(webhookURL, body); err != nil {
			logger.Error("Failed to send transcription webhook to ", webhookURL, ". ", err)
		}
	}
}
