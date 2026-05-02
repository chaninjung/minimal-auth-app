package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
	"time"

	"github.com/chaninjung/minimal-auth-app/internal/config"
	"github.com/chaninjung/minimal-auth-app/internal/store"
)

// newTestAuth wires up a real (file-backed) Store in a temp dir. Using the
// real DB rather than a mock is deliberate — the unique-violation mapping
// is one of the things most likely to drift, and a stub would not catch it.
func newTestAuth(t *testing.T) *Auth {
	t.Helper()
	s, err := store.Open(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	if err := s.Migrate(context.Background()); err != nil {
		t.Fatalf("Migrate: %v", err)
	}
	t.Cleanup(func() { _ = s.Close() })
	return &Auth{
		Cfg: config.Config{
			JWTSecret:  []byte("test-secret"),
			TokenTTL:   time.Minute,
			BcryptCost: 4, // keep tests fast
		},
		Store: s,
	}
}

func postJSON(t *testing.T, h http.HandlerFunc, body any) *httptest.ResponseRecorder {
	t.Helper()
	buf, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/", bytes.NewReader(buf))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h(rr, req)
	return rr
}

func TestSignUp_Created(t *testing.T) {
	a := newTestAuth(t)
	rr := postJSON(t, a.SignUp, map[string]string{
		"email": "test@example.com", "password": "hunter2hunter2",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("status=%d body=%s", rr.Code, rr.Body.String())
	}
}

func TestSignUp_DuplicateConflict(t *testing.T) {
	a := newTestAuth(t)
	body := map[string]string{"email": "dup@example.com", "password": "hunter2hunter2"}
	if rr := postJSON(t, a.SignUp, body); rr.Code != http.StatusCreated {
		t.Fatalf("first signup: %d", rr.Code)
	}
	rr := postJSON(t, a.SignUp, body)
	if rr.Code != http.StatusConflict {
		t.Fatalf("expected 409 on duplicate, got %d", rr.Code)
	}
}

func TestSignUp_DuplicateConflict_CaseInsensitive(t *testing.T) {
	// Emails are stored COLLATE NOCASE — registering FOO@x.com after
	// foo@x.com must conflict, not silently shadow.
	a := newTestAuth(t)
	if rr := postJSON(t, a.SignUp, map[string]string{
		"email": "case@example.com", "password": "hunter2hunter2",
	}); rr.Code != http.StatusCreated {
		t.Fatalf("first: %d", rr.Code)
	}
	rr := postJSON(t, a.SignUp, map[string]string{
		"email": "CASE@example.com", "password": "hunter2hunter2",
	})
	if rr.Code != http.StatusConflict {
		t.Fatalf("expected 409 for case-variant email, got %d", rr.Code)
	}
}

func TestSignUp_InvalidEmail(t *testing.T) {
	a := newTestAuth(t)
	rr := postJSON(t, a.SignUp, map[string]string{
		"email": "no-at-sign", "password": "hunter2hunter2",
	})
	if rr.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", rr.Code)
	}
}

func TestSignUp_ShortPassword(t *testing.T) {
	a := newTestAuth(t)
	rr := postJSON(t, a.SignUp, map[string]string{
		"email": "x@y.com", "password": "short",
	})
	if rr.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422, got %d", rr.Code)
	}
}

func TestSignIn_OK_SetsCookie(t *testing.T) {
	a := newTestAuth(t)
	body := map[string]string{"email": "log@example.com", "password": "hunter2hunter2"}
	if rr := postJSON(t, a.SignUp, body); rr.Code != http.StatusCreated {
		t.Fatalf("signup: %d", rr.Code)
	}
	rr := postJSON(t, a.SignIn, body)
	if rr.Code != http.StatusOK {
		t.Fatalf("signin: %d body=%s", rr.Code, rr.Body.String())
	}
	cookies := rr.Result().Cookies()
	if len(cookies) == 0 {
		t.Fatal("expected auth cookie")
	}
	c := cookies[0]
	if c.Value == "" {
		t.Fatal("auth cookie has empty value")
	}
	if !c.HttpOnly {
		t.Error("auth cookie should be HttpOnly")
	}
	if c.SameSite != http.SameSiteLaxMode {
		t.Errorf("SameSite=%v, want Lax", c.SameSite)
	}
}

func TestSignIn_BadPassword_GenericError(t *testing.T) {
	a := newTestAuth(t)
	if rr := postJSON(t, a.SignUp, map[string]string{
		"email": "bp@example.com", "password": "hunter2hunter2",
	}); rr.Code != http.StatusCreated {
		t.Fatalf("signup: %d", rr.Code)
	}
	rr := postJSON(t, a.SignIn, map[string]string{
		"email": "bp@example.com", "password": "wrongwrongwrong",
	})
	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", rr.Code)
	}
}

func TestSignIn_UnknownUser_SameError(t *testing.T) {
	// Must look identical to "wrong password" so the response cannot be
	// used to enumerate registered emails.
	a := newTestAuth(t)
	rr := postJSON(t, a.SignIn, map[string]string{
		"email": "ghost@example.com", "password": "hunter2hunter2",
	})
	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", rr.Code)
	}
}

func TestSignOut_NoContent(t *testing.T) {
	a := newTestAuth(t)
	req := httptest.NewRequest(http.MethodPost, "/", nil)
	rr := httptest.NewRecorder()
	a.SignOut(rr, req)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", rr.Code)
	}
	cookies := rr.Result().Cookies()
	if len(cookies) == 0 || cookies[0].MaxAge != -1 {
		t.Fatal("expected cookie clear (MaxAge=-1)")
	}
}
