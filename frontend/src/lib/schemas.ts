import { z } from "zod";

// zod was chosen as the validator because (a) it produces the TypeScript
// type as a side-effect of the schema, eliminating the dual-source-of-truth
// problem, and (b) it integrates cleanly with react-hook-form via
// @hookform/resolvers/zod.
//
// Rules mirror the backend (internal/handlers/auth.go validateCreds):
//   - email contains @, length 3..254
//   - password length 8..128
//
// The frontend validates eagerly to give fast feedback; the backend
// re-validates because we never trust the client.
export const credentialsSchema = z.object({
  email: z
    .string()
    .min(3, "email is too short")
    .max(254, "email is too long")
    .email("enter a valid email"),
  password: z
    .string()
    .min(8, "at least 8 characters")
    .max(128, "at most 128 characters"),
});

export type CredentialsForm = z.infer<typeof credentialsSchema>;
