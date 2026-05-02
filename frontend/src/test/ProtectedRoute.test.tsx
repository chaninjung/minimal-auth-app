import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

// We need to mock the auth API before importing anything that pulls
// it transitively (AuthContext imports it). vi.mock is hoisted so this
// runs before the imports below.
vi.mock("../api/auth", () => ({
  getMe: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
}));

import { getMe } from "../api/auth";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AuthProvider } from "../context/AuthContext";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/signin" element={<div>signin page</div>} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <div>profile page</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("redirects to /signin when the bootstrap getMe() rejects (no session)", async () => {
    vi.mocked(getMe).mockRejectedValueOnce(new Error("401"));

    renderAt("/profile");

    // Wait for the bootstrap to settle and the redirect to land.
    expect(await screen.findByText("signin page")).toBeInTheDocument();
    expect(screen.queryByText("profile page")).not.toBeInTheDocument();
  });

  it("renders the protected content when getMe() resolves with a user", async () => {
    vi.mocked(getMe).mockResolvedValueOnce({ id: 1, email: "alice@example.com" });

    renderAt("/profile");

    expect(await screen.findByText("profile page")).toBeInTheDocument();
    expect(screen.queryByText("signin page")).not.toBeInTheDocument();
  });
});
