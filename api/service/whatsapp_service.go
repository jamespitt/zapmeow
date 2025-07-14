package service

import (
	"os/exec"
	"path/filepath" // Added for filepath.Base
	"strings" // Ensure strings package is imported
	"zapmeow/api/helper"
	"zapmeow/api/model"
	"zapmeow/api/queue"
	"zapmeow/api/response"
	"zapmeow/pkg/http"
	"zapmeow/pkg/logger"
	"zapmeow/pkg/whatsapp"
	"zapmeow/pkg/zapmeow"

	"github.com/vincent-petithory/dataurl"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	"google.golang.org/protobuf/proto"
)

// stripJIDSuffix removes the @server part from a JID string.
func stripJIDSuffix(jid string) string {
	if idx := strings.Index(jid, "@"); idx != -1 {
		return jid[:idx]
	}
	return jid
}

type whatsAppService struct {
	app            *zapmeow.ZapMeow
	messageService MessageService
	accountService AccountService
	groupService   GroupService
	whatsApp       whatsapp.WhatsApp
}

type WhatsAppService interface {
	GetInstance(instanceID string) (*whatsapp.Instance, error)
	IsAuthenticated(instance *whatsapp.Instance) bool
	Logout(instance *whatsapp.Instance) error
	SendTextMessage(instance *whatsapp.Instance, jid whatsapp.JID, text string) (whatsapp.MessageResponse, error)
	SendAudioMessage(instance *whatsapp.Instance, jid whatsapp.JID, audioURL *dataurl.DataURL, mimitype string) (whatsapp.MessageResponse, error)
	SendDocumentMessage(instance *whatsapp.Instance, jid whatsapp.JID, documentURL *dataurl.DataURL, mimitype string, filename string) (whatsapp.MessageResponse, error)
	SendImageMessage(instance *whatsapp.Instance, jid whatsapp.JID, imageURL *dataurl.DataURL, mimitype string) (whatsapp.MessageResponse, error)
	GetContactInfo(instance *whatsapp.Instance, jid whatsapp.JID) (*whatsapp.ContactInfo, error)
	GetGroupInfo(instance *whatsapp.Instance, groupID string) (*model.GroupInfo, error)
	SyncGroups(instance *whatsapp.Instance) ([]*model.GroupInfo, error)
	ParseEventMessage(instance *whatsapp.Instance, message *events.Message) (whatsapp.Message, error)
	IsOnWhatsApp(instance *whatsapp.Instance, phones []string) ([]whatsapp.IsOnWhatsAppResponse, error)
}

func NewWhatsAppService(
	app *zapmeow.ZapMeow,
	messageService MessageService,
	accountService AccountService,
	groupService GroupService,
	whatsApp whatsapp.WhatsApp,
) *whatsAppService {
	return &whatsAppService{
		app:            app,
		messageService: messageService,
		accountService: accountService,
		groupService:   groupService,
		whatsApp:       whatsApp,
	}
}

func (w *whatsAppService) SyncGroups(instance *whatsapp.Instance) ([]*model.GroupInfo, error) {
	groups, err := w.whatsApp.GetJoinedGroups(instance)
	if err != nil {
		return nil, err
	}

	var result []*model.GroupInfo
	for _, group := range groups {
		participants := make([]model.Participant, len(group.Participants))
		for i, p := range group.Participants {
			participants[i] = model.Participant{
				JID:          p.JID.String(),
				IsAdmin:      p.IsAdmin,
				IsSuperAdmin: p.IsSuperAdmin,
			}
		}

		groupInfo := &model.GroupInfo{
			JID:          group.JID.String(),
			OwnerJID:     group.OwnerJID.String(),
			Name:         group.Name,
			Participants: participants,
		}

		err = w.groupService.CreateOrUpdateGroup(instance.ID, groupInfo)
		if err != nil {
			logger.Error("Failed to create or update group. ", err)
		}
		result = append(result, groupInfo)
	}

	return result, nil
}

