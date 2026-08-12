package handler

import (
	"net/http"
	"strconv"
	"time"
	"zapmeow/api/response"
	"zapmeow/api/service"

	"github.com/gin-gonic/gin"
)

const (
	defaultAllMessagesLimit = 50
	maxAllMessagesLimit     = 200
)

type getAllMessagesResponse struct {
	Messages   []response.Message `json:"messages"`
	HasMore    bool               `json:"has_more"`
	NextBefore int64              `json:"next_before,omitempty"`
}

type getAllMessagesHandler struct {
	whatsAppService service.WhatsAppService
	messageService  service.MessageService
}

func NewGetAllMessagesHandler(
	whatsAppService service.WhatsAppService,
	messageService service.MessageService,
) *getAllMessagesHandler {
	return &getAllMessagesHandler{
		whatsAppService: whatsAppService,
		messageService:  messageService,
	}
}

// Get All WhatsApp Messages
//
//	@Summary		Get all WhatsApp messages for an instance
//	@Description	Returns messages across all chats for the instance, newest first, paginated.
//	@Tags			WhatsApp Chat
//	@Param			instanceId	path	string	true	"Instance ID"
//	@Param			limit		query	int		false	"Max messages to return (default 50, max 200)"
//	@Param			before		query	int		false	"Unix timestamp (seconds); only return messages strictly before this time"
//	@Produce		json
//	@Success		200	{object}	getAllMessagesResponse	"List of chat messages"
//	@Router			/{instanceId}/chat/all-messages [get]
func (h *getAllMessagesHandler) Handler(c *gin.Context) {
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

	limit := defaultAllMessagesLimit
	if raw := c.Query("limit"); raw != "" {
		parsed, err := strconv.Atoi(raw)
		if err != nil || parsed <= 0 {
			response.ErrorResponse(c, http.StatusBadRequest, "invalid limit")
			return
		}
		limit = parsed
	}
	if limit > maxAllMessagesLimit {
		limit = maxAllMessagesLimit
	}

	var before *time.Time
	if raw := c.Query("before"); raw != "" {
		sec, err := strconv.ParseInt(raw, 10, 64)
		if err != nil {
			response.ErrorResponse(c, http.StatusBadRequest, "invalid before")
			return
		}
		t := time.Unix(sec, 0)
		before = &t
	}

	// Fetch one extra message to detect whether another page exists.
	messages, err := h.messageService.GetMessagesByInstanceID(instanceID, limit+1, before)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	msgs := *messages
	hasMore := len(msgs) > limit
	if hasMore {
		msgs = msgs[:limit]
	}

	var nextBefore int64
	if hasMore && len(msgs) > 0 {
		nextBefore = msgs[len(msgs)-1].Timestamp.Unix()
	}

	response.Response(c, http.StatusOK, getAllMessagesResponse{
		Messages:   response.NewMessagesResponse(&msgs),
		HasMore:    hasMore,
		NextBefore: nextBefore,
	})
}
