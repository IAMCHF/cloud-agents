import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { base64Url, completeLogin, getAccessToken, pkceChallenge } from "./oidc";

const CONFIG = {
  mode: "oidc" as const,
  client_id: "web",
  authorization_endpoint: "https://idp.test/authorize",
  token_endpoint: "https://idp.test/token",
};

describe("oidc", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("derives the RFC 7636 S256 challenge", async () => {
    const verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
    expect(await pkceChallenge(verifier)).toBe("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
  });

  it("base64url encodes without padding", () => {
    expect(base64Url(new Uint8Array([251, 255, 190]))).toBe("-_--");
  });

  it("exchanges the code and stores the access token", async () => {
    window.sessionStorage.setItem(
      "cloud-agents.oidc.pkce",
      JSON.stringify({ verifier: "verifier-1", state: "state-1" }),
    );
    const fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify({ access_token: "access-1", expires_in: 300 }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const handled = await completeLogin(CONFIG, "?code=code-1&state=state-1");

    expect(handled).toBe(true);
    expect(getAccessToken()).toBe("access-1");
    const call = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(call[0]).toBe("https://idp.test/token");
    const body = String(call[1].body);
    expect(body).toContain("code_verifier=verifier-1");
    expect(body).toContain("code=code-1");
  });

  it("returns false when there is no callback code", async () => {
    expect(await completeLogin(CONFIG, "?session=s1&token=t1")).toBe(false);
  });

  it("rejects a mismatched state", async () => {
    window.sessionStorage.setItem(
      "cloud-agents.oidc.pkce",
      JSON.stringify({ verifier: "verifier-1", state: "state-1" }),
    );
    await expect(completeLogin(CONFIG, "?code=code-1&state=other")).rejects.toThrow("state");
  });
});