func (w *whatsAppService) GetGroupInfo(instance *whatsapp.Instance, groupID string) (*model.GroupInfo, error) {
	group, err := w.whatsApp.GetGroupInfo(instance, groupID)
	if err != nil {
		return nil, err
	}

	participants := make([]model.Participant, len(group.Participants))
	for i, p := range group.Participants {
		participants[i] = model.Participant{
			JID:          p.JID.String(),
			IsAdmin:      p.IsAdmin,
			IsSuperAdmin: p.IsSuperAdmin,
		}
	}

	groupInfo := &model.GroupInfo{
		JID:          group.JID.String(),
		OwnerJID:     group.OwnerJID.String(),
		Name:         group.Name,
		Participants: participants,
	}

	err = w.groupService.CreateOrUpdateGroup(instance.ID, groupInfo)
	if err != nil {
		logger.Error("Failed to create or update group. ", err)
	}

	return groupInfo, nil
}

func (w *whatsAppService) SendTextMessage(
	instance *whatsapp.Instance,
	jid whatsapp.JID,
	text string,
) (whatsapp.MessageResponse, error) {
	return w.whatsApp.SendTextMessage(instance, jid, text)
}

func (w *whatsAppService) SendDocumentMessage(
	instance *whatsapp.Instance,
	jid whatsapp.JID,
	documentURL *dataurl.DataURL,
	mimitype string,
	filename string,
) (whatsapp.MessageResponse, error) {
	return w.whatsApp.SendDocumentMessage(instance, jid, documentURL, mimitype, filename)
}

func (w *whatsAppService) SendAudioMessage(
	instance *whatsapp.Instance,
	jid whatsapp.JID,
	audioURL *dataurl.DataURL,
	mimitype string,
) (whatsapp.MessageResponse, error) {
	return w.whatsApp.SendAudioMessage(instance, jid, audioURL, mimitype)
}

func (w *whatsAppService) SendImageMessage(
	instance *whatsapp.Instance,
	jid whatsapp.JID,
	imageURL *dataurl.DataURL,
	mimitype string,
) (whatsapp.MessageResponse, error) {
	return w.whatsApp.SendImageMessage(instance, jid, imageURL, mimitype)
}

func (w *whatsAppService) GetContactInfo(instance *whatsapp.Instance, jid whatsapp.JID) (*whatsapp.ContactInfo, error) {
	return w.whatsApp.GetContactInfo(instance, jid)
}

func (w *whatsAppService) ParseEventMessage(instance *whatsapp.Instance, message *events.Message) (whatsapp.Message, error) {
	return w.whatsApp.ParseEventMessage(instance, message)
}

func (w *whatsAppService) IsOnWhatsApp(instance *whatsapp.Instance, phones []string) ([]whatsapp.IsOnWhatsAppResponse, error) {
	return w.whatsApp.IsOnWhatsApp(instance, phones)
}

func (w *whatsAppService) GetInstance(instanceID string) (*whatsapp.Instance, error) {
	instance := w.app.LoadInstance(instanceID)
	if instance != nil {
		return instance, nil
	}

	instance, err := w.gerOrCreateInstance(instanceID)
	if err != nil {
		return nil, err
	}
	w.app.StoreInstance(instanceID, instance)

	instance = w.app.LoadInstance(instanceID)
	instance.Client.AddEventHandler(func(evt interface{}) {
		w.eventHandler(instanceID, evt)
	})

	err = w.whatsApp.InitInstance(instance, func(event string, code string, err error) {
		switch event {
		case "code":
			{
				err = w.accountService.UpdateAccount(instanceID, map[string]interface{}{
					"QrCode":    code,
					"Status":    "UNPAIRED",
					"WasSynced": false,
				})
				if err != nil {
					logger.Error("Failed to update account. ", err)
				}
			}
		case "error":
			{
				logger.Error("Qrcode. ", err)
			}
		case "rate-limit":
			{
				err := w.deleteInstance(instance)
				if err != nil {
					logger.Error("Failed to destroy instance. ", err)
				}
				return
			}
		case "timeout":
			{
				err := w.accountService.UpdateAccount(instanceID, map[string]interface{}{
					"QrCode": "",
					"Status": "TIMEOUT",
				})
				if err != nil {
					logger.Error("Failed to update account. ", err)
				}

				w.deleteInstance(instance)
			}

		}
	})
	if err != nil {
		return nil, err
	}

	return instance, nil
}

