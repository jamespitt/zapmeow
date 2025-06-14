package handler

import (
	"net/http"
	"os"
	"zapmeow/api/response"
	"zapmeow/api/service"
	"zapmeow/pkg/logger"
	"zapmeow/pkg/zapmeow"

	"github.com/gin-gonic/gin"
	"github.com/mdp/qrterminal/v3"
)

type getQrCodeResponse struct {
	QrCode string `json:"qrcode"`
}

type getQrCodeHandler struct {
	app             *zapmeow.ZapMeow
	whatsAppService service.WhatsAppService
	messageService  service.MessageService
	accountService  service.AccountService
}

func NewGetQrCodeHandler(
	app *zapmeow.ZapMeow,
	whatsAppService service.WhatsAppService,
	messageService service.MessageService,
	accountService service.AccountService,
) *getQrCodeHandler {
	return &getQrCodeHandler{
		app:             app,
		whatsAppService: whatsAppService,
		messageService:  messageService,
		accountService:  accountService,
	}
}

// Get QR Code for WhatsApp Login
//
//	@Summary		Get WhatsApp QR Code
//	@Description	Returns a QR code to initiate WhatsApp login.
//	@Tags			WhatsApp Login
//	@Param			instanceId	path	string	true	"Instance ID"
//	@Produce		json
//	@Success		200	{object}	getQrCodeResponse	"QR Code"
//	@Router			/{instanceId}/qrcode [get]
func (h *getQrCodeHandler) Handler(c *gin.Context) {
	instanceID := c.Param("instanceId")
	_, err := h.whatsAppService.GetInstance(instanceID)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	h.app.Mutex.Lock()
	defer h.app.Mutex.Unlock()
	account, err := h.accountService.GetAccountByInstanceID(instanceID)
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	if account == nil {
		response.ErrorResponse(c, http.StatusInternalServerError, "Account not found")
		return
	}

	// Log the QR code to the terminal
	logger.Info("Generating QR Code for instance: ", instanceID)
	qrterminal.GenerateWithConfig(account.QrCode, qrterminal.Config{
		Level:     qrterminal.L,
		Writer:    os.Stdout,
		BlackChar: qrterminal.BLACK,
		WhiteChar: qrterminal.WHITE,
	})

	response.Response(c, http.StatusOK, getQrCodeResponse{
		QrCode: account.QrCode,
	})
}
