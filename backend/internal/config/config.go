// Package config loads runtime configuration from environment variables.
//
// All values have safe defaults so the server can boot with `go run` and
// no extra setup; see README.md for production-grade overrides.
package config

import (
	"os"
	"strconv"
	"time"
)

// Config holds the resolved runtime configuration.
//
// Anything that would change between local dev, CI, and production lives
// here so handlers/stores never read os.Getenv directly. That makes
// handlers trivially testable — see internal/handlers/auth_test.go.
type Config struct {
	Addr          string        // listen address, e.g. "0.0.0.0:8080"
	DBPath        string        // SQLite file path
	JWTSecret     []byte        // HMAC secret for signing JWTs
	TokenTTL      time.Duration // JWT validity window
	AllowedOrigin string        // CORS allowed origin (single — keep it explicit)
	CookieSecure  bool          // set Secure flag on auth cookie (HTTPS only)
	BcryptCost    int           // bcrypt work factor; lower in tests
}

// FromEnv builds a Config from environment variables, applying defaults.
func FromEnv() Config {
	return Config{
		Addr:          getenv("ADDR", "0.0.0.0:8080"),
		DBPath:        getenv("DB_PATH", "data.db"),
		JWTSecret:     []byte(getenv("JWT_SECRET", "dev-secret-change-me")),
		TokenTTL:      durationEnv("TOKEN_TTL", 24*time.Hour),
		AllowedOrigin: getenv("ALLOWED_ORIGIN", "http://localhost:5173"),
		CookieSecure:  boolEnv("COOKIE_SECURE", false),
		BcryptCost:    intEnv("BCRYPT_COST", 12),
	}
}

func getenv(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func intEnv(k string, d int) int {
	if v := os.Getenv(k); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return d
}

func boolEnv(k string, d bool) bool {
	if v := os.Getenv(k); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return d
}

func durationEnv(k string, d time.Duration) time.Duration {
	if v := os.Getenv(k); v != "" {
		if dd, err := time.ParseDuration(v); err == nil {
			return dd
		}
	}
	return d
}
