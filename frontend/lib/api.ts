const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type AuthUser = {
  id: string;
  email: string;
  role: string;
  mfa_enabled: boolean;
  status: string;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
};

export type PortfolioSummary = {
  total_equity: number;
  available_balance: number;
  unrealized_pnl: number;
  realized_pnl: number;
  daily_return_pct: number;
  max_drawdown_pct: number;
  sharpe_30d: number;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function register(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function getSubscription(token: string): Promise<{ plan: string; status: string }> {
  return request<{ plan: string; status: string }>("/v1/billing/subscription", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function getPortfolioSummary(token: string): Promise<PortfolioSummary> {
  return request<PortfolioSummary>("/v1/portfolio/summary", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

