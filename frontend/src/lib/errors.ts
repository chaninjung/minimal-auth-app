import { ApiException } from "../api/client";

// Pulls a user-friendly message out of an unknown thrown value.
// Centralised so every page renders error text the same way.
export function extractErrorMessage(err: unknown): string {
  if (err instanceof ApiException) {
    return err.body.error;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Something went wrong";
}
