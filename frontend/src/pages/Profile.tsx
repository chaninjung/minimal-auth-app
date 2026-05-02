import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../lib/errors";

export default function Profile() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ProtectedRoute guarantees user is non-null by the time this renders,
  // but TypeScript still needs the narrowing.
  if (!user) return null;

  async function onSignOut() {
    setBusy(true);
    setError(null);
    try {
      await signOut();
      nav("/signin", { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h1>Profile</h1>
      <dl>
        <dt>ID</dt>
        <dd>{user.id}</dd>
        <dt>Email</dt>
        <dd>{user.email}</dd>
      </dl>
      {error && <div className="err banner">{error}</div>}
      <button onClick={onSignOut} disabled={busy}>
        {busy ? "Signing out…" : "Sign out"}
      </button>
    </div>
  );
}
