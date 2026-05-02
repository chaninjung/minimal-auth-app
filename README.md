# Minimal Auth App

A minimal authentication app:

- **Backend** — Python 3.13 + FastAPI, SQLite for persistence, bcrypt for passwords, JWT (HS256) carried in a HttpOnly cookie.
- **Frontend** — React 18 + TypeScript SPA (Vite), `react-hook-form` + `zod` for validation, Context API for auth state.

---

## Repository layout

```
.
├── .github/workflows/      # CI — backend pytest, frontend build/test
├── backend/                # Python / FastAPI server
│   ├── app/
│   │   ├── main.py         # FastAPI factory + lifespan + uvicorn entry
│   │   ├── config.py       # env-driven Settings (pydantic-settings)
│   │   ├── store.py        # SQLite repository
│   │   ├── schemas.py      # Pydantic request/response DTOs
│   │   ├── deps.py         # FastAPI Depends — auth / store injection
│   │   ├── rate_limit.py   # per-IP sliding-window limiter
│   │   ├── logging_setup.py # structlog JSON + request-id middleware
│   │   ├── services/       # password (bcrypt), token (JWT)
│   │   └── routers/        # auth, me
│   ├── tests/              # pytest — password, token, HTTP flow, rate limit
│   └── pyproject.toml
├── frontend/               # Vite + React + TS
│   ├── src/
│   │   ├── api/            # axios client + typed endpoints
│   │   ├── components/     # ProtectedRoute
│   │   ├── context/        # AuthContext / AuthProvider
│   │   ├── lib/            # zod schemas, error helpers
│   │   ├── pages/          # SignIn / SignUp / Profile
│   │   └── test/           # Vitest — schemas, errors, ProtectedRoute
│   └── package.json
└── README.md
```

---

## Prerequisites

| Tool   | Version                         |
| ------ | ------------------------------- |
| Python | ≥ 3.11 (developed on 3.13)      |
| Node   | ≥ 18 (developed on 24)          |
| npm    | ≥ 9                             |

No Docker, no native libraries to compile — SQLite is via Python's stdlib `sqlite3`.

---

## Run it

Open two terminals.

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:    .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
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

| Method | Path                  | Auth | Body                          | Success                                      |
| ------ | --------------------- | ---- | ----------------------------- | -------------------------------------------- |
| POST   | `/api/auth/signup`    | —    | `{ email, password }`         | `201 { id, email }`                          |
| POST   | `/api/auth/signin`    | —    | `{ email, password }`         | `200 { id, email }` + sets `rk_token` cookie |
| POST   | `/api/auth/signout`   | —    | (empty)                       | `204` + clears `rk_token`                    |
| GET    | `/api/me`             | ✅   | —                             | `200 { id, email }`                          |

FastAPI also exposes the auto-generated OpenAPI spec at `/openapi.json` and an interactive Swagger UI at `/docs`.

Validation rules (enforced on both sides):

- `email` — must contain `@`, length 3–254. Lower-cased on the server.
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

All config is environment-driven; sensible defaults let the server boot bare. Override with `JWT_SECRET=... python -m uvicorn app.main:app`, etc.

| Variable             | Default                  | Notes                                                            |
| -------------------- | ------------------------ | ---------------------------------------------------------------- |
| `HOST`               | `0.0.0.0`                | Listen host.                                                     |
| `PORT`               | `8080`                   | Listen port.                                                     |
| `DB_PATH`            | `data.db`                | SQLite file path.                                                |
| `JWT_SECRET`         | `dev-secret-change-me`   | **Override in any non-dev environment.**                         |
| `TOKEN_TTL_SECONDS`  | `86400` (24h)            | JWT validity in seconds.                                         |
| `ALLOWED_ORIGIN`     | `http://localhost:5173`  | CORS origin (single explicit value, no wildcards).               |
| `COOKIE_SECURE`      | `false`                  | Set `true` behind HTTPS so the cookie carries the `Secure` flag. |
| `BCRYPT_ROUNDS`      | `12`                     | bcrypt work factor (cost log2). Tests override to `4`.           |

---

## Tests

### Backend (pytest, 21 tests)

```bash
cd backend
pytest
```

- bcrypt round-trip, salt uniqueness, malformed-hash safety.
- JWT issue/parse, wrong secret rejected, expired token rejected, **`alg=none` rejected** (classic JWT confusion attack), garbage-token rejected.
- HTTP flow — sign-up created, duplicate (incl. case-insensitive) → 409, invalid email → 422, short password → 422, sign-in OK sets HttpOnly+SameSite cookie, bad password and unknown user return the **same** `401` (no enumeration), `/me` requires auth, sign-out returns `204`, full sign-up → sign-in → /me → sign-out integration.
- Rate limit — 11th sign-in within 1 min from one IP → `429`, 6th sign-up within 1 min → `429`.

### Frontend (Vitest, 10 tests)

```bash
cd frontend
npm test           # one-shot
npm run typecheck  # strict TS check
```

- Credential schema validation — accepts valid creds, rejects non-emails, short passwords, oversized passwords.
- Error-message extractor — pulls structured `error` field from backend responses, falls back gracefully.
- `ProtectedRoute` — redirects to `/signin` on bootstrap failure, renders children on success.

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs pytest, frontend typecheck, Vitest, and the production build on every push to `main` and every PR.

---

## Design summary

Headline trade-offs:

- **Auth transport: HttpOnly cookie, not `localStorage`.** `localStorage` is readable by any script on the origin (XSS = total compromise). HttpOnly + `SameSite=Lax` blocks both XSS theft and most CSRF vectors for our endpoints.
- **No silent email enumeration.** Sign-in returns the same generic error for "no such user" and "wrong password", and runs bcrypt unconditionally against a pre-baked dummy hash when the user does not exist — so the response time can't be used as a side channel either.
- **Strict TypeScript.** `strict`, `noUnusedLocals`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`.
- **Single source of validation rules** matched by hand between backend Pydantic schema (`app/schemas.py`) and frontend zod schema (`src/lib/schemas.ts`) — FastAPI auto-generates an OpenAPI spec from the Pydantic models, so a future migration to `openapi-typescript` on the frontend would close the loop with minimal extra effort.
