"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import { api } from "@/lib/api";

export default function LoginPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState("checking");
  const [authEnabled, setAuthEnabled] = useState(false);

  useEffect(() => {
    api
      .health()
      .then((h: { status?: string; auth_enabled?: boolean }) => {
        setHealth(h.status === "ok" ? "ok" : "down");
        setAuthEnabled(Boolean(h.auth_enabled));
      })
      .catch(() => setHealth("down"));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const res = await api.login(username, password);
      localStorage.setItem("datamind_token", res.access_token);
      setMessage(`已登录为 ${res.user.username} (${res.user.global_role})`);
    } catch (err) {
      setError(String(err));
    }
  }

  function logout() {
    localStorage.removeItem("datamind_token");
    setMessage("已退出");
  }

  return (
    <AppShell topBar={<TopBar active="login" health={health} />}>
      <div className="mx-auto max-w-md px-6 py-10">
        <form onSubmit={onSubmit} className="panel space-y-3 rounded-md p-5">
          <h1 className="text-lg font-semibold">Login</h1>
          <p className="text-xs text-[var(--text-muted)]">
            AUTH_ENABLED={String(authEnabled)}
            {authEnabled
              ? " · 多用户已开启，请使用种子账号 admin / admin（可在 .env 修改）"
              : " · 当前为 Demo 模式（可不登录直接用分析台）。登录仍可用 admin / admin 获取 JWT。"}
          </p>
          <label className="block text-sm">
            <span className="text-[var(--text-muted)]">Username</span>
            <input className="input-dark mt-1 w-full" value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label className="block text-sm">
            <span className="text-[var(--text-muted)]">Password</span>
            <input
              className="input-dark mt-1 w-full"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <div className="flex gap-2">
            <button type="submit" className="btn btn-primary">
              Login
            </button>
            <button type="button" className="btn" onClick={logout}>
              Logout
            </button>
          </div>
          {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
          {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
        </form>
      </div>
    </AppShell>
  );
}
