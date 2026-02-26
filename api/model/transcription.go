package model

import "gorm.io/gorm"

type Transcription struct {
	gorm.Model
	MessageID       string `gorm:"column:message_id;index"`
	InstanceID      string `gorm:"column:instance_id"`
	Text string `gorm:"column:text"`
	Status          string `gorm:"column:status"` // pending, done, failed
}
