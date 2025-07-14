package config

import (
	"log"
	"os"
	"os/user"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

type Environment = uint

const (
	Development Environment = iota
	Production
)

type Config struct {
	Environment        string
	DatabaseURL        string
	RedisAddr          string
	RedisPassword      string
	Port               string
	HistorySync        bool
	MaxMessageSync     int
	WebhookURL         string
	ExcludedSenderJIDs []string
	ChatTriggers       []ChatTriggerConfig
	RootDir            string
	StoragePath        string
	HistorySyncQueueName string
}

type ChatTriggerConfig struct {
	ChatID string `yaml:"chat_id"`
	Script string `yaml:"script"`
}

func Load() Config {
	storagePathEnv := os.Getenv("STORAGE_PATH")
	webhookURLEnv := os.Getenv("WEBHOOK_URL")
	databaseURLEnv := os.Getenv("DATABASE_PATH")
	redisAddrEnv := os.Getenv("REDIS_ADDR")
	redisPasswordEnv := os.Getenv("REDIS_PASSWORD")
	portEnv := os.Getenv("PORT")
	historySyncEnv := os.Getenv("HISTORY_SYNC")
	maxMessageSyncEnv := os.Getenv("MAX_MESSAGE_SYNC")

	usr, err := user.Current()
	if err != nil {
		log.Fatalf("Failed to get current user: %v", err)
	}
	homeDir := usr.HomeDir

	// Expand tilde for paths
	storagePathEnv = strings.Replace(storagePathEnv, "~", homeDir, 1)
	databaseURLEnv = strings.Replace(databaseURLEnv, "~", homeDir, 1)

	maxMessageSync, err := strconv.Atoi(maxMessageSyncEnv)
	if err != nil {
		maxMessageSync = 10
	}

	historySync, err := strconv.ParseBool(historySyncEnv)
	if err != nil {
		log.Fatal(err)
	}

	// Load chat triggers
	chatTriggersData, err := os.ReadFile("config/chat_triggers.yaml")
	if err != nil {
		log.Printf("Warning: Could not read chat_triggers.yaml: %v. Proceeding without chat triggers.", err)
	}

	var fullChatConfig struct {
		ExcludedJIDs []string            `yaml:"excluded_sender_jids"`
		Triggers     []ChatTriggerConfig `yaml:"chat_triggers"`
	}

	if chatTriggersData != nil {
		err = yaml.Unmarshal(chatTriggersData, &fullChatConfig)
		if err != nil {
			log.Fatalf("Failed to unmarshal chat_triggers.yaml: %v", err)
		}
	}

	return Config{
		Environment:        string(getEnvironment()),
		DatabaseURL:        databaseURLEnv,
		RedisAddr:          redisAddrEnv,
		RedisPassword:      redisPasswordEnv,
		Port:               portEnv,
		HistorySync:        historySync,
		MaxMessageSync:     maxMessageSync,
		WebhookURL:         webhookURLEnv,
		ExcludedSenderJIDs: fullChatConfig.ExcludedJIDs,
		ChatTriggers:       fullChatConfig.Triggers,
		RootDir:            ".",
		StoragePath:        storagePathEnv,
	}
}

func getEnvironment() Environment {
	env := os.Getenv("ENVIRONMENT")
	if env == "production" {
		return Production
	}
	return Development
}
