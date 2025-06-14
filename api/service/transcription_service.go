package service

import (
	"zapmeow/api/model"
	"zapmeow/api/repository"
)

type TranscriptionService interface {
	CreateTranscription(transcription *model.Transcription) error
	FindByMessageID(messageID string) (*model.Transcription, error)
}

type transcriptionService struct {
	transcriptionRepo repository.TranscriptionRepository
}

func NewTranscriptionService(transcriptionRepo repository.TranscriptionRepository) *transcriptionService {
	return &transcriptionService{
		transcriptionRepo: transcriptionRepo,
	}
}

func (s *transcriptionService) CreateTranscription(transcription *model.Transcription) error {
	return s.transcriptionRepo.CreateTranscription(transcription)
}

func (s *transcriptionService) FindByMessageID(messageID string) (*model.Transcription, error) {
	return s.transcriptionRepo.FindByMessageID(messageID)
}
