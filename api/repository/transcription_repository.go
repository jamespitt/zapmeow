package repository

import (
	"zapmeow/api/model"
	"zapmeow/pkg/database"

	"gorm.io/gorm"
)

type TranscriptionRepository interface {
	CreateTranscription(transcription *model.Transcription) error
	FindByMessageID(messageID string) (*model.Transcription, error)
}

type transcriptionRepository struct {
	database database.Database
}

func NewTranscriptionRepository(database database.Database) *transcriptionRepository {
	return &transcriptionRepository{database: database}
}

func (repo *transcriptionRepository) CreateTranscription(transcription *model.Transcription) error {
	err := repo.database.Client().Create(transcription).Error
	if err != nil && err.Error() == "UNIQUE constraint failed: transcriptions.message_id" {
		return nil // Ignore unique constraint errors
	}
	return err
}

func (repo *transcriptionRepository) FindByMessageID(messageID string) (*model.Transcription, error) {
	var transcription model.Transcription
	if result := repo.database.Client().Where("message_id = ?", messageID).First(&transcription); result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil // Return nil transcription and nil error if not found
		}
		return nil, result.Error // Return error if something else went wrong
	}
	return &transcription, nil
}
