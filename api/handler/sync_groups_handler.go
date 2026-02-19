package handler

import (
	"net/http"
	"zapmeow/api/response"
	"zapmeow/api/service"

	"github.com/gin-gonic/gin"
)

type syncGroupsHandler struct {
	whatsAppService service.WhatsAppService
}

func NewSyncGroupsHandler(
	whatsAppService service.WhatsAppService,
) *syncGroupsHandler {
	return &syncGroupsHandler{
		whatsAppService: whatsAppService,
	}
}

// Sync Groups
//
//	@Summary		Sync Groups
//	@Description	Syncs all groups from the instance.
//	@Tags			WhatsApp Group
//	@Param			instanceId	path	string	true	"Instance ID"
//	@Success		200	{object}	response.Response	"Groups Synced"
//	@Router			/{instanceId}/groups/sync [get]
func (h *syncGroupsHandler) Handler(c *gin.Context) {
	instance, err := h.whatsAppService.GetInstance(c.Param("instanceId"))
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	if !h.whatsAppService.IsAuthenticated(instance) {
		response.ErrorResponse(c, http.StatusUnauthorized, "Instance not authenticated")
		return
	}

	groups, err := h.whatsAppService.SyncGroups(instance)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	response.Response(c, http.StatusOK, gin.H{
		"message": "Groups Synced",
		"groups":  groups,
	})
}
