# Minimal Auth App

A minimal authentication app:

- **Backend** — Go 1.26 HTTP server with REST API, SQLite for persistence, bcrypt for passwords, JWT carried in a HttpOnly cookie.
- **Frontend** — React 18 + TypeScript SPA (Vite), `react-hook-form` + `zod` for validation, Context API for auth state.

---

## Repository layout

```
.
├── backend/                 # Go server
│   ├── cmd/server/          # main package (entry point)
│   ├── internal/
│   │   ├── auth/            # password hashing + JWT
│   │   ├── config/          # env-driven configuration
│   │   ├── handlers/        # HTTP handlers (+ tests)
│   │   ├── httpx/           # JSON helpers, error shape
│   │   ├── middleware/      # auth middleware
│   │   └── store/           # SQLite repository
│   └── go.mod
├── frontend/                # Vite + React + TS
│   ├── src/
│   │   ├── api/             # axios client + typed endpoints
│   │   ├── components/      # ProtectedRoute
│   │   ├── context/         # AuthContext / AuthProvider
│   │   ├── lib/             # zod schemas, error helpers
│   │   └── pages/           # SignIn / SignUp / Profile
│   └── package.json
└── README.md
```

---

## Prerequisites

| Tool | Version |
| ---- | ------- |
| Go   | ≥ 1.22 (developed on 1.26) |
| Node | ≥ 18 (developed on 24)     |
| npm  | ≥ 9                        |

No Docker / no C compiler required — `modernc.org/sqlite` is a pure-Go SQLite driver.

---

## Run it

Open two terminals.

### 1. Backend

```bash
cd backend
go mod tidy           # first run only
go run ./cmd/server
```

The server listens on `0.0.0.0:8080`. A `data.db` SQLite file is created in the working directory on first boot.

### 2. Frontend

```bash
cd frontend
npm install           # first run only
npm run dev
```

Open http://localhost:5173. Vite proxies `/api/*` to `http://localhost:8080`, so the browser sees a single same-origin app — no CORS dance required during dev.

### Health check

```bash
curl -i http://localhost:8080/healthz   # → 204
```

---

## API

All endpoints are under `/api`. Bodies are JSON.

| Method | Path                  | Auth | Body                          | Success                                    |
| ------ | --------------------- | ---- | ----------------------------- | ------------------------------------------ |
| POST   | `/api/auth/signup`    | —    | `{ email, password }`         | `201 { id, email }`                        |
| POST   | `/api/auth/signin`    | —    | `{ email, password }`         | `200 { id, email }` + sets `rk_token` cookie |
| POST   | `/api/auth/signout`   | —    | (empty)                       | `204` + clears `rk_token`                  |
| GET    | `/api/me`             | ✅   | —                             | `200 { id, email }`                        |

Validation rules (enforced on both sides):

- `email` — RFC-ish email, length 3–254.
- `password` — length 8–128.

Error shape:

```json
{ "error": "human-readable message", "code": "machine_code" }
```

### Quick `curl` exercise

```bash
curl -i -X POST http://localhost:8080/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"hunter2hunter2"}'

# Save the cookie jar so /me works
curl -i -c jar.txt -X POST http://localhost:8080/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"hunter2hunter2"}'

curl -i -b jar.txt http://localhost:8080/api/me
```

---

## Configuration

All config is environment-driven; sensible defaults let the server boot bare. Override with `ADDR=:9000 go run ./cmd/server`, etc.

| Variable         | Default                  | Notes                                                      |
| ---------------- | ------------------------ | ---------------------------------------------------------- |
| `ADDR`           | `0.0.0.0:8080`           | Listen address.                                            |
| `DB_PATH`        | `data.db`                | SQLite file path.                                          |
| `JWT_SECRET`     | `dev-secret-change-me`   | **Override in any non-dev environment.**                   |
| `TOKEN_TTL`      | `24h`                    | JWT validity (Go duration string).                         |
| `ALLOWED_ORIGIN` | `http://localhost:5173`  | CORS origin (single explicit value, no wildcards).         |
| `COOKIE_SECURE`  | `false`                  | Set `true` behind HTTPS so the cookie carries the `Secure` flag. |
| `BCRYPT_COST`    | `12`                     | Tests use `4` for speed.                                   |

---

## Tests

```bash
cd backend
go test ./...
```

Covers:

- bcrypt round-trip, salt uniqueness.
- JWT issue/parse, wrong secret rejected, expired token rejected, **`alg=none` rejected** (classic JWT confusion attack).
- HTTP handlers — sign-up created, duplicate (incl. case-insensitive) → 409, invalid email → 422, short password → 422, sign-in OK sets HttpOnly+SameSite cookie, bad password and unknown user return the **same** `401` (no enumeration), sign-out returns `204` and clears the cookie.

The frontend type-checks (`tsc --strict`) as part of `npm run build`.

---

## Design summary

Headline trade-offs:

- **Auth transport: HttpOnly cookie, not `localStorage`.** `localStorage` is readable by any script on the origin (XSS = total compromise). HttpOnly + `SameSite=Lax` blocks both XSS theft and most CSRF vectors for our endpoints.
- **No silent email enumeration.** Sign-in returns the same generic error for "no such user" and "wrong password".
- **Strict TypeScript.** `strict`, `noUnusedLocals`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`.
- **Single source of validation rules** matched by hand between backend (`internal/handlers/auth.go`) and frontend (`src/lib/schemas.ts`) — chosen deliberately over OpenAPI codegen at this surface size.
