// Package store is the persistence layer. SQLite was chosen because it
// requires zero setup (single file), and modernc.org/sqlite is a pure-Go
// driver — no CGO, so the binary builds cleanly on every platform.
//
// In production this would be swapped for Postgres; the *Store type
// exposes a small set of methods (CreateUser, UserByEmail, UserByID) that
// could become an interface to allow that swap without touching handlers.
package store

import (
	"context"
	"database/sql"
	"errors"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

// Errors surfaced to the handler layer. We map driver-specific errors here
// so callers don't need to know about SQLite internals.
var (
	ErrEmailTaken   = errors.New("email already registered")
	ErrUserNotFound = errors.New("user not found")
)

// User mirrors the row in the users table. Fields are unexported elsewhere
// in the response path — handlers project this to a public DTO that does
// not include PasswordHash.
type User struct {
	ID           int64
	Email        string
	PasswordHash string
	CreatedAt    time.Time
}

type Store struct {
	db *sql.DB
}

// Open opens (and creates if missing) a SQLite database at path. SQLite
// allows only one writer at a time, so we cap MaxOpenConns to 1 to avoid
// "database is locked" errors under concurrent writes from a single
// process — adequate for an assignment-scale workload.
func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

// Migrate creates tables if they don't exist. Idempotent — safe to call
// every boot.
func (s *Store) Migrate(ctx context.Context) error {
	_, err := s.db.ExecContext(ctx, `
		CREATE TABLE IF NOT EXISTS users (
			id            INTEGER PRIMARY KEY AUTOINCREMENT,
			email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
			password_hash TEXT NOT NULL,
			created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		);
	`)
	return err
}

// CreateUser inserts a new user. Returns ErrEmailTaken if the email is
// already registered (case-insensitive thanks to COLLATE NOCASE).
func (s *Store) CreateUser(ctx context.Context, email, passwordHash string) (*User, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO users (email, password_hash) VALUES (?, ?)`,
		email, passwordHash,
	)
	if err != nil {
		if isUniqueViolation(err) {
			return nil, ErrEmailTaken
		}
		return nil, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, err
	}
	return s.UserByID(ctx, id)
}

func (s *Store) UserByEmail(ctx context.Context, email string) (*User, error) {
	var u User
	err := s.db.QueryRowContext(ctx,
		`SELECT id, email, password_hash, created_at FROM users WHERE email = ? COLLATE NOCASE`,
		email,
	).Scan(&u.ID, &u.Email, &u.PasswordHash, &u.CreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrUserNotFound
	}
	if err != nil {
		return nil, err
	}
	return &u, nil
}

func (s *Store) UserByID(ctx context.Context, id int64) (*User, error) {
	var u User
	err := s.db.QueryRowContext(ctx,
		`SELECT id, email, password_hash, created_at FROM users WHERE id = ?`,
		id,
	).Scan(&u.ID, &u.Email, &u.PasswordHash, &u.CreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrUserNotFound
	}
	if err != nil {
		return nil, err
	}
	return &u, nil
}

// modernc.org/sqlite reports unique violations as a plain error containing
// "UNIQUE constraint failed". Matching on the message is brittle, so this
// is the one place that knows the driver-specific phrasing.
func isUniqueViolation(err error) bool {
	if err == nil {
		return false
	}
	return strings.Contains(err.Error(), "UNIQUE constraint failed")
}
