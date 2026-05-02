import axios from "axios";

// Single axios instance — `withCredentials: true` is critical so the
// browser sends our HttpOnly auth cookie on every request.
//
// baseURL is "/api" (relative): in dev Vite proxies it to the Go server;
// in prod the frontend would be served behind a reverse proxy that
// forwards /api/* to the backend (or VITE_API_BASE could swap this out).
export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Mirror of internal/httpx.ErrorBody on the Go side. Kept in sync by hand
// because the surface is tiny — see REPORT.md for why we did not pull in
// an OpenAPI generator for an assignment of this scope.
export type ApiError = {
  error: string;
  code?: string;
};
