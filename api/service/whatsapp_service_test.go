package service

import (
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
	"zapmeow/api/model"
	"zapmeow/config"
	"zapmeow/pkg/logger" // Added logger import
	"zapmeow/pkg/whatsapp"
	"zapmeow/pkg/zapmeow"

	"github.com/vincent-petithory/dataurl"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	"google.golang.org/protobuf/proto"
)

// --- Mocks ---

// mockMessageService implements MessageService for testing

type mockMessageService struct {
	CreatedMessages []*model.Message
}

func (m *mockMessageService) CreateMessage(message *model.Message) error {
	m.CreatedMessages = append(m.CreatedMessages, message)
	return nil
}

func (m *mockMessageService) CreateMessages(messages *[]model.Message) error { return nil } 
func (m *mockMessageService) GetChatMessages(instanceID string, chatJID string) (*[]model.Message, error) {
	return nil, nil
} 
func (m *mockMessageService) CountChatMessages(instanceID string, chatJID string) (int64, error) {
	return 0, nil
} 
func (m *mockMessageService) DeleteMessagesByInstanceID(instanceID string) error {
	return nil
} 

// mockAccountService implements AccountService for testing
type mockAccountService struct{}

func (m *mockAccountService) CreateAccount(account *model.Account) error { return nil }
func (m *mockAccountService) GetAccountByInstanceID(id string) (*model.Account, error) {
	return nil, nil
}
func (m *mockAccountService) UpdateAccount(id string, updates map[string]interface{}) error {
	return nil
}
func (m *mockAccountService) DeleteAccountMessages(id string) error {
	return nil
}
func (m *mockAccountService) GetConnectedAccounts() ([]model.Account, error) {
	return nil, nil
}

func (m *mockAccountService) GetAllAccounts() ([]model.Account, error) {
	return nil, nil
}

type mockGroupService struct{}

func (m *mockGroupService) CreateOrUpdateGroup(instanceID string, groupInfo *model.GroupInfo) error {
	return nil
} 

// mockWhatsApp implements whatsapp.WhatsApp for testing
type mockWhatsApp struct{}

func (m *mockWhatsApp) CreateInstance(instanceID string) *whatsapp.Instance {
	return &whatsapp.Instance{ID: instanceID}
}
func (m *mockWhatsApp) CreateInstanceFromDevice(instanceID string, jid types.JID) *whatsapp.Instance {
	return &whatsapp.Instance{ID: instanceID}
}
func (m *mockWhatsApp) InitInstance(instance *whatsapp.Instance, qrCallback func(event string, code string, err error)) error {
	return nil
}
func (m *mockWhatsApp) Connect(instance *whatsapp.Instance) error    { return nil } 
func (m *mockWhatsApp) Disconnect(instance *whatsapp.Instance)       {}
func (m *mockWhatsApp) IsConnected(instance *whatsapp.Instance) bool { return true }
func (m *mockWhatsApp) IsLoggedIn(instance *whatsapp.Instance) bool  { return true }
func (m *mockWhatsApp) Logout(instance *whatsapp.Instance) error     { return nil }
func (m *mockWhatsApp) EventHandler(instance *whatsapp.Instance, handler func(evt interface{})) {} 

func (m *mockWhatsApp) SendTextMessage(instance *whatsapp.Instance, jid types.JID, text string) (whatsapp.MessageResponse, error) {
	return whatsapp.MessageResponse{}, nil
}
func (m *mockWhatsApp) SendImageMessage(instance *whatsapp.Instance, jid types.JID, imageURL *dataurl.DataURL, mimitype string) (whatsapp.MessageResponse, error) {
	return whatsapp.MessageResponse{}, nil
}
func (m *mockWhatsApp) SendAudioMessage(instance *whatsapp.Instance, jid types.JID, audioURL *dataurl.DataURL, mimitype string) (whatsapp.MessageResponse, error) {
	return whatsapp.MessageResponse{}, nil
}
func (m *mockWhatsApp) SendDocumentMessage(instance *whatsapp.Instance, jid types.JID, documentURL *dataurl.DataURL, mimitype string, filename string) (whatsapp.MessageResponse, error) {
	return whatsapp.MessageResponse{}, nil
}
func (m *mockWhatsApp) GetContactInfo(instance *whatsapp.Instance, jid types.JID) (*whatsapp.ContactInfo, error) {
	return nil, nil
}
func (m *mockWhatsApp) GetGroupInfo(instance *whatsapp.Instance, groupID string) (*types.GroupInfo, error) {
	return nil, nil
}
func (m *mockWhatsApp) GetJoinedGroups(instance *whatsapp.Instance) ([]*types.GroupInfo, error) {
	return nil, nil
}
func (m *mockWhatsApp) ParseEventMessage(instance *whatsapp.Instance, message *events.Message) (whatsapp.Message, error) {
	parsedMsg := whatsapp.Message{
		InstanceID: instance.ID,
		MessageID:  message.Info.ID,
		ChatJID:    message.Info.Chat.User,
		SenderJID:  message.Info.Sender.User,
		Timestamp:  message.Info.Timestamp, 
		FromMe:     message.Info.IsFromMe,
	}
	if message.Message != nil && message.Message.GetConversation() != "" {
		parsedMsg.Body = message.Message.GetConversation()
	} else if message.Message != nil && message.Message.GetExtendedTextMessage() != nil {
		parsedMsg.Body = message.Message.GetExtendedTextMessage().GetText()
	}

	if message.Message != nil && message.Message.AudioMessage != nil {
		mediaType := whatsapp.Audio 
		parsedMsg.MediaType = &mediaType
		dummyAudioData := []byte("dummy_audio_data")
		parsedMsg.Media = &dummyAudioData
		dummyMimetype := "audio/ogg"
		parsedMsg.Mimetype = &dummyMimetype
	}

	return parsedMsg, nil
}
func (m *mockWhatsApp) IsOnWhatsApp(instance *whatsapp.Instance, phones []string) ([]whatsapp.IsOnWhatsAppResponse, error) {
	return nil, nil
}

// --- Tests ---

func TestHandleMessage_ChatTriggers(t *testing.T) {
	// Set dummy environment variables required by config.Load() which is called by logger.Init()
	os.Setenv("STORAGE_PATH", "/tmp/zapmeow_test_storage")
	os.Setenv("WEBHOOK_URL", "http://localhost:9090/webhook")
	os.Setenv("DATABASE_PATH", "/tmp/zapmeow_test_db.sqlite")
	os.Setenv("REDIS_ADDR", "localhost:6379")
	os.Setenv("REDIS_PASSWORD", "")
	os.Setenv("PORT", "8081")
	os.Setenv("HISTORY_SYNC", "false")
	os.Setenv("MAX_MESSAGE_SYNC", "5")
	os.Setenv("ENVIRONMENT", "development")

	// Create a dummy config/chat_triggers.yaml for logger.Init() -> config.Load()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Failed to get working directory: %v", err)
	}
	dummyConfigDir := filepath.Join(wd, "config")
	if err := os.MkdirAll(dummyConfigDir, 0755); err != nil {
		t.Fatalf("Failed to create dummy config dir: %v", err)
	}
	projectRoot := filepath.Join(wd, "../..")
	testScriptRelativePath := "scripts/test_trigger_script.sh"
	testScriptAbsolutePathForConfig := filepath.Join(projectRoot, testScriptRelativePath)

	dummyChatTriggersFile := filepath.Join(dummyConfigDir, "chat_triggers.yaml")
	chatTriggersYAML := `
chat_triggers:
  - chat_id: "triggered_chat"
    script: "` + testScriptAbsolutePathForConfig + `"
  - chat_id: "another_chat"
    script: "` + filepath.Join(projectRoot, "scripts/non_existent_script.sh") + `"
`
	if err := os.WriteFile(dummyChatTriggersFile, []byte(chatTriggersYAML), 0644); err != nil {
		t.Fatalf("Failed to write dummy chat_triggers.yaml: %v", err)
	}
	defer os.RemoveAll(dummyConfigDir) // Clean up dummy config

	logger.Init() // Initialize logger

	if _, err := os.Stat(testScriptAbsolutePathForConfig); os.IsNotExist(err) {
		t.Fatalf("Test script %s does not exist. Make sure it's in the /scripts directory and executable.", testScriptAbsolutePathForConfig)
	}

	testAppConfig := config.Config{
		RootDir: projectRoot,
		ChatTriggers: []config.ChatTriggerConfig{
			{ChatID: "triggered_chat", Script: testScriptAbsolutePathForConfig},
			{ChatID: "another_chat", Script: filepath.Join(projectRoot, "scripts/non_existent_script.sh")},
		},
		ExcludedSenderJIDs: []string{"global_exclude@s.whatsapp.net", "353870985961@s.whatsapp.net"}, // Added global exclusions for test
		WebhookURL: "http://localhost:9090/webhook", // Ensure WebhookURL is set in testAppConfig
	}
	appInstances := new(sync.Map)

	appInstances.Store("test_instance_1", &whatsapp.Instance{ID: "test_instance_1"})
	appInstances.Store("test_instance_2", &whatsapp.Instance{ID: "test_instance_2"})
	appInstances.Store("test_instance_3", &whatsapp.Instance{ID: "test_instance_3"})
	appInstances.Store("test_instance_4", &whatsapp.Instance{ID: "test_instance_4"})
	appInstances.Store("test_instance_5", &whatsapp.Instance{ID: "test_instance_5"}) // Added instance for new test
	appInstances.Store("test_instance_6", &whatsapp.Instance{ID: "test_instance_6"})
	appInstances.Store("test_instance_7", &whatsapp.Instance{ID: "test_instance_7"})
	appInstances.Store("test_instance_8", &whatsapp.Instance{ID: "test_instance_8"}) // Added instance for new global exclusion test

	app := &zapmeow.ZapMeow{
		Config:    testAppConfig,
		Instances: appInstances,
	}

	mockMsgService := &mockMessageService{}
	mockAccService := &mockAccountService{}
	mockWa := &mockWhatsApp{}

	service := NewWhatsAppService(app, mockMsgService, mockAccService, &mockGroupService{}, mockWa)

	outputFilePath := "/tmp/test_trigger_output.txt"

	tests := []struct {
		name              string
		instanceID        string
		event             *events.Message
		expectScriptRun   bool
		expectedOutput    string
		expectErrorLog    bool 
		cleanupOutputFile bool
	}{
		{
			name:       "Text message for triggered chat ID",
			instanceID: "test_instance_1",
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:   types.NewJID("triggered_chat", types.DefaultUserServer),
						Sender: types.NewJID("allowed_sender", types.DefaultUserServer), // Changed to a clearly non-excluded sender
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg1", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{Conversation: proto.String("Hello trigger")},
			},
			expectScriptRun:  true,
			expectedOutput: "triggered_chat Hello trigger",
			cleanupOutputFile: true,
		},
		{
			name:       "Text message for non-triggered chat ID",
			instanceID: "test_instance_2",
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:   types.NewJID("non_triggered_chat", types.DefaultUserServer),
						Sender: types.NewJID("sender", types.DefaultUserServer), // This sender is not globally excluded by default test config
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg2", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{Conversation: proto.String("Hello normal")},
			},
			expectScriptRun: false,
			cleanupOutputFile: true,
		},
		{
			name:       "Audio message for triggered chat ID (should not trigger text script)",
			instanceID: "test_instance_3",
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:   types.NewJID("triggered_chat", types.DefaultUserServer),
						Sender: types.NewJID("sender", types.DefaultUserServer),
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg3", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{AudioMessage: &waProto.AudioMessage{Mimetype: proto.String("audio/ogg")} },
			},
			expectScriptRun: false,
			cleanupOutputFile: true,
		},
		{
			name:       "Text message for chat ID with non-existent script",
			instanceID: "test_instance_4",
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:   types.NewJID("another_chat", types.DefaultUserServer),
						Sender: types.NewJID("sender", types.DefaultUserServer),
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg4", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{Conversation: proto.String("Hello broken trigger")},
			},
			expectScriptRun: false,
			expectErrorLog:  true,
			cleanupOutputFile: true,
		},
		{
			name:       "Text message from me for triggered chat ID (should not trigger)",
			instanceID: "test_instance_5", 
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:     types.NewJID("triggered_chat", types.DefaultUserServer),
						Sender:   types.NewJID("sender", types.DefaultUserServer), // Actual sender JID doesn't matter as much when FromMe is true
						IsFromMe: true, 
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg5", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{Conversation: proto.String("Hello from me")},
			},
			expectScriptRun:   false, 
			cleanupOutputFile: true,
		},
		{
			name:       "Text message from globally excluded JID (353...) in triggered chat (should not trigger)",
			instanceID: "test_instance_6",
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:     types.NewJID("triggered_chat", types.DefaultUserServer),
						Sender:   types.NewJID("353870985961", types.DefaultUserServer), // This JID is in ExcludedSenderJIDs
						IsFromMe: false,
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg6", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{Conversation: proto.String("Hello from globally excluded JID")},
			},
			expectScriptRun:   false,
			cleanupOutputFile: true,
		},
		{
			name:       "Text message from another globally excluded JID (global_exclude@...) in triggered chat (should not trigger)",
			instanceID: "test_instance_8", // New instance ID
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:     types.NewJID("triggered_chat", types.DefaultUserServer),
						Sender:   types.NewJID("global_exclude", types.DefaultUserServer), // This JID is in ExcludedSenderJIDs
						IsFromMe: false,
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg8", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{Conversation: proto.String("Hello from another globally excluded JID")},
			},
			expectScriptRun:   false,
			cleanupOutputFile: true,
		},
		{
			name:       "Text message from allowed JID (447...) in triggered chat (should trigger)",
			instanceID: "test_instance_7",
			event: &events.Message{
				Info: func() types.MessageInfo {
					ms := types.MessageSource{
						Chat:     types.NewJID("triggered_chat", types.DefaultUserServer),
						Sender:   types.NewJID("447906616842", types.DefaultUserServer), // This JID is NOT in ExcludedSenderJIDs
						IsFromMe: false,
					}
					info := types.MessageInfo{MessageSource: ms, ID: "msg7", Timestamp: time.Now()}
					return info
				}(),
				Message: &waProto.Message{Conversation: proto.String("Hello from allowed JID")},
			},
			expectScriptRun:   true,
			expectedOutput:  "triggered_chat Hello from allowed JID",
			cleanupOutputFile: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.cleanupOutputFile || tt.expectScriptRun {
				os.Remove(outputFilePath) 
			}

			service.handleMessage(tt.instanceID, tt.event)

			if tt.expectScriptRun {
				time.Sleep(250 * time.Millisecond) 
				content, err := os.ReadFile(outputFilePath)
				if err != nil {
					t.Fatalf("Expected script to run and create output file '%s', but got error: %v", outputFilePath, err)
				}
				if strings.TrimSpace(string(content)) != tt.expectedOutput {
					t.Errorf("Script output mismatch: got '%s', want '%s'", strings.TrimSpace(string(content)), tt.expectedOutput)
				}
				if tt.cleanupOutputFile {
					os.Remove(outputFilePath)
				}
			} else {
				time.Sleep(100 * time.Millisecond)
				_, err := os.Stat(outputFilePath)
				if !os.IsNotExist(err) {
					content, _ := os.ReadFile(outputFilePath)
					if len(strings.TrimSpace(string(content))) > 0 {
						t.Errorf("Expected script not to run or output file to be empty, but found content: '%s' in %s", string(content), outputFilePath)
						if tt.cleanupOutputFile {
							os.Remove(outputFilePath)
						}
					}
				}
			}
		})
	}
}

func TestMain(m *testing.M) {
	os.Exit(m.Run())
}