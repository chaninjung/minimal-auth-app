package handlers

import (
	"net/http"

	"github.com/chaninjung/minimal-auth-app/internal/httpx"
	"github.com/chaninjung/minimal-auth-app/internal/middleware"
	"github.com/chaninjung/minimal-auth-app/internal/store"
)

// Me handles GET /api/me — the protected endpoint that returns the
// authenticated user. Auth is enforced by middleware.Auth which sets the
// claims on the request context.
type Me struct {
	Store *store.Store
}

func (h *Me) Get(w http.ResponseWriter, r *http.Request) {
	claims := middleware.ClaimsFrom(r.Context())
	if claims == nil {
		// Defensive — should be unreachable behind middleware.Auth.
		httpx.Error(w, http.StatusUnauthorized, "unauthenticated", "authentication required")
		return
	}
	// Re-fetch from the DB rather than trusting only the token. This means
	// if the user is deleted, the next /me call invalidates the session
	// even though the JWT itself is still cryptographically valid.
	u, err := h.Store.UserByID(r.Context(), claims.UserID)
	if err != nil {
		httpx.Error(w, http.StatusUnauthorized, "unauthenticated", "authentication required")
		return
	}
	httpx.JSON(w, http.StatusOK, userView{ID: u.ID, Email: u.Email})
}
