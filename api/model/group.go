package model

import (
	"gorm.io/gorm"
)

type Group struct {
	gorm.Model
	InstanceID  string
	JID         string `gorm:"uniqueIndex"`
	OwnerJID    string
	GroupName   string
	GroupTopic  string
	TopicSetBy  string
	TopicSetAt  int64
	GroupLocked bool
}
