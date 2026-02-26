package queue

import (
	"encoding/json"
	"zapmeow/pkg/logger"
	"zapmeow/pkg/zapmeow"
)

type TranscriptionQueueData struct {
	MessageID  string
	InstanceID string
	MediaPath  string
}

type transcriptionQueue struct {
	app *zapmeow.ZapMeow
}

type TranscriptionQueue interface {
	Enqueue(item TranscriptionQueueData) error
	Dequeue() (*TranscriptionQueueData, error)
}

func NewTranscriptionQueue(app *zapmeow.ZapMeow) *transcriptionQueue {
	return &transcriptionQueue{app: app}
}

func (q *transcriptionQueue) Enqueue(item TranscriptionQueueData) error {
	jsonData, err := json.Marshal(item)
	if err != nil {
		logger.Error("Error enqueue transcription. ", err)
		return err
	}
	return q.app.Queue.Enqueue(q.app.Config.TranscriptionQueueName, jsonData)
}

func (q *transcriptionQueue) Dequeue() (*TranscriptionQueueData, error) {
	result, err := q.app.Queue.Dequeue(q.app.Config.TranscriptionQueueName)
	if err != nil {
		logger.Error("Error dequeuing transcription. ", err)
		return nil, err
	}
	if result == nil {
		return nil, nil
	}

	var data TranscriptionQueueData
	if err := json.Unmarshal(result, &data); err != nil {
		logger.Error("Error unmarshal transcription. ", err)
		return nil, err
	}
	return &data, nil
}
