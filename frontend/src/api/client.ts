// HTTP client — a thin wrapper over the platform `fetch`.
//
// Why not axios:
//   - axios adds ~13 KB to the bundle for ergonomics that we can
//     reproduce in ~30 lines.
//   - `fetch` is the platform primitive. Using it directly keeps the
//     dependency surface smaller and doesn't hide the contract.
//
// What this wrapper buys us:
//   - `credentials: "include"` baked in, so the browser sends our
//     HttpOnly auth cookie on every request.
//   - JSON serialisation / deserialisation handled once.
//   - Non-2xx responses surface as a typed `ApiException` carrying the
//     standard `{ error, code }` envelope from the backend, so callers
//     can do `try/catch` and `extractErrorMessage(err)` uniformly.
//
// `baseURL` is "/api" (relative): in dev Vite proxies it to the FastAPI
// server; in production the SPA would be served behind a reverse proxy
// that forwards /api/* to the backend.

export type ApiError = {
  error: string;
  code?: string;
};

/** Thrown for any non-2xx response. */
export class ApiException extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiError,
  ) {
    super(body.error);
    this.name = "ApiException";
  }
}

const BASE = "/api";

async function request<T>(
  method: "GET" | "POST",
  path: string,
  body?: unknown,
): Promise<T> {
  const init: RequestInit = {
    method,
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  const response = await fetch(`${BASE}${path}`, init);

  if (!response.ok) {
    // Try to read the standard error envelope; fall back to status text
    // if the body isn't JSON (e.g. a network-edge 502).
    const fallback: ApiError = { error: response.statusText || "request failed" };
    let errBody: ApiError = fallback;
    try {
      errBody = (await response.json()) as ApiError;
    } catch {
      // ignore — keep the fallback
    }
    throw new ApiException(response.status, errBody);
  }

  // 204 No Content has no body; the caller's generic should be `void`.
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
};
