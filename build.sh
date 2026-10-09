#!/bin/bash
go build cmd/server/main.go 
sudo systemctl restart zapmeow.service
