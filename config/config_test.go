package config

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestLoad_ChatTriggers(t *testing.T) {
	// Create a temporary directory for the test config file
	tmpDir, err := os.MkdirTemp("", "config_test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create a temporary chat_triggers.yaml
	tmpYamlPath := filepath.Join(tmpDir, "chat_triggers.yaml")
	yamlContent := `
excluded_sender_jids:
  - "excluded1@s.whatsapp.net"
  - "excluded2@s.whatsapp.net"
chat_triggers:
  - chat_id: "chat1@s.whatsapp.net"
    script: "/scripts/script1.sh"
  - chat_id: "chat2@s.whatsapp.net"
    script: "scripts/script2.sh"
`
	if err := os.WriteFile(tmpYamlPath, []byte(yamlContent), 0644); err != nil {
		t.Fatalf("Failed to write temp chat_triggers.yaml: %v", err)
	}

	// Temporarily change current working directory to the temp dir
	// so that Load() can find config/chat_triggers.yaml relative path
	originalWd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Failed to get current working directory: %v", err)
	}
	// Create a config directory inside the temp dir to mimic the project structure
	if err := os.Mkdir(filepath.Join(tmpDir, "config"), 0755); err != nil {
		t.Fatalf("Failed to create temp config dir: %v", err)
	}
	// Move the temp yaml file into the temp config dir
	if err := os.Rename(tmpYamlPath, filepath.Join(tmpDir, "config", "chat_triggers.yaml")); err != nil {
		t.Fatalf("Failed to move temp yaml: %v", err)
	}

	if err := os.Chdir(tmpDir); err != nil {
		t.Fatalf("Failed to change working directory to temp dir: %v", err)
	}
	defer os.Chdir(originalWd) // Change back to original working directory

	// Set dummy environment variables required by Load()
	os.Setenv("STORAGE_PATH", "/tmp")
	os.Setenv("WEBHOOK_URL", "http://localhost")
	os.Setenv("DATABASE_PATH", "/tmp/db.sqlite")
	os.Setenv("REDIS_ADDR", "localhost:6379")
	os.Setenv("REDIS_PASSWORD", "")
	os.Setenv("PORT", "8080")
	os.Setenv("HISTORY_SYNC", "false")
	os.Setenv("MAX_MESSAGE_SYNC", "10")
	os.Setenv("ENVIRONMENT", "development")


	cfg := Load()

	expectedTriggers := []ChatTriggerConfig{
		{ChatID: "chat1@s.whatsapp.net", Script: "/scripts/script1.sh"},
		{ChatID: "chat2@s.whatsapp.net", Script: "scripts/script2.sh"},
	}

	expectedExcludedJIDs := []string{
		"excluded1@s.whatsapp.net",
		"excluded2@s.whatsapp.net",
	}

	if !reflect.DeepEqual(cfg.ChatTriggers, expectedTriggers) {
		t.Errorf("Load() ChatTriggers = %v, want %v", cfg.ChatTriggers, expectedTriggers)
	}

	if !reflect.DeepEqual(cfg.ExcludedSenderJIDs, expectedExcludedJIDs) {
		t.Errorf("Load() ExcludedSenderJIDs = %v, want %v", cfg.ExcludedSenderJIDs, expectedExcludedJIDs)
	}

	// Test case for when chat_triggers.yaml does not exist
	// Remove the chat_triggers.yaml file
	if err := os.Remove(filepath.Join(tmpDir, "config", "chat_triggers.yaml")); err != nil {
		t.Fatalf("Failed to remove temp chat_triggers.yaml for non-existence test: %v", err)
	}

	cfgNoFile := Load()
	if len(cfgNoFile.ChatTriggers) != 0 {
		t.Errorf("Load() ChatTriggers when file does not exist = %v, want empty slice", cfgNoFile.ChatTriggers)
	}
}
