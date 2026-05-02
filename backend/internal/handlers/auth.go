// Package handlers contains the HTTP handlers for /api/auth/* and /api/me.
//
// Design notes:
//   - The public DTO (userView) never includes the password hash. Handlers
//     project from store.User to userView so an accidental field addition
//     in the DB layer does not leak through the API.
//   - SignIn returns the same opaque error for "no such user" and "wrong
//     password" so an attacker cannot enumerate valid emails.
//   - The auth token is delivered as a HttpOnly, SameSite=Lax cookie. This
//     keeps it inaccessible to JavaScript (XSS-resistant) and avoids the
//     need for the frontend to manage token storage.
package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/chaninjung/minimal-auth-app/internal/auth"
	"github.com/chaninjung/minimal-auth-app/internal/config"
	"github.com/chaninjung/minimal-auth-app/internal/httpx"
	"github.com/chaninjung/minimal-auth-app/internal/middleware"
	"github.com/chaninjung/minimal-auth-app/internal/store"
)

type Auth struct {
	Cfg   config.Config
	Store *store.Store
}

type credBody struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// userView is the public projection of a user — never includes the hash.
type userView struct {
	ID    int64  `json:"id"`
	Email string `json:"email"`
}

func decodeJSON(r *http.Request, dst any) error {
	if r.Body == nil {
		return errors.New("empty body")
	}
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	return dec.Decode(dst)
}

// validateCreds normalises and validates inputs. Email is lowercased and
// trimmed; we keep the rule simple ("must contain @, length sane") and
// rely on the frontend (zod) for richer feedback. Password length matches
// the frontend rule (8–128). Bcrypt itself caps usable input at 72 bytes;
// we accept up to 128 to be friendly and let bcrypt truncate as documented.
func validateCreds(b credBody) (email, password string, err error) {
	email = strings.TrimSpace(strings.ToLower(b.Email))
	if !strings.Contains(email, "@") || len(email) < 3 || len(email) > 254 {
		return "", "", errors.New("email is invalid")
	}
	if len(b.Password) < 8 || len(b.Password) > 128 {
		return "", "", errors.New("password must be 8-128 characters")
	}
	return email, b.Password, nil
}

// SignUp creates a new user. Returns 201 with the public user view.
func (h *Auth) SignUp(w http.ResponseWriter, r *http.Request) {
	var b credBody
	if err := decodeJSON(r, &b); err != nil {
		httpx.Error(w, http.StatusBadRequest, "bad_request", "invalid json body")
		return
	}
	email, password, err := validateCreds(b)
	if err != nil {
		httpx.Error(w, http.StatusUnprocessableEntity, "validation_failed", err.Error())
		return
	}
	hash, err := auth.HashPassword(password, h.Cfg.BcryptCost)
	if err != nil {
		httpx.Error(w, http.StatusInternalServerError, "internal", "could not hash password")
		return
	}
	u, err := h.Store.CreateUser(r.Context(), email, hash)
	if err != nil {
		if errors.Is(err, store.ErrEmailTaken) {
			httpx.Error(w, http.StatusConflict, "email_taken", "email is already registered")
			return
		}
		httpx.Error(w, http.StatusInternalServerError, "internal", "could not create user")
		return
	}
	httpx.JSON(w, http.StatusCreated, userView{ID: u.ID, Email: u.Email})
}

// SignIn verifies credentials and sets the auth cookie on success.
func (h *Auth) SignIn(w http.ResponseWriter, r *http.Request) {
	var b credBody
	if err := decodeJSON(r, &b); err != nil {
		httpx.Error(w, http.StatusBadRequest, "bad_request", "invalid json body")
		return
	}
	email, password, err := validateCreds(b)
	if err != nil {
		// Generic message — never leak which field is wrong on auth.
		httpx.Error(w, http.StatusUnauthorized, "invalid_credentials", "invalid credentials")
		return
	}
	u, err := h.Store.UserByEmail(r.Context(), email)
	if err != nil || !auth.CheckPassword(u.PasswordHash, password) {
		httpx.Error(w, http.StatusUnauthorized, "invalid_credentials", "invalid credentials")
		return
	}
	tok, exp, err := auth.IssueToken(h.Cfg.JWTSecret, u.ID, u.Email, h.Cfg.TokenTTL)
	if err != nil {
		httpx.Error(w, http.StatusInternalServerError, "internal", "could not issue token")
		return
	}
	setAuthCookie(w, h.Cfg, tok, exp)
	httpx.JSON(w, http.StatusOK, userView{ID: u.ID, Email: u.Email})
}

// SignOut clears the auth cookie. We don't maintain a server-side session
// store, so signout is purely about the client losing its token.
func (h *Auth) SignOut(w http.ResponseWriter, _ *http.Request) {
	clearAuthCookie(w, h.Cfg)
	w.WriteHeader(http.StatusNoContent)
}

func setAuthCookie(w http.ResponseWriter, cfg config.Config, token string, exp time.Time) {
	http.SetCookie(w, &http.Cookie{
		Name:     middleware.CookieName,
		Value:    token,
		Path:     "/",
		Expires:  exp,
		HttpOnly: true,
		Secure:   cfg.CookieSecure,
		SameSite: http.SameSiteLaxMode,
	})
}

func clearAuthCookie(w http.ResponseWriter, cfg config.Config) {
	http.SetCookie(w, &http.Cookie{
		Name:     middleware.CookieName,
		Value:    "",
		Path:     "/",
		Expires:  time.Unix(0, 0),
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   cfg.CookieSecure,
		SameSite: http.SameSiteLaxMode,
	})
}
