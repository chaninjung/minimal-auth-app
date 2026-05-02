import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { credentialsSchema, type CredentialsForm } from "../lib/schemas";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../lib/errors";

export default function SignUp() {
  const { signUp } = useAuth();
  const nav = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CredentialsForm>({
    resolver: zodResolver(credentialsSchema),
    mode: "onTouched",
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await signUp(values);
      nav("/profile", { replace: true });
    } catch (err) {
      setServerError(extractErrorMessage(err));
    }
  });

  return (
    <div className="card">
      <h1>Create account</h1>
      <form onSubmit={onSubmit} noValidate>
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            aria-invalid={!!errors.email}
            {...register("email")}
          />
          {errors.email && <span className="err">{errors.email.message}</span>}
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            {...register("password")}
          />
          {errors.password && (
            <span className="err">{errors.password.message}</span>
          )}
        </label>
        {serverError && <div className="err banner">{serverError}</div>}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="muted">
        Already have one? <Link to="/signin">Sign in</Link>
      </p>
    </div>
  );
}
