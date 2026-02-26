package service

import (
	"zapmeow/api/model"
	"zapmeow/api/repository"
)

type TranscriptionService interface {
	CreateTranscription(t *model.Transcription) error
	UpdateTranscription(id uint, updates map[string]interface{}) error
}

type transcriptionService struct {
	repo repository.TranscriptionRepository
}

func NewTranscriptionService(repo repository.TranscriptionRepository) *transcriptionService {
	return &transcriptionService{repo: repo}
}

func (s *transcriptionService) CreateTranscription(t *model.Transcription) error {
	return s.repo.CreateTranscription(t)
}

func (s *transcriptionService) UpdateTranscription(id uint, updates map[string]interface{}) error {
	return s.repo.UpdateTranscription(id, updates)
}
