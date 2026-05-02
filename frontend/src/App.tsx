import { Navigate, Route, Routes } from "react-router-dom";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import Profile from "./pages/Profile";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

export default function App() {
  const { user, loading } = useAuth();

  return (
    <main className="app">
      <header className="topbar">
        <strong>Minimal Auth</strong>
        {!loading && user && <span className="muted">{user.email}</span>}
      </header>
      <Routes>
        <Route
          path="/"
          element={<Navigate to={user ? "/profile" : "/signin"} replace />}
        />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/signup" element={<SignUp />} />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  );
}
