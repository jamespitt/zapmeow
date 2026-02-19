package http

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
)

func Request(url string, data map[string]interface{}) error {
	body, err := json.Marshal(data)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(body))
	if err != nil {
		// This error is for network issues, not bad status codes
		return err
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return errors.New("Request returned an unexpected status code")
	}

	defer resp.Body.Close()

	// Check for non-2xx status codes
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("webhook request failed with status code: %d", resp.StatusCode)
	}

	return nil
}
