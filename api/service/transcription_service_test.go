package service_test

import (
	"errors"
	"testing"
	"zapmeow/api/model"
	"zapmeow/api/service"
)

// mockTranscriptionRepository records calls for assertion.
type mockTranscriptionRepository struct {
	created []*model.Transcription
	updated []transcriptionRepoUpdate
	createErr error
	updateErr error
}

type transcriptionRepoUpdate struct {
	ID      uint
	Updates map[string]interface{}
}

func (m *mockTranscriptionRepository) CreateTranscription(t *model.Transcription) error {
	if m.createErr != nil {
		return m.createErr
	}
	t.ID = 99
	m.created = append(m.created, t)
	return nil
}

func (m *mockTranscriptionRepository) UpdateTranscription(id uint, updates map[string]interface{}) error {
	if m.updateErr != nil {
		return m.updateErr
	}
	m.updated = append(m.updated, transcriptionRepoUpdate{id, updates})
	return nil
}

func TestTranscriptionService_CreateTranscription(t *testing.T) {
	repo := &mockTranscriptionRepository{}
	svc := service.NewTranscriptionService(repo)

	tr := &model.Transcription{MessageID: "msg_1", InstanceID: "inst_1", Status: "pending"}
	if err := svc.CreateTranscription(tr); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(repo.created) != 1 {
		t.Fatalf("expected 1 created record, got %d", len(repo.created))
	}
	if repo.created[0].MessageID != "msg_1" {
		t.Errorf("MessageID = %q, want %q", repo.created[0].MessageID, "msg_1")
	}
	if tr.ID != 99 {
		t.Errorf("ID not set by repo; got %d, want 99", tr.ID)
	}
}

func TestTranscriptionService_CreateTranscription_PropagatesError(t *testing.T) {
	repo := &mockTranscriptionRepository{createErr: errors.New("db error")}
	svc := service.NewTranscriptionService(repo)

	err := svc.CreateTranscription(&model.Transcription{})
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestTranscriptionService_UpdateTranscription(t *testing.T) {
	repo := &mockTranscriptionRepository{}
	svc := service.NewTranscriptionService(repo)

	updates := map[string]interface{}{"Status": "done", "TranscribedText": "hello"}
	if err := svc.UpdateTranscription(99, updates); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(repo.updated) != 1 {
		t.Fatalf("expected 1 update, got %d", len(repo.updated))
	}
	if repo.updated[0].ID != 99 {
		t.Errorf("ID = %d, want 99", repo.updated[0].ID)
	}
	if repo.updated[0].Updates["Status"] != "done" {
		t.Errorf("Status = %q, want \"done\"", repo.updated[0].Updates["Status"])
	}
}

func TestTranscriptionService_UpdateTranscription_PropagatesError(t *testing.T) {
	repo := &mockTranscriptionRepository{updateErr: errors.New("db error")}
	svc := service.NewTranscriptionService(repo)

	err := svc.UpdateTranscription(1, map[string]interface{}{})
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}
