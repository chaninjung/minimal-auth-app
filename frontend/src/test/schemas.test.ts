import { describe, expect, it } from "vitest";
import { credentialsSchema } from "../lib/schemas";

describe("credentialsSchema", () => {
  it("accepts a valid email and 8+ char password", () => {
    const result = credentialsSchema.safeParse({
      email: "alice@example.com",
      password: "hunter2hunter2",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a non-email string", () => {
    const result = credentialsSchema.safeParse({
      email: "not-an-email",
      password: "hunter2hunter2",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(["email"]);
    }
  });

  it("rejects passwords shorter than 8 characters", () => {
    const result = credentialsSchema.safeParse({
      email: "x@y.com",
      password: "short",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(["password"]);
    }
  });

  it("rejects passwords longer than 128 characters", () => {
    const result = credentialsSchema.safeParse({
      email: "x@y.com",
      password: "a".repeat(129),
    });
    expect(result.success).toBe(false);
  });
});
