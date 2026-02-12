"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AuthUser, getPortfolioSummary, getSubscription, login, PortfolioSummary, register } from "../lib/api";

type SessionState = {
  token: string;
  user: AuthUser;
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

export default function Page() {
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("changeme123");
  const [session, setSession] = useState<SessionState | null>(null);
  const [plan, setPlan] = useState("unknown");
  const [subscriptionStatus, setSubscriptionStatus] = useState("unknown");
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("session");
    if (!stored) {
      return;
    }
    try {
      setSession(JSON.parse(stored) as SessionState);
    } catch {
      window.localStorage.removeItem("session");
    }
  }, []);

  useEffect(() => {
    if (!session) {
      return;
    }
    window.localStorage.setItem("session", JSON.stringify(session));
    setLoading(true);
    setError("");

    Promise.all([getSubscription(session.token), getPortfolioSummary(session.token)])
      .then(([sub, summary]) => {
        setPlan(sub.plan);
        setSubscriptionStatus(sub.status);
        setPortfolio(summary);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "요청 중 오류가 발생했습니다.";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, [session]);

  const cards = useMemo(
    () => [
      { title: "총 자산", value: portfolio ? formatCurrency(portfolio.total_equity) : "-" },
      { title: "가용 잔고", value: portfolio ? formatCurrency(portfolio.available_balance) : "-" },
      { title: "일일 수익률", value: portfolio ? `${portfolio.daily_return_pct.toFixed(2)}%` : "-" },
      { title: "30일 Sharpe", value: portfolio ? portfolio.sharpe_30d.toFixed(2) : "-" },
      { title: "실현 손익", value: portfolio ? formatCurrency(portfolio.realized_pnl) : "-" },
      { title: "최대 낙폭", value: portfolio ? `${portfolio.max_drawdown_pct.toFixed(2)}%` : "-" }
    ],
    [portfolio]
  );

  async function handleLogin(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await login(email, password);
      setSession({ token: response.access_token, user: response.user });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "로그인 실패";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    setLoading(true);
    setError("");
    try {
      const response = await register(email, password);
      setSession({ token: response.access_token, user: response.user });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "회원가입 실패";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setSession(null);
    setPortfolio(null);
    setPlan("unknown");
    setSubscriptionStatus("unknown");
    window.localStorage.removeItem("session");
  }

  if (!session) {
    return (
      <main className="shell">
        <header className="topbar">
          <h1>Auto Investing Login</h1>
        </header>
        <section className="panel">
          <form className="form" onSubmit={handleLogin}>
            <label>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            </label>
            <label>
              Password
              <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
            </label>
            <div className="actions">
              <button type="submit" disabled={loading}>
                로그인
              </button>
              <button type="button" disabled={loading} onClick={handleRegister}>
                회원가입
              </button>
            </div>
          </form>
          <p className="muted">초기 테스트용: 계정이 없으면 회원가입 버튼을 누르면 됩니다.</p>
          {error ? <p className="error">{error}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="topbar">
        <h1>Auto Investing Dashboard</h1>
        <div className="headerRight">
          <span className="badge">{session.user.email}</span>
          <span className="badge">
            Plan: {plan} ({subscriptionStatus})
          </span>
          <button onClick={logout}>로그아웃</button>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {loading ? <p className="muted">데이터 로딩 중...</p> : null}

      <section className="grid">
        {cards.map((card) => (
          <article className="card" key={card.title}>
            <p className="label">{card.title}</p>
            <p className="value">{card.value}</p>
          </article>
        ))}
      </section>

      <section className="panel">
        <h2>실시간 투자 상태</h2>
        <p>현재는 REST 기반 요약을 표시합니다. Sprint 4에서 WebSocket으로 실시간 스트리밍 전환합니다.</p>
      </section>
    </main>
  );
}