func (w *whatsAppService) IsAuthenticated(instance *whatsapp.Instance) bool {
	return w.whatsApp.IsConnected(instance) && w.whatsApp.IsLoggedIn(instance)
}

func (w *whatsAppService) Logout(instance *whatsapp.Instance) error {
	err := w.whatsApp.Logout(instance)
	if err != nil {
		return err
	}

	err = w.accountService.UpdateAccount(instance.ID, map[string]interface{}{
		"Status": "UNPAIRED",
	})
	if err != nil {
		return err
	}

	return w.deleteInstance(instance)
}

func (w *whatsAppService) gerOrCreateInstance(instanceID string) (*whatsapp.Instance, error) {
	account, err := w.accountService.GetAccountByInstanceID(instanceID)
	if err != nil {
		return nil, err
	}

	if account == nil || (account != nil && account.Status != "CONNECTED") {
		instance := w.whatsApp.CreateInstance(instanceID)

		err := w.accountService.CreateAccount(&model.Account{
			InstanceID: instanceID,
		})
		if err != nil {
			return nil, err
		}
		return instance, nil
	}

	jid := types.JID{
		User:       account.User,
		RawAgent:   account.RawAgent,
		Device:     account.Device,
		Integrator: account.Integrator,
		Server:     account.Server,
	}
	instance := w.whatsApp.CreateInstanceFromDevice(
		instanceID,
		jid,
	)
	return instance, nil
}

func (w *whatsAppService) deleteInstance(instance *whatsapp.Instance) error {
	err := w.accountService.DeleteAccountMessages(instance.ID)
	if err != nil {
		return err
	}

	w.whatsApp.Disconnect(instance)
	w.app.DeleteInstance(instance.ID)
	return nil
}

func (w *whatsAppService) eventHandler(instanceID string, rawEvt interface{}) {
	switch evt := rawEvt.(type) {
	case *events.Message:
		w.handleMessage(instanceID, evt)
	case *events.HistorySync:
		w.handleHistorySync(instanceID, evt)
	case *events.Connected:
		w.handleConnected(instanceID)
	case *events.LoggedOut:
		w.handleLoggedOut(instanceID)
	}
}

func (w *whatsAppService) handleHistorySync(instanceID string, evt *events.HistorySync) {
	if !w.app.Config.HistorySync {
		return
	}
	history, _ := proto.Marshal(evt.Data)

	q := queue.NewHistorySyncQueue(w.app)
	err := q.Enqueue(queue.HistorySyncQueueData{
		History:    history,
		InstanceID: instanceID,
	})

	if err != nil {
		logger.Error("Failed to add history sync to queue. ", err)
	}
}

func (w *whatsAppService) handleConnected(instanceID string) {
	var instance = w.app.LoadInstance(instanceID)
	err := w.accountService.UpdateAccount(instanceID, map[string]interface{}{
		"User":       instance.Client.Store.ID.User,
		"RawAgent":   instance.Client.Store.ID.RawAgent,
		"Device":     instance.Client.Store.ID.Device,
		"Server":     instance.Client.Store.ID.Server,
		"Integrator": instance.Client.Store.ID.Integrator,
		"InstanceID": instance.ID,
		"Status":     "CONNECTED",
		"QrCode":     "",
		"WasSynced":  false,
	})

	if err != nil {
		logger.Error("Failed to update account. ", err)
	}
}

func (w *whatsAppService) handleLoggedOut(instanceID string) {
	instance, err := w.GetInstance(instanceID)
	if err != nil {
		logger.Error(err)
		return
	}

	err = w.deleteInstance(instance)
	if err != nil {
		logger.Error(err)
	}

	err = w.accountService.UpdateAccount(instanceID, map[string]interface{}{
		"Status": "UNPAIRED",
	})
	if err != nil {
		logger.Error("Failed to update account. ", err)
	}
}

