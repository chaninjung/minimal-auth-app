import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../context/AuthContext";

// ProtectedRoute waits for the initial auth bootstrap (loading=true) so we
// don't flash a redirect to /signin for users who are actually signed in.
// Once loaded, it either renders children or redirects, preserving the
// originally requested location in `state.from` so we could return there
// after sign-in (left as a small future enhancement).
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="center muted">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/signin" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}
