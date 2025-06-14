package model

import (
	"gorm.io/gorm"
)

// Transcription represents a transcription of an audio message.
type Transcription struct {
	GORMModel
	MessageID string `gorm:"uniqueIndex"` // Link to the Message table
	Text      string
}

// TableName specifies the table name for the Transcription model.
func (Transcription) TableName() string {
	return "transcriptions"
}
