package model

import "gorm.io/gorm"

type Transcription struct {
	gorm.Model
	MessageID       string `gorm:"column:message_id;index"`
	InstanceID      string `gorm:"column:instance_id"`
	TranscribedText string `gorm:"column:transcribed_text"`
	Status          string `gorm:"column:status"` // pending, done, failed
}
