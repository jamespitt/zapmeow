package repository

import (
	"zapmeow/api/model"
	"zapmeow/pkg/database"
)

type TranscriptionRepository interface {
	CreateTranscription(transcription *model.Transcription) error
}

type transcriptionRepository struct {
	db database.Database
}

func NewTranscriptionRepository(db database.Database) *transcriptionRepository {
	return &transcriptionRepository{
		db: db,
	}
}

func (r *transcriptionRepository) CreateTranscription(transcription *model.Transcription) error {
	return r.db.Client().Create(transcription).Error
}
