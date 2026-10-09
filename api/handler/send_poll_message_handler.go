package handler

import (
	"net/http"
	"zapmeow/api/model"
	"zapmeow/api/response"
	"zapmeow/api/service"
	"zapmeow/pkg/whatsapp"

	"github.com/gin-gonic/gin"
)

type sendPollMessageBody struct {
	Phone                 string   `json:"phone"`
	Name                  string   `json:"name"`
	Options               []string `json:"options"`
	SelectableOptionCount *int     `json:"selectable_option_count"`
}

type sendPollMessageResponse struct {
	Message response.Message `json:"message"`
}

type sendPollMessageHandler struct {
	whatsAppService service.WhatsAppService
	messageService  service.MessageService
}

func NewSendPollMessageHandler(
	whatsAppService service.WhatsAppService,
	messageService service.MessageService,
) *sendPollMessageHandler {
	return &sendPollMessageHandler{
		whatsAppService: whatsAppService,
		messageService:  messageService,
	}
}

// Send Poll Message on WhatsApp
//
//	@Summary		Send Poll Message on WhatsApp
//	@Description	Sends a poll message on WhatsApp using the specified instance.
//	@Tags			WhatsApp Chat
//	@Param			instanceId	path	string				true	"Instance ID"
//	@Param			data		body	sendPollMessageBody	true	"Poll message body"
//	@Accept			json
//	@Produce		json
//	@Success		200	{object}	sendPollMessageResponse	"Message Send Response"
//	@Router			/{instanceId}/chat/send/poll [post]
func (h *sendPollMessageHandler) Handler(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			response.ErrorResponse(c, http.StatusInternalServerError, "An internal error occurred")
		}
	}()

	instanceID := c.Param("instanceId")
	instance, err := h.whatsAppService.GetInstance(instanceID)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	if !h.whatsAppService.IsAuthenticated(instance) {
		response.ErrorResponse(c, http.StatusUnauthorized, "unautenticated")
		return
	}

	var body sendPollMessageBody
	if err := c.ShouldBindJSON(&body); err != nil {
		response.ErrorResponse(c, http.StatusBadRequest, "Error trying to validate infos. ")
		return
	}

	if body.Phone == "" || body.Name == "" || len(body.Options) < 2 || len(body.Options) > 12 {
		response.ErrorResponse(c, http.StatusBadRequest, "Error trying to validate infos. ")
		return
	}

	jid, ok := whatsapp.MakeJID(body.Phone)
	if !ok {
		response.ErrorResponse(c, http.StatusBadRequest, "Invalid phone")
		return
	}

	selectableCount := 1
	if body.SelectableOptionCount != nil {
		selectableCount = *body.SelectableOptionCount
	}

	resp, err := h.whatsAppService.SendPollMessage(instance, jid, body.Name, selectableCount, body.Options)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	message := model.Message{
		MessageID:  resp.ID,
		ChatJID:    jid.User,
		SenderJID:  resp.Sender.User,
		InstanceID: instanceID,
		Body:       body.Name,
		MediaType:  "poll",
		Timestamp:  resp.Timestamp,
		FromMe:     true,
	}

	err = h.messageService.CreateMessage(&message)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	response.Response(c, http.StatusOK, sendPollMessageResponse{
		Message: response.NewMessageResponse(message),
	})
}
