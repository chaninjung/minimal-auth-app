// Package middleware contains HTTP middleware. The auth middleware reads
// the JWT from a HttpOnly cookie, verifies it, and attaches the claims to
// the request context so downstream handlers can read the caller's
// identity without re-parsing.
package middleware

import (
	"context"
	"net/http"

	"github.com/chaninjung/minimal-auth-app/internal/auth"
	"github.com/chaninjung/minimal-auth-app/internal/httpx"
)

// CookieName is the name of the auth cookie. Centralised so handlers and
// middleware never disagree.
const CookieName = "rk_token"

type ctxKey string

const claimsKey ctxKey = "claims"

// Auth returns a middleware that requires a valid JWT cookie. On failure
// it emits a 401 with a generic message — we never tell the caller which
// validation step failed, only that auth is required.
func Auth(secret []byte) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			c, err := r.Cookie(CookieName)
			if err != nil || c.Value == "" {
				httpx.Error(w, http.StatusUnauthorized, "unauthenticated", "authentication required")
				return
			}
			claims, err := auth.ParseToken(secret, c.Value)
			if err != nil {
				httpx.Error(w, http.StatusUnauthorized, "invalid_token", "authentication required")
				return
			}
			ctx := context.WithValue(r.Context(), claimsKey, claims)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// ClaimsFrom extracts the auth claims attached by Auth. Returns nil if the
// request did not pass through Auth — handlers behind Auth can rely on a
// non-nil result.
func ClaimsFrom(ctx context.Context) *auth.Claims {
	if c, ok := ctx.Value(claimsKey).(*auth.Claims); ok {
		return c
	}
	return nil
}
