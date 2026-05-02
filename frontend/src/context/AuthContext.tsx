import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getMe,
  signIn as apiSignIn,
  signOut as apiSignOut,
  signUp as apiSignUp,
  type Credentials,
  type User,
} from "../api/auth";

// Why Context (not Redux/Zustand): the entire shared state for this app is
// a single User | null plus three async actions. Pulling in a state library
// would be ceremony for ceremony's sake. Context + useState is enough and
// keeps the dependency footprint small.
//
// The provider runs a single `getMe()` on mount to bootstrap the auth
// state from the cookie. While that request is in flight, `loading` is
// true so ProtectedRoute does not flicker through a redirect.

type AuthState = {
  user: User | null;
  loading: boolean;
};

type AuthContextValue = AuthState & {
  signIn: (c: Credentials) => Promise<void>;
  signUp: (c: Credentials) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const u = await getMe();
        if (!cancelled) setState({ user: u, loading: false });
      } catch {
        // 401 here just means "not signed in" — perfectly normal on first
        // visit. We swallow it and let the routes decide what to render.
        if (!cancelled) setState({ user: null, loading: false });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (c: Credentials) => {
    const u = await apiSignIn(c);
    setState({ user: u, loading: false });
  }, []);

  const signUp = useCallback(async (c: Credentials) => {
    await apiSignUp(c);
    // UX choice: auto-sign-in after sign-up so the user lands directly on
    // the protected page instead of being bounced to /signin.
    const u = await apiSignIn(c);
    setState({ user: u, loading: false });
  }, []);

  const signOut = useCallback(async () => {
    await apiSignOut();
    setState({ user: null, loading: false });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, signIn, signUp, signOut }),
    [state, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
