package repository

import (
	"zapmeow/api/model"
	"zapmeow/pkg/database"
)

type TranscriptionRepository interface {
	CreateTranscription(transcription *model.Transcription) error
	FindByMessageID(messageID string) (*model.Transcription, error)
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

func (r *transcriptionRepository) FindByMessageID(messageID string) (*model.Transcription, error) {
	var transcription model.Transcription
	result := r.db.Client().Where("message_id = ?", messageID).First(&transcription)
	if result.Error != nil {
		if result.Error.Error() == "record not found" {
			return nil, nil // Return nil transcription and nil error if not found
		}
		return nil, result.Error // Return error if something else went wrong
	}
	return &transcription, nil
}

func (r *transcriptionRepository) FindByMessageID(messageID string) (*model.Transcription, error) {
	var transcription model.Transcription
	result := r.db.Client().Where("message_id = ?", messageID).First(&transcription)
	if result.Error != nil {
		if result.Error.Error() == "record not found" {
			return nil, nil // Return nil transcription and nil error if not found
		}
		return nil, result.Error // Return error if something else went wrong
	}
	return &transcription, nil
}
