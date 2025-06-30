package database

import (
	"zapmeow/api/model"
	"zapmeow/pkg/logger"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	gormLogger "gorm.io/gorm/logger"
)

type Database interface {
	RunMigrate(dst ...interface{}) error
	Client() *gorm.DB
}

type database struct {
	client *gorm.DB
}

func NewDatabase(databasePath string) *database {
	client, err := gorm.Open(sqlite.Open(databasePath), &gorm.Config{
		Logger: gormLogger.Default.LogMode(gormLogger.Silent),
	})
	if err != nil {
		logger.Fatal("Error creating gorm database. ", err)
	}

	return &database{
		client: client,
	}
}

func (d *database) RunMigrate(dst ...interface{}) error {
	// Add the Transcription model to the auto-migration
	modelsToMigrate := []interface{}{
		&model.Account{},
		&model.Message{},
		&model.Transcription{},
		&model.Group{},
	}
	// Append any additional models passed in dst
	modelsToMigrate = append(modelsToMigrate, dst...)
	return d.client.AutoMigrate(modelsToMigrate...)
}

func (d *database) Client() *gorm.DB {
	return d.client
}
