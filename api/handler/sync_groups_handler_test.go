package handler

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"zapmeow/api/model"
	"zapmeow/pkg/whatsapp"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"go.mau.fi/whatsmeow/types/events"
	"github.com/vincent-petithory/dataurl"
)

type MockWhatsAppService struct {
	mock.Mock
}

func (m *MockWhatsAppService) GetInstance(instanceID string) (*whatsapp.Instance, error) {
	args := m.Called(instanceID)
	return args.Get(0).(*whatsapp.Instance), args.Error(1)
}

func (m *MockWhatsAppService) IsAuthenticated(instance *whatsapp.Instance) bool {
	args := m.Called(instance)
	return args.Bool(0)
}

func (m *MockWhatsAppService) Logout(instance *whatsapp.Instance) error {
	args := m.Called(instance)
	return args.Error(0)
}

func (m *MockWhatsAppService) SendTextMessage(instance *whatsapp.Instance, jid whatsapp.JID, text string) (whatsapp.MessageResponse, error) {
	args := m.Called(instance, jid, text)
	return args.Get(0).(whatsapp.MessageResponse), args.Error(1)
}

func (m *MockWhatsAppService) SendAudioMessage(instance *whatsapp.Instance, jid whatsapp.JID, audioURL *dataurl.DataURL, mimitype string) (whatsapp.MessageResponse, error) {
	args := m.Called(instance, jid, audioURL, mimitype)
	return args.Get(0).(whatsapp.MessageResponse), args.Error(1)
}

func (m *MockWhatsAppService) SendDocumentMessage(instance *whatsapp.Instance, jid whatsapp.JID, documentURL *dataurl.DataURL, mimitype string, filename string) (whatsapp.MessageResponse, error) {
	args := m.Called(instance, jid, documentURL, mimitype, filename)
	return args.Get(0).(whatsapp.MessageResponse), args.Error(1)
}

func (m *MockWhatsAppService) SendImageMessage(instance *whatsapp.Instance, jid whatsapp.JID, imageURL *dataurl.DataURL, mimitype string) (whatsapp.MessageResponse, error) {
	args := m.Called(instance, jid, imageURL, mimitype)
	return args.Get(0).(whatsapp.MessageResponse), args.Error(1)
}

func (m *MockWhatsAppService) GetContactInfo(instance *whatsapp.Instance, jid whatsapp.JID) (*whatsapp.ContactInfo, error) {
	args := m.Called(instance, jid)
	return args.Get(0).(*whatsapp.ContactInfo), args.Error(1)
}

func (m *MockWhatsAppService) GetGroupInfo(instance *whatsapp.Instance, groupID string) (*model.GroupInfo, error) {
	args := m.Called(instance, groupID)
	return args.Get(0).(*model.GroupInfo), args.Error(1)
}

func (m *MockWhatsAppService) SyncGroups(instance *whatsapp.Instance) ([]*model.GroupInfo, error) {
	args := m.Called(instance)
	return args.Get(0).([]*model.GroupInfo), args.Error(1)
}

func (m *MockWhatsAppService) ParseEventMessage(instance *whatsapp.Instance, message *events.Message) (whatsapp.Message, error) {
	args := m.Called(instance, message)
	return args.Get(0).(whatsapp.Message), args.Error(1)
}

func (m *MockWhatsAppService) IsOnWhatsApp(instance *whatsapp.Instance, phones []string) ([]whatsapp.IsOnWhatsAppResponse, error) {
	args := m.Called(instance, phones)
	return args.Get(0).([]whatsapp.IsOnWhatsAppResponse), args.Error(1)
}

func TestSyncGroupsHandler(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mockService := new(MockWhatsAppService)
	handler := NewSyncGroupsHandler(mockService)

	instance := &whatsapp.Instance{}
	groups := []*model.GroupInfo{
		{
			JID: "123@g.us",
		},
	}

	mockService.On("GetInstance", "1").Return(instance, nil)
	mockService.On("IsAuthenticated", instance).Return(true)
	mockService.On("SyncGroups", instance).Return(groups, nil)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Params = gin.Params{gin.Param{Key: "instanceId", Value: "1"}}

	handler.Handler(c)

	assert.Equal(t, http.StatusOK, w.Code)
	mockService.AssertCalled(t, "SyncGroups", instance)
}
