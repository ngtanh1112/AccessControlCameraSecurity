import { type FormEvent, useState } from "react";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { navigate } from "../routes/navigation";

const demoAccounts = [
  ["admin", "admin123"],
  ["manager", "manager123"],
  ["alice", "alice123"],
  ["bob", "bob123"],
] as const;

export function LoginPage() {
  const { signIn } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await signIn(username, password);
      navigate("/dashboard", true);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-layout">
      <section className="login-panel" aria-labelledby="login-title">
        <p className="eyebrow">LOCAL SECURITY CONSOLE</p>
        <h1 id="login-title">Access Control Camera Security</h1>
        <p className="login-intro">Sign in to view the cameras and zones assigned to your account.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor="username">Username</label>
          <input id="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          {error !== null && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" type="submit" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Login"}</button>
        </form>
        <aside className="demo-accounts" aria-label="Demo Accounts">
          <h2>Demo Accounts</h2>
          <ul>{demoAccounts.map(([demoUser, demoPassword]) => <li key={demoUser}><code>{demoUser} / {demoPassword}</code></li>)}</ul>
        </aside>
      </section>
    </main>
  );
}
