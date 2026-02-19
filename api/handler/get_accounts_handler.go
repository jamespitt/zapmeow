package handler

import (
	"net/http"
	"zapmeow/api/response"
	"zapmeow/api/service"

	"github.com/gin-gonic/gin"
)

type getAccountsHandler struct {
	accountService service.AccountService
}

func NewGetAccountsHandler(accountService service.AccountService) *getAccountsHandler {
	return &getAccountsHandler{
		accountService: accountService,
	}
}

// Get Accounts godoc
// @Summary      Get accounts
// @Description  Get all accounts
// @Tags         accounts
// @Accept       json
// @Produce      json
// @Success      200  {object}  []model.Account
// @Router       /accounts [get]
func (h *getAccountsHandler) Handler(c *gin.Context) {
	accounts, err := h.accountService.GetAllAccounts()
	if err != nil {
		response.ErrorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}
	response.Response(c, http.StatusOK, accounts)
}
