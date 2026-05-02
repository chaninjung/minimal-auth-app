import { describe, expect, it } from "vitest";
import { ApiException } from "../api/client";
import { extractErrorMessage } from "../lib/errors";

describe("extractErrorMessage", () => {
  it("pulls the `error` field from a structured backend response", () => {
    const err = new ApiException(401, {
      error: "invalid credentials",
      code: "invalid_credentials",
    });
    expect(extractErrorMessage(err)).toBe("invalid credentials");
  });

  it("falls back to Error.message for a plain Error", () => {
    expect(extractErrorMessage(new Error("boom"))).toBe("boom");
  });

  it("returns a sane default for unknown values", () => {
    expect(extractErrorMessage("some string")).toBe("Something went wrong");
    expect(extractErrorMessage(null)).toBe("Something went wrong");
  });

  it("ApiException is a subclass of Error and carries status + body", () => {
    const err = new ApiException(429, {
      error: "too many requests",
      code: "rate_limited",
    });
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(429);
    expect(err.body.code).toBe("rate_limited");
  });
});
