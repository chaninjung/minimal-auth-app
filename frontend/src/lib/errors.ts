import axios from "axios";
import type { ApiError } from "../api/client";

// Pulls a user-friendly message out of an unknown thrown value. Centralised
// so every page renders error text the same way.
export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as ApiError | undefined;
    if (data?.error) return data.error;
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
