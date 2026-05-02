// Package auth contains password hashing and JWT issuance/verification.
//
// Passwords are hashed with bcrypt — chosen because it is purpose-built for
// password storage (slow by design, automatic per-hash salt, tunable work
// factor). The hash format itself encodes the algorithm and cost, so
// future rotations to a higher cost can be done lazily on next login.
package auth

import "golang.org/x/crypto/bcrypt"

// HashPassword returns a bcrypt hash of password using the given cost. A
// cost of 0 falls back to bcrypt.DefaultCost (10). Production should use
// 12+; tests use 4 to keep them fast.
func HashPassword(password string, cost int) (string, error) {
	if cost == 0 {
		cost = bcrypt.DefaultCost
	}
	h, err := bcrypt.GenerateFromPassword([]byte(password), cost)
	if err != nil {
		return "", err
	}
	return string(h), nil
}

// CheckPassword reports whether password matches hash. bcrypt's
// CompareHashAndPassword is constant-time with respect to the password
// length, so it does not leak timing info about correctness.
func CheckPassword(hash, password string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(password)) == nil
}
