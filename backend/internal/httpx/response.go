// Package httpx contains small HTTP helpers used by every handler so the
// JSON error shape stays consistent across endpoints.
package httpx

import (
	"encoding/json"
	"log"
	"net/http"
)

// ErrorBody is the shape returned for any 4xx/5xx response. Code is an
// optional machine-readable identifier the frontend can branch on; Error
// is a short human-readable message.
type ErrorBody struct {
	Error string `json:"error"`
	Code  string `json:"code,omitempty"`
}

// JSON writes v as JSON with the given status. A nil v is allowed (used
// for 204-style responses with no body).
func JSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if v == nil {
		return
	}
	if err := json.NewEncoder(w).Encode(v); err != nil {
		// Headers are already flushed at this point, so we can only log.
		log.Printf("httpx: encode response: %v", err)
	}
}

// Error writes a standard ErrorBody.
func Error(w http.ResponseWriter, status int, code, msg string) {
	JSON(w, status, ErrorBody{Error: msg, Code: code})
}
