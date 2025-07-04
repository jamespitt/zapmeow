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
	Environment          Environment
	StoragePath          string
	WebhookURL           string
	DatabaseURL          string
	RedisAddr            string
	RedisPassword        string
	Port                 string
	HistorySyncQueueName string
	HistorySync          bool
	MaxMessageSync       int
	ChatTriggers         []ChatTriggerConfig
	ExcludedSenderJIDs   []string `yaml:"excluded_sender_jids"`
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
	environment := getEnvironment()

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
		Environment:          environment,
		StoragePath:          storagePathEnv,
		WebhookURL:           webhookURLEnv,
		DatabaseURL:          databaseURLEnv,
		RedisAddr:            redisAddrEnv,
		RedisPassword:        redisPasswordEnv,
		Port:                 portEnv,
		HistorySyncQueueName: "queue:history-sync",
		HistorySync:          historySync,
		MaxMessageSync:       maxMessageSync,
		ChatTriggers:         fullChatConfig.Triggers,
		ExcludedSenderJIDs:   fullChatConfig.ExcludedJIDs,
	}
}

func getEnvironment() Environment {
	env := os.Getenv("ENVIRONMENT")
	if env == "production" {
		return Production
	}
	return Development
}
