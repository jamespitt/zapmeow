package model

import (
	"gorm.io/gorm"
)

type Transcription struct {
	gorm.Model
	MessageID string `gorm:"uniqueIndex"`
	Text      string
	Message   Message `gorm:"foreignKey:MessageID"`
}
