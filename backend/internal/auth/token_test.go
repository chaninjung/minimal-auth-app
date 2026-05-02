package auth

import (
	"strings"
	"testing"
	"time"
)

func TestIssueAndParse_Roundtrip(t *testing.T) {
	secret := []byte("test-secret")
	tok, exp, err := IssueToken(secret, 42, "x@example.com", time.Minute)
	if err != nil {
		t.Fatalf("IssueToken: %v", err)
	}
	if exp.Before(time.Now()) {
		t.Fatal("token expired immediately")
	}
	c, err := ParseToken(secret, tok)
	if err != nil {
		t.Fatalf("ParseToken: %v", err)
	}
	if c.UserID != 42 || c.Email != "x@example.com" {
		t.Fatalf("bad claims: %+v", c)
	}
}

func TestParse_WrongSecret(t *testing.T) {
	tok, _, _ := IssueToken([]byte("a"), 1, "x@y.com", time.Minute)
	if _, err := ParseToken([]byte("b"), tok); err == nil {
		t.Fatal("expected verification error for wrong secret")
	}
}

func TestParse_Expired(t *testing.T) {
	secret := []byte("s")
	tok, _, _ := IssueToken(secret, 1, "x@y.com", -time.Second)
	_, err := ParseToken(secret, tok)
	if err == nil {
		t.Fatal("expected expiry error")
	}
}

func TestParse_GarbageToken(t *testing.T) {
	if _, err := ParseToken([]byte("s"), "not-a-real-jwt"); err == nil {
		t.Fatal("expected parse error for garbage")
	}
}

func TestParse_RejectsAlgNone(t *testing.T) {
	// "alg=none" is the classic JWT confusion attack: a token with header
	// {"alg":"none"} and no signature should be rejected by our keyfunc,
	// which only accepts HMAC. We construct one by hand and ensure it fails.
	headerB64 := base64URL(`{"alg":"none","typ":"JWT"}`)
	payloadB64 := base64URL(`{"uid":1}`)
	tok := headerB64 + "." + payloadB64 + "."
	if _, err := ParseToken([]byte("s"), tok); err == nil {
		t.Fatal("expected rejection of alg=none")
	}
	// sanity check on the test helper itself
	if !strings.Contains(tok, ".") {
		t.Fatal("test helper malformed")
	}
}

// base64URL returns a JWT-style (no-padding) base64url encoding of s.
func base64URL(s string) string {
	const tbl = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
	b := []byte(s)
	var out strings.Builder
	for i := 0; i < len(b); i += 3 {
		var n uint32
		var pad int
		switch len(b) - i {
		case 1:
			n = uint32(b[i]) << 16
			pad = 2
		case 2:
			n = uint32(b[i])<<16 | uint32(b[i+1])<<8
			pad = 1
		default:
			n = uint32(b[i])<<16 | uint32(b[i+1])<<8 | uint32(b[i+2])
		}
		out.WriteByte(tbl[(n>>18)&0x3F])
		out.WriteByte(tbl[(n>>12)&0x3F])
		if pad < 2 {
			out.WriteByte(tbl[(n>>6)&0x3F])
		}
		if pad < 1 {
			out.WriteByte(tbl[n&0x3F])
		}
	}
	return out.String()
}
