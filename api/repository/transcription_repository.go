package repository

import (
	"zapmeow/api/model"
	"zapmeow/pkg/database"
)

type TranscriptionRepository interface {
	CreateTranscription(t *model.Transcription) error
	UpdateTranscription(id uint, updates map[string]interface{}) error
}

type transcriptionRepository struct {
	database database.Database
}

func NewTranscriptionRepository(database database.Database) *transcriptionRepository {
	return &transcriptionRepository{database: database}
}

func (r *transcriptionRepository) CreateTranscription(t *model.Transcription) error {
	return r.database.Client().Create(t).Error
}

func (r *transcriptionRepository) UpdateTranscription(id uint, updates map[string]interface{}) error {
	return r.database.Client().Model(&model.Transcription{}).Where("id = ?", id).Updates(updates).Error
}
