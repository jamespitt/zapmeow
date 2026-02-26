package worker

import (
	"encoding/json"
	"os"
	"testing"
	"zapmeow/api/model"
	"zapmeow/api/queue"
	"zapmeow/config"
	"zapmeow/pkg/logger"
	"zapmeow/pkg/zapmeow"
)

func TestMain(m *testing.M) {
	os.Setenv("STORAGE_PATH", "/tmp/zapmeow_test_storage")
	os.Setenv("WEBHOOK_URL", "")
	os.Setenv("DATABASE_PATH", "/tmp/zapmeow_test_db.sqlite")
	os.Setenv("REDIS_ADDR", "localhost:6379")
	os.Setenv("REDIS_PASSWORD", "")
	os.Setenv("PORT", "8081")
	os.Setenv("HISTORY_SYNC", "false")
	os.Setenv("MAX_MESSAGE_SYNC", "5")
	os.Setenv("ENVIRONMENT", "development")

	// logger.Init calls config.Load which reads chat_triggers.yaml relative to cwd
	os.MkdirAll("config", 0755)
	os.WriteFile("config/chat_triggers.yaml", []byte("chat_triggers: []\n"), 0644)
	defer os.RemoveAll("config")

	logger.Init()
	os.Exit(m.Run())
}

// mockTranscriptionService records calls for assertion.
type mockTranscriptionService struct {
	Created []*model.Transcription
	Updated []transcriptionUpdate
}

type transcriptionUpdate struct {
	ID      uint
	Updates map[string]interface{}
}

func (m *mockTranscriptionService) CreateTranscription(t *model.Transcription) error {
	t.ID = 42 // give it a predictable fake ID
	m.Created = append(m.Created, t)
	return nil
}

func (m *mockTranscriptionService) UpdateTranscription(id uint, updates map[string]interface{}) error {
	m.Updated = append(m.Updated, transcriptionUpdate{id, updates})
	return nil
}

// mockQueue implements pkg/queue.Queue in-memory.
type mockQueue struct {
	items [][]byte
}

func (m *mockQueue) Enqueue(_ string, data []byte) error {
	m.items = append(m.items, data)
	return nil
}

func (m *mockQueue) Dequeue(_ string) ([]byte, error) {
	if len(m.items) == 0 {
		return nil, nil
	}
	data := m.items[0]
	m.items = m.items[1:]
	return data, nil
}

func newTestWorker(mq *mockQueue, svc *mockTranscriptionService) (*transcriptionWorker, queue.TranscriptionQueue) {
	app := &zapmeow.ZapMeow{
		Queue: mq,
		Config: config.Config{
			TranscriptionQueueName: "transcription",
			WebhookURLs:            []string{},
		},
	}
	w := NewTranscriptionWorker(app, svc)
	q := queue.NewTranscriptionQueue(app)
	return w, q
}

// --- parseWhisperOutput ---

func TestParseWhisperOutput(t *testing.T) {
	w := &transcriptionWorker{}

	tests := []struct {
		name   string
		input  string
		expect string
	}{
		{
			name:   "single segment",
			input:  "[00:00:00.000 --> 00:00:05.000]   Hello, world.",
			expect: "Hello, world.",
		},
		{
			name:   "multiple segments are joined with a space",
			input:  "[00:00:00.000 --> 00:00:02.000]   First part.\n[00:00:02.000 --> 00:00:05.000]   Second part.",
			expect: "First part. Second part.",
		},
		{
			name:   "non-timestamp lines are ignored",
			input:  "whisper_init: loading model\n[00:00:00.000 --> 00:00:03.000]   Actual text.\nsome debug line",
			expect: "Actual text.",
		},
		{
			name:   "empty output returns empty string",
			input:  "",
			expect: "",
		},
		{
			name:   "only debug lines returns empty string",
			input:  "loading model...\ncomputing...",
			expect: "",
		},
		{
			name:   "leading and trailing whitespace inside segment is stripped",
			input:  "[00:00:00.000 --> 00:00:02.000]     padded text   ",
			expect: "padded text",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := w.parseWhisperOutput(tt.input)
			if got != tt.expect {
				t.Errorf("got %q, want %q", got, tt.expect)
			}
		})
	}
}

// --- processTranscription ---

func TestProcessTranscription_EmptyQueue(t *testing.T) {
	mq := &mockQueue{}
	svc := &mockTranscriptionService{}
	w, q := newTestWorker(mq, svc)

	if err := w.processTranscription(q); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(svc.Created) != 0 {
		t.Error("expected no transcriptions created for an empty queue")
	}
}

func TestProcessTranscription_CreatesRecordAndMarksFailedWhenNoBinary(t *testing.T) {
	mq := &mockQueue{}
	svc := &mockTranscriptionService{}
	w, q := newTestWorker(mq, svc)

	// WhisperCLIPath is empty so exec.Command will fail
	jobData, _ := json.Marshal(queue.TranscriptionQueueData{
		MessageID:  "msg_abc",
		InstanceID: "inst_1",
		MediaPath:  "/nonexistent/audio.ogg",
	})
	mq.items = append(mq.items, jobData)

	if err := w.processTranscription(q); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(svc.Created) != 1 {
		t.Fatalf("expected 1 transcription created, got %d", len(svc.Created))
	}
	tr := svc.Created[0]
	if tr.MessageID != "msg_abc" {
		t.Errorf("MessageID = %q, want %q", tr.MessageID, "msg_abc")
	}
	if tr.Status != "pending" {
		t.Errorf("initial Status = %q, want \"pending\"", tr.Status)
	}

	if len(svc.Updated) != 1 {
		t.Fatalf("expected 1 update, got %d", len(svc.Updated))
	}
	if svc.Updated[0].ID != 42 {
		t.Errorf("update ID = %d, want 42", svc.Updated[0].ID)
	}
	if svc.Updated[0].Updates["Status"] != "failed" {
		t.Errorf("final Status = %q, want \"failed\"", svc.Updated[0].Updates["Status"])
	}
}

func TestProcessTranscription_MultipleJobsProcessedSequentially(t *testing.T) {
	mq := &mockQueue{}
	svc := &mockTranscriptionService{}
	w, q := newTestWorker(mq, svc)

	for _, id := range []string{"msg_1", "msg_2", "msg_3"} {
		data, _ := json.Marshal(queue.TranscriptionQueueData{MessageID: id, InstanceID: "inst_1"})
		mq.items = append(mq.items, data)
	}

	// processTranscription handles one job per call
	for i := 0; i < 3; i++ {
		if err := w.processTranscription(q); err != nil {
			t.Fatalf("call %d: unexpected error: %v", i, err)
		}
	}

	if len(svc.Created) != 3 {
		t.Errorf("expected 3 transcriptions created, got %d", len(svc.Created))
	}
}
