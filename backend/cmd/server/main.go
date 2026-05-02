// Command server is the HTTP entry point. It wires config -> store ->
// handlers -> router and runs ListenAndServe with graceful shutdown.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	chimw "github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"github.com/chaninjung/minimal-auth-app/internal/config"
	"github.com/chaninjung/minimal-auth-app/internal/handlers"
	"github.com/chaninjung/minimal-auth-app/internal/middleware"
	"github.com/chaninjung/minimal-auth-app/internal/store"
)

func main() {
	cfg := config.FromEnv()

	s, err := store.Open(cfg.DBPath)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	defer s.Close()

	if err := s.Migrate(context.Background()); err != nil {
		log.Fatalf("migrate: %v", err)
	}

	r := chi.NewRouter()

	// Standard cross-cutting middleware. Logger/Recoverer are essentials
	// for ops; Timeout caps slow handlers; RequestID tags each request for
	// log correlation.
	r.Use(chimw.RequestID)
	r.Use(chimw.RealIP)
	r.Use(chimw.Logger)
	r.Use(chimw.Recoverer)
	r.Use(chimw.Timeout(15 * time.Second))

	// CORS: tightly scoped — single origin, no wildcards, credentials on
	// (so the browser sends our HttpOnly cookie). In dev, the frontend
	// uses Vite's proxy so requests are same-origin and CORS isn't
	// exercised; this config kicks in if the frontend is hosted separately.
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{cfg.AllowedOrigin},
		AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodOptions},
		AllowedHeaders:   []string{"Content-Type"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	authHandler := &handlers.Auth{Cfg: cfg, Store: s}
	meHandler := &handlers.Me{Store: s}

	r.Route("/api", func(r chi.Router) {
		r.Post("/auth/signup", authHandler.SignUp)
		r.Post("/auth/signin", authHandler.SignIn)
		r.Post("/auth/signout", authHandler.SignOut)

		r.Group(func(r chi.Router) {
			r.Use(middleware.Auth(cfg.JWTSecret))
			r.Get("/me", meHandler.Get)
		})
	})

	r.Get("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})

	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           r,
		ReadHeaderTimeout: 5 * time.Second,
	}

	// Run the server, then block on signals for graceful shutdown.
	go func() {
		log.Printf("listening on %s (origin=%s)", cfg.Addr, cfg.AllowedOrigin)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("listen: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("shutting down…")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("shutdown: %v", err)
	}
}
