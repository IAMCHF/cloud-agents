/** OIDC 授权码 + PKCE（SPA 公共客户端）；token 只存 sessionStorage，不落构建产物。 */

export interface AuthConfig {
  mode: "token" | "oidc";
  issuer?: string;
  client_id?: string;
  scope?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
}

interface StoredTokens {
  accessToken: string;
  expiresAt: number;
}

interface PkceState {
  verifier: string;
  state: string;
}

const TOKEN_KEY = "cloud-agents.oidc.tokens";
const PKCE_KEY = "cloud-agents.oidc.pkce";
const EXPIRY_MARGIN_MS = 30_000;

export async function loadAuthConfig(): Promise<AuthConfig> {
  const response = await fetch("/api/auth/config");
  if (!response.ok) {
    throw new Error(`认证配置获取失败：${response.status}`);
  }
  return (await response.json()) as AuthConfig;
}

export function getAccessToken(now = Date.now()): string | null {
  const raw = window.sessionStorage.getItem(TOKEN_KEY);
  if (raw === null) {
    return null;
  }
  try {
    const stored = JSON.parse(raw) as StoredTokens;
    return stored.expiresAt > now ? stored.accessToken : null;
  } catch {
    return null;
  }
}

export function clearAccessToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY);
}

export function redirectUri(): string {
  return `${window.location.origin}${window.location.pathname}`;
}

export function createVerifier(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return base64Url(bytes);
}

export async function pkceChallenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64Url(new Uint8Array(digest));
}

export function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function beginLogin(config: AuthConfig): Promise<void> {
  if (config.authorization_endpoint === undefined || config.client_id === undefined) {
    throw new Error("OIDC 配置不完整");
  }
  const verifier = createVerifier();
  const state = base64Url(crypto.getRandomValues(new Uint8Array(16)));
  const pending: PkceState = { verifier, state };
  window.sessionStorage.setItem(PKCE_KEY, JSON.stringify(pending));

  const url = new URL(config.authorization_endpoint);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", config.client_id);
  url.searchParams.set("redirect_uri", redirectUri());
  url.searchParams.set("scope", config.scope ?? "openid profile email");
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", await pkceChallenge(verifier));
  url.searchParams.set("code_challenge_method", "S256");
  window.location.assign(url.toString());
}

/** 处理回调：换 token 后清理地址栏；没有 code 时返回 false。 */
export async function completeLogin(
  config: AuthConfig,
  search: string = window.location.search,
): Promise<boolean> {
  const params = new URLSearchParams(search);
  const code = params.get("code");
  const state = params.get("state");
  if (code === null || state === null) {
    return false;
  }
  if (config.token_endpoint === undefined || config.client_id === undefined) {
    throw new Error("OIDC 配置不完整");
  }
  const pending = readPending();
  if (pending === null || pending.state !== state) {
    throw new Error("OIDC state 不匹配");
  }
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri(),
    client_id: config.client_id,
    code_verifier: pending.verifier,
  });
  const response = await fetch(config.token_endpoint, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    throw new Error(`登录失败：${response.status}`);
  }
  const payload = (await response.json()) as { access_token?: string; expires_in?: number };
  if (payload.access_token === undefined) {
    throw new Error("登录响应缺少 access_token");
  }
  const expiresInMs = (payload.expires_in ?? 300) * 1000;
  const tokens: StoredTokens = {
    accessToken: payload.access_token,
    expiresAt: Date.now() + expiresInMs - EXPIRY_MARGIN_MS,
  };
  window.sessionStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  window.sessionStorage.removeItem(PKCE_KEY);
  window.history.replaceState({}, "", window.location.pathname);
  return true;
}

function readPending(): PkceState | null {
  const raw = window.sessionStorage.getItem(PKCE_KEY);
  if (raw === null) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as PkceState;
    return parsed.verifier && parsed.state ? parsed : null;
  } catch {
    return null;
  }
}
