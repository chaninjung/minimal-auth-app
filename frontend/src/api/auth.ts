import { api } from "./client";

// Wire types — must match the Go handlers' DTO (userView in
// internal/handlers/auth.go and the credBody body shape).
export type User = {
  id: number;
  email: string;
};

export type Credentials = {
  email: string;
  password: string;
};

export async function signUp(creds: Credentials): Promise<User> {
  const { data } = await api.post<User>("/auth/signup", creds);
  return data;
}

export async function signIn(creds: Credentials): Promise<User> {
  const { data } = await api.post<User>("/auth/signin", creds);
  return data;
}

export async function signOut(): Promise<void> {
  await api.post("/auth/signout");
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/me");
  return data;
}
