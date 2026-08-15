package handler

import (
	"net/http"
	"strings"
	"zapmeow/api/response"
	"zapmeow/api/service"

	"github.com/gin-gonic/gin"
)

type chatSummary struct {
	ChatJID      string           `json:"chat_jid"`
	Name         string           `json:"name,omitempty"`
	IsGroup      bool             `json:"is_group"`
	MessageCount int64            `json:"message_count"`
	LastMessage  response.Message `json:"last_message"`
}

type getChatsResponse struct {
	Chats []chatSummary `json:"chats"`
}

type getChatsHandler struct {
	whatsAppService service.WhatsAppService
	messageService  service.MessageService
	groupService    service.GroupService
}

func NewGetChatsHandler(
	whatsAppService service.WhatsAppService,
	messageService service.MessageService,
	groupService service.GroupService,
) *getChatsHandler {
	return &getChatsHandler{
		whatsAppService: whatsAppService,
		messageService:  messageService,
		groupService:    groupService,
	}
}

// Get WhatsApp Chats
//
//	@Summary		Get WhatsApp chats for an instance
//	@Description	Returns one summary row per chat (group or person) the instance has messages in, newest activity first.
//	@Tags			WhatsApp Chat
//	@Param			instanceId	path	string	true	"Instance ID"
//	@Produce		json
//	@Success		200	{object}	getChatsResponse	"List of chats"
//	@Router			/{instanceId}/chats [get]
func (h *getChatsHandler) Handler(c *gin.Context) {
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

	latestByChat, counts, err := h.messageService.GetChatsByInstanceID(instanceID)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	chats := make([]chatSummary, 0, len(*latestByChat))
	for _, msg := range *latestByChat {
		isGroup := strings.HasSuffix(msg.ChatJID, "@g.us")
		name := ""
		if isGroup {
			if group, err := h.groupService.GetGroupByJID(msg.ChatJID); err == nil && group != nil {
				name = group.Name
			}
		}
		chats = append(chats, chatSummary{
			ChatJID:      msg.ChatJID,
			Name:         name,
			IsGroup:      isGroup,
			MessageCount: counts[msg.ChatJID],
			LastMessage:  response.NewMessageResponse(msg),
		})
	}

	response.Response(c, http.StatusOK, getChatsResponse{Chats: chats})
}
