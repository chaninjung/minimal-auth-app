import { api } from "./client";

// Wire types — must match the Pydantic models in `app/schemas.py`
// on the backend and the validation schema in `src/lib/schemas.ts`.
export type User = {
  id: number;
  email: string;
};

export type Credentials = {
  email: string;
  password: string;
};

export const signUp = (creds: Credentials): Promise<User> =>
  api.post<User>("/auth/signup", creds);

export const signIn = (creds: Credentials): Promise<User> =>
  api.post<User>("/auth/signin", creds);

export const signOut = (): Promise<void> => api.post<void>("/auth/signout");

export const getMe = (): Promise<User> => api.get<User>("/me");
