package handler

import (
	"net/http"
	"zapmeow/api/response"
	"zapmeow/api/service"

	"github.com/gin-gonic/gin"
	"go.mau.fi/whatsmeow/types"
)

type groupInfoResponse struct {
	Info *types.GroupInfo `json:"info"`
}

type getGroupInfoHandler struct {
	whatsAppService service.WhatsAppService
}

func NewGetGroupInfoHandler(
	whatsAppService service.WhatsAppService,
) *getGroupInfoHandler {
	return &getGroupInfoHandler{
		whatsAppService: whatsAppService,
	}
}

// Get Group Information
//
//	@Summary		Get Group Information
//	@Description	Retrieves group information.
//	@Tags			WhatsApp Group
//	@Param			instanceId	path	string	true	"Instance ID"
//	@Param			groupId		query	string	true	"Group ID"
//	@Accept			json
//	@Produce		json
//	@Success		200	{object}	groupInfoResponse	"Group Information"
//	@Router			/{instanceId}/group/info [get]
func (h *getGroupInfoHandler) Handler(c *gin.Context) {
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

	groupID := c.Query("groupId")
	if groupID == "" {
		response.ErrorResponse(c, http.StatusBadRequest, "groupId is required")
		return
	}

	info, err := h.whatsAppService.GetGroupInfo(instance, groupID)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	response.Response(c, http.StatusOK, groupInfoResponse{
		Info: info,
	})
}
