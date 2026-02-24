package main

import (
	"fmt"
	"zapmeow/config"
	"github.com/joho/godotenv"
)

func main() {
	godotenv.Load(".env")
	cfg := config.Load()
	fmt.Printf("WebhookURLs: %#v\n", cfg.WebhookURLs)
}
