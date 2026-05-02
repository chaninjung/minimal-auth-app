package auth

import (
	"errors"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// Claims is the JWT payload. We only carry the user ID and email — anything
// more would couple the token to mutable user state. UserID is the source
// of truth; email is included to populate the UI without an extra DB hit
// (still re-validated against the DB on /api/me).
type Claims struct {
	UserID int64  `json:"uid"`
	Email  string `json:"email"`
	jwt.RegisteredClaims
}

// IssueToken signs a new JWT with HS256 and returns the token string and
// its absolute expiry time (so callers can mirror it on the cookie).
func IssueToken(secret []byte, userID int64, email string, ttl time.Duration) (string, time.Time, error) {
	now := time.Now()
	exp := now.Add(ttl)
	claims := Claims{
		UserID: userID,
		Email:  email,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(exp),
			IssuedAt:  jwt.NewNumericDate(now),
			NotBefore: jwt.NewNumericDate(now),
			Issuer:    "minimal-auth",
			Subject:   email,
		},
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := tok.SignedString(secret)
	if err != nil {
		return "", time.Time{}, err
	}
	return signed, exp, nil
}

// ParseToken verifies signature, expiry, and algorithm, returning the
// claims on success. The keyfunc rejects any non-HMAC algorithm to defend
// against the classic "alg=none" / RSA-as-HMAC confusion attacks.
func ParseToken(secret []byte, raw string) (*Claims, error) {
	tok, err := jwt.ParseWithClaims(raw, &Claims{}, func(t *jwt.Token) (any, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return secret, nil
	})
	if err != nil {
		return nil, err
	}
	claims, ok := tok.Claims.(*Claims)
	if !ok || !tok.Valid {
		return nil, errors.New("invalid token")
	}
	return claims, nil
}
