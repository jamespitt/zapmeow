package handler

import (
	"net/http"
	"os"
	"strings"
	"zapmeow/api/response"
	"zapmeow/api/service"
	"zapmeow/pkg/zapmeow"

	"github.com/gin-gonic/gin"
)

type getQrCodePageHandler struct {
	app             *zapmeow.ZapMeow
	whatsAppService service.WhatsAppService
	accountService  service.AccountService
}

func NewGetQrCodePageHandler(
	app *zapmeow.ZapMeow,
	whatsAppService service.WhatsAppService,
	accountService service.AccountService,
) *getQrCodePageHandler {
	return &getQrCodePageHandler{
		app:             app,
		whatsAppService: whatsAppService,
		accountService:  accountService,
	}
}

func (h *getQrCodePageHandler) Handler(c *gin.Context) {
	instanceID := c.Param("instanceId")
	if instanceID == "" {
		response.ErrorResponse(c, http.StatusBadRequest, "InstanceID is required")
		return
	}

	_, err := h.whatsAppService.GetInstance(instanceID)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	account, err := h.accountService.GetAccountByInstanceID(instanceID)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	if account.Status == "CONNECTED" {
		response.ErrorResponse(c, http.StatusBadRequest, "Instance already connected")
		return
	}

	html, err := os.ReadFile("docs/qrcode.html")
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, "Error reading QR code page")
		return
	}

	htmlString := strings.Replace(string(html), "{{QR_CODE}}", account.QrCode, 1)

	c.Data(http.StatusOK, "text/html; charset=utf-8", []byte(htmlString))
}
