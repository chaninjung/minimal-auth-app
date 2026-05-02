package auth

import "testing"

func TestHashAndCheck(t *testing.T) {
	const pw = "hunter2hunter2"
	h, err := HashPassword(pw, 4) // low cost for test speed
	if err != nil {
		t.Fatalf("HashPassword: %v", err)
	}
	if h == "" || h == pw {
		t.Fatalf("hash looks wrong: %q", h)
	}
	if !CheckPassword(h, pw) {
		t.Fatal("CheckPassword: expected match")
	}
	if CheckPassword(h, "wrong-password") {
		t.Fatal("CheckPassword: expected mismatch")
	}
}

func TestHashUniquePerCall(t *testing.T) {
	// bcrypt salts each call so the same password should produce different
	// hashes — this guards against accidental salt reuse.
	a, _ := HashPassword("samesame", 4)
	b, _ := HashPassword("samesame", 4)
	if a == b {
		t.Fatal("expected unique hashes per call")
	}
}