func (w *whatsAppService) handleMessage(instanceId string, evt *events.Message) {
	instance := w.app.LoadInstance(instanceId)
	parsedEventMessage, err := w.whatsApp.ParseEventMessage(instance, evt)

	if err != nil {
		logger.Error(err)
		return
	}

	message := model.Message{
		SenderJID:  parsedEventMessage.SenderJID,
		ChatJID:    parsedEventMessage.ChatJID,
		InstanceID: parsedEventMessage.InstanceID,
		MessageID:  parsedEventMessage.MessageID,
		Timestamp:  parsedEventMessage.Timestamp,
		Body:       parsedEventMessage.Body,
		FromMe:     parsedEventMessage.FromMe,
	}

	logger.Info(
		"[DEBUG] Handling message. Parsed Event Details: ",
		"ChatJID='", parsedEventMessage.ChatJID, "', ",
		"SenderJID='", parsedEventMessage.SenderJID, "', ",
		"FromMe='", parsedEventMessage.FromMe, "', ",
		"Body='", parsedEventMessage.Body, "',",
		"MediaType='", parsedEventMessage.MediaType, "'", // MediaType is a pointer, might print address or <nil>
	)

	if parsedEventMessage.MediaType != nil {
		mimetype := *parsedEventMessage.Mimetype
		if mimetype == "" && parsedEventMessage.MediaType.String() == "audio" {
			mimetype = "audio/ogg"
			logger.Info("Mimetype was empty for audio message, defaulting to 'audio/ogg'")
		}

		path, err := helper.SaveMedia(
			instance.ID,
			parsedEventMessage.MessageID,
			*parsedEventMessage.Media,
			mimetype,
		)

		if err != nil {
			logger.Error("Failed to save media. ", err)
		}

		message.MediaType = parsedEventMessage.MediaType.String()
		message.Mimetype = mimetype
		message.MediaPath = path
	}

	// Check for text message triggers
	if parsedEventMessage.MediaType == nil && parsedEventMessage.Body != "" && !parsedEventMessage.FromMe { // Condition for a plain text message, not from me
		// Check against global excluded sender JIDs first
		isExcluded := false
		for _, excludedJIDConfig := range w.app.Config.ExcludedSenderJIDs {
			if parsedEventMessage.SenderJID == stripJIDSuffix(excludedJIDConfig) { // Compare with stripped JID from config
				isExcluded = true
				logger.Info("Sender JID ", parsedEventMessage.SenderJID, " is globally excluded (config: ", excludedJIDConfig, "). Skipping chat triggers.")
				break
			}
		}

		if !isExcluded { // Only proceed if sender is not globally excluded
			chatJID := parsedEventMessage.ChatJID // This is already without suffix
			messageBody := parsedEventMessage.Body

			for _, trigger := range w.app.Config.ChatTriggers {
				if stripJIDSuffix(trigger.ChatID) == chatJID { // Compare with stripped JID from config
					logger.Info("Found chat trigger for ChatID ", chatJID, " (config: ", trigger.ChatID, "), script: ", trigger.Script)
					// Pass the Python script name as the first arg to run.sh, then original ChatJID and messageBody
					scriptName := filepath.Base(trigger.Script)
					// Arguments for run.sh: script_to_run.py, arg1_for_script, arg2_for_script, ...
					// The Python scripts themselves no longer use these command-line args for recipient JID.
					// They are passed for potential logging or other uses within the script if ever needed.
					cmd := exec.Command(filepath.Join(w.app.Config.RootDir, "tasks", "run.sh"), scriptName, parsedEventMessage.ChatJID, messageBody)
					output, scriptErr := cmd.CombinedOutput()

					if scriptErr != nil {
						logger.Error("Failed to execute script ", trigger.Script, " for ChatID ", chatJID, ": ", scriptErr, ". Output: ", string(output))
					} else {
						logger.Info("Successfully executed script ", trigger.Script, " for ChatID ", chatJID, ".")
						if len(output) > 0 {
							logger.Info("Script ", trigger.Script, " output: ", string(output))
						}
					}
				}
			}
		}
	}

	err = w.messageService.CreateMessage(&message)
	if err != nil {
		logger.Error("Failed to create message. ", err)
		return
	}

	body := map[string]interface{}{
		"instanceId": instanceId,
		"message":    response.NewMessageResponse(message),
	}

	err = http.Request(w.app.Config.WebhookURL, body)
	if err != nil {
		logger.Error("Failed to send webhook request to ", w.app.Config.WebhookURL, ". ", err)
	}
}
