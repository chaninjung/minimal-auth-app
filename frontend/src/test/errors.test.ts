import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";
import { extractErrorMessage } from "../lib/errors";

describe("extractErrorMessage", () => {
  it("pulls the `error` field from a structured backend response", () => {
    const headers = new AxiosHeaders();
    const err = new AxiosError(
      "Request failed with status code 401",
      "ERR_BAD_REQUEST",
      undefined,
      undefined,
      {
        status: 401,
        statusText: "Unauthorized",
        headers,
        config: { headers },
        data: { error: "invalid credentials", code: "invalid_credentials" },
      },
    );
    expect(extractErrorMessage(err)).toBe("invalid credentials");
  });

  it("falls back to the axios message when no body is attached", () => {
    const err = new AxiosError("Network Error");
    expect(extractErrorMessage(err)).toBe("Network Error");
  });

  it("uses Error.message for a plain Error", () => {
    expect(extractErrorMessage(new Error("boom"))).toBe("boom");
  });

  it("returns a sane default for unknown values", () => {
    expect(extractErrorMessage("some string")).toBe("Something went wrong");
    expect(extractErrorMessage(null)).toBe("Something went wrong");
  });
});
