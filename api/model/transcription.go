package model

import (
	"gorm.io/gorm"
)

type Transcription struct {
	GormModel
	MessageID string `gorm:"uniqueIndex"`
	Text      string
	Message   Message `gorm:"foreignKey:MessageID"`
}