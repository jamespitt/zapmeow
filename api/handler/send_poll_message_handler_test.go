package handler

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
	"zapmeow/api/model"
	"zapmeow/pkg/whatsapp"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"go.mau.fi/whatsmeow/types"
)

type MockMessageService struct {
	mock.Mock
}

func (m *MockMessageService) CreateMessage(message *model.Message) error {
	args := m.Called(message)
	return args.Error(0)
}

func (m *MockMessageService) CreateMessages(messages *[]model.Message) error {
	args := m.Called(messages)
	return args.Error(0)
}

func (m *MockMessageService) GetChatMessages(instanceID string, chatJID string) (*[]model.Message, error) {
	args := m.Called(instanceID, chatJID)
	return args.Get(0).(*[]model.Message), args.Error(1)
}

func (m *MockMessageService) GetMessagesByInstanceID(instanceID string, chatJID string, limit int, before *time.Time) (*[]model.Message, error) {
	args := m.Called(instanceID, chatJID, limit, before)
	return args.Get(0).(*[]model.Message), args.Error(1)
}

func (m *MockMessageService) GetChatsByInstanceID(instanceID string) (*[]model.Message, map[string]int64, error) {
	args := m.Called(instanceID)
	return args.Get(0).(*[]model.Message), args.Get(1).(map[string]int64), args.Error(2)
}

func (m *MockMessageService) GetMessageByMessageID(instanceID string, messageID string) (*model.Message, error) {
	args := m.Called(instanceID, messageID)
	return args.Get(0).(*model.Message), args.Error(1)
}

func (m *MockMessageService) CountChatMessages(instanceID string, chatJID string) (int64, error) {
	args := m.Called(instanceID, chatJID)
	return args.Get(0).(int64), args.Error(1)
}

func (m *MockMessageService) DeleteMessagesByInstanceID(instanceID string) error {
	args := m.Called(instanceID)
	return args.Error(0)
}

func TestSendPollMessageHandler_Success(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mockWhatsAppService := new(MockWhatsAppService)
	mockMessageService := new(MockMessageService)
	h := NewSendPollMessageHandler(mockWhatsAppService, mockMessageService)

	instance := &whatsapp.Instance{ID: "inst-1"}
	phone := "1234567890"
	jid, _ := whatsapp.MakeJID(phone)
	pollName := "Favorite Color?"
	options := []string{"Red", "Blue", "Green"}
	selectableCount := 1

	mockWhatsAppService.On("GetInstance", "inst-1").Return(instance, nil)
	mockWhatsAppService.On("IsAuthenticated", instance).Return(true)
	mockWhatsAppService.On("SendPollMessage", instance, jid, pollName, selectableCount, options).Return(whatsapp.MessageResponse{
		ID:        "msg-poll-1",
		Sender:    types.JID{User: "sender"},
		Timestamp: time.Now(),
	}, nil)
	mockMessageService.On("CreateMessage", mock.AnythingOfType("*model.Message")).Return(nil)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Params = gin.Params{gin.Param{Key: "instanceId", Value: "inst-1"}}

	reqBody := sendPollMessageBody{
		Phone:                 phone,
		Name:                  pollName,
		Options:               options,
		SelectableOptionCount: &selectableCount,
	}
	jsonBytes, _ := json.Marshal(reqBody)
	c.Request, _ = http.NewRequest(http.MethodPost, "/api/inst-1/chat/send/poll", bytes.NewBuffer(jsonBytes))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Handler(c)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestSendPollMessageHandler_Unauthenticated(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mockWhatsAppService := new(MockWhatsAppService)
	mockMessageService := new(MockMessageService)
	h := NewSendPollMessageHandler(mockWhatsAppService, mockMessageService)

	instance := &whatsapp.Instance{ID: "inst-1"}
	mockWhatsAppService.On("GetInstance", "inst-1").Return(instance, nil)
	mockWhatsAppService.On("IsAuthenticated", instance).Return(false)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Params = gin.Params{gin.Param{Key: "instanceId", Value: "inst-1"}}

	reqBody := sendPollMessageBody{
		Phone:   "1234567890",
		Name:    "Test Poll",
		Options: []string{"A", "B"},
	}
	jsonBytes, _ := json.Marshal(reqBody)
	c.Request, _ = http.NewRequest(http.MethodPost, "/api/inst-1/chat/send/poll", bytes.NewBuffer(jsonBytes))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Handler(c)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestSendPollMessageHandler_InvalidOptions(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mockWhatsAppService := new(MockWhatsAppService)
	mockMessageService := new(MockMessageService)
	h := NewSendPollMessageHandler(mockWhatsAppService, mockMessageService)

	instance := &whatsapp.Instance{ID: "inst-1"}
	mockWhatsAppService.On("GetInstance", "inst-1").Return(instance, nil)
	mockWhatsAppService.On("IsAuthenticated", instance).Return(true)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Params = gin.Params{gin.Param{Key: "instanceId", Value: "inst-1"}}

	// Poll requires at least 2 options
	reqBody := sendPollMessageBody{
		Phone:   "1234567890",
		Name:    "Test Poll",
		Options: []string{"Only One Option"},
	}
	jsonBytes, _ := json.Marshal(reqBody)
	c.Request, _ = http.NewRequest(http.MethodPost, "/api/inst-1/chat/send/poll", bytes.NewBuffer(jsonBytes))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Handler(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}
