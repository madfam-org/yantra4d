/**
 * "Sign in with Janua" — the OIDC authorization-code + PKCE flow against
 * Janua's own provider endpoints: `GET /api/v1/oauth/authorize` (hosted login)
 * and `POST /api/v1/oauth/token` (form-encoded exchange).
 *
 * Why this lives in the Studio and not in `@janua/react-sdk`
 * -----------------------------------------------------------
 * The SDK the Studio ships (react-sdk 0.1.3/0.1.4 over typescript-sdk 0.1.3)
 * only exposes `signInWithOAuth(provider)`, which is the *social-login proxy*
 * flow: it navigates the browser to `GET /api/v1/auth/oauth/authorize/{provider}`.
 * Janua serves that path as POST only, so the navigation lands on a 405 JSON
 * page — and the social providers are not configured on auth.madfam.io anyway
 * (`/api/v1/auth/oauth/providers` answers an empty list). The SDK's callback
 * half is broken the same way: it POSTs JSON to `/api/v1/oauth/token`, a
 * standard OAuth 2.0 endpoint that consumes `application/x-www-form-urlencoded`
 * and answers 422 to JSON.
 *
 * The upstream fix already exists in the typescript-sdk *source*
 * (`Auth.getJanuaAuthorizeUrl`, `Auth.handleJanuaSSOCallback`,
 * `buildJanuaAuthorizeUrl`) but is not published. This module mirrors that
 * contract exactly — the same URL shape, the same key names for the PKCE
 * material and the same localStorage keys for the tokens — so the SDK's
 * `JanuaProvider` picks the session up on its next mount, and a later SDK bump
 * can delete this file without a migration. `januaSso.test.ts` pins the key
 * names against the installed SDK.
 *
 * One deliberate difference from the SDK: the PKCE material and the return
 * path live in localStorage, not sessionStorage. The Studio asks Janua's
 * hosted login for a magic link first (`login_method=magic_link`), and an
 * emailed link is opened wherever the person reads mail — usually a NEW tab.
 * sessionStorage is per tab, so the verifier minted in the first tab would be
 * invisible to the tab that receives the code, and every link-based sign-in
 * would die with "state did not match". localStorage is shared across tabs of
 * the origin; the material is one-time and is cleared on completion or failure.
 */

/** Key names shared with the SDK's `retrievePKCEParams()` / `validateState()`; kept in localStorage here (see the module doc). */
export const PKCE_STORAGE_KEYS = {
  codeVerifier: 'janua_pkce_verifier',
  state: 'janua_pkce_state',
} as const

/** localStorage keys the SDK's `JanuaProvider` hydrates its session from. */
export const TOKEN_STORAGE_KEYS = {
  accessToken: 'janua_access_token',
  refreshToken: 'janua_refresh_token',
  idToken: 'janua_id_token',
} as const

/** Where the page that asked for sign-in is remembered until the callback lands. */
export const RETURN_PATH_KEY = 'yantra4d_sign_in_return_path'

export const DEFAULT_SCOPES = 'openid profile email'

/**
 * Which method Janua's hosted login offers first. The Studio is a public PKCE
 * client whose people may hold no password at all (staff accounts were created
 * by invitation and social sign-in), so it asks for the emailed sign-in link;
 * the password form stays one click away on the hosted page. Janua ignores the
 * hint on builds that predate it.
 */
export type JanuaLoginMethod = 'magic_link' | 'password'
export const STUDIO_LOGIN_METHOD: JanuaLoginMethod = 'magic_link'

/**
 * Decode a JWT payload without verifying it. Returns the claims object, or
 * null when the token is malformed. Verification is the API's job; this only
 * reads unprivileged, self-asserted claims (here: `exp`).
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const b64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
    return JSON.parse(new TextDecoder().decode(bytes)) as Record<string, unknown>
  } catch {
    return null
  }
}

/**
 * The stored Janua access token if one is present and not past its `exp`,
 * else null. A token whose `exp` cannot be read is treated as usable — the
 * backend is the final authority and answers 401 if it is not.
 */
export function getStoredAccessToken(): string | null {
  try {
    const token = localStorage.getItem(TOKEN_STORAGE_KEYS.accessToken)
    if (!token) return null
    const claims = decodeJwtPayload(token)
    const exp = claims && typeof claims.exp === 'number' ? (claims.exp as number) : null
    if (exp !== null && exp * 1000 <= Date.now()) return null
    return token
  } catch {
    // localStorage can throw (Safari private mode, disabled storage).
    return null
  }
}

/**
 * Whether a usable Janua session is already in hand.
 *
 * "Signed in", for the Studio, means holding a live token for its OWN backend
 * (`api.yantra4d.com`, audience `yantra4d-api`) — which this OIDC flow stores.
 * The SDK's `isAuthenticated` cannot report that: it is `!!user`, and it loads
 * `user` from Janua's `GET /api/v1/auth/me`, an endpoint that rejects a
 * `yantra4d-api`-audience token with 401. So after a successful sign-in the
 * SDK still reports `isAuthenticated: false`, the private-project gate stays
 * locked and ManifestProvider never re-fetches with the token it already has.
 * AuthProvider ORs this in to close that gap. See
 * `AuthProvider.tsx` (JanuaBridge) and `ManifestProvider` (`signedIn`).
 */
export function hasStoredJanuaSession(): boolean {
  return getStoredAccessToken() !== null
}

/**
 * The `Authorization` header value for a fetch to `url`, or null when there is
 * no session or the URL is cross-origin. Private-project render artifacts
 * (`/static/<slug>_preview_*.glb|.stl`) are access-gated — an unauthenticated
 * GET returns 403 — and THREE's mesh loaders / the STL worker fetch them
 * outside `apiFetch`, so the token is attached explicitly here. Same-origin
 * only: never leak a `yantra4d-api` bearer to a third-party host.
 */
export function bearerHeaderForSameOrigin(url: string): string | null {
  const token = getStoredAccessToken()
  if (!token) return null
  try {
    if (new URL(url, window.location.href).origin !== window.location.origin) return null
  } catch {
    return null
  }
  return `Bearer ${token}`
}

export interface JanuaSsoConfig {
  /** Janua issuer, e.g. `https://auth.madfam.io`. */
  baseURL: string
  /** The Studio's registered OAuth client id. */
  clientId: string
  /**
   * Redirect URI exactly as registered on that client. Janua matches it
   * literally (no prefix matching), and derives its CORS allow-list from the
   * origins of active clients' redirect URIs.
   */
  redirectUri: string
}

export interface JanuaTokens {
  access_token: string
  token_type?: string
  expires_in?: number
  refresh_token?: string
  id_token?: string
  scope?: string
}

export class JanuaSignInError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'JanuaSignInError'
    this.status = status
  }
}

function base64Url(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** RFC 7636 code verifier: 32 random bytes, base64url (43 characters). */
export function generateCodeVerifier(): string {
  return base64Url(crypto.getRandomValues(new Uint8Array(32)))
}

/** RFC 7636 S256 challenge: base64url(SHA-256(verifier)). */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  return base64Url(new Uint8Array(digest))
}

/** CSRF state: 16 random bytes, base64url. */
export function generateState(): string {
  return base64Url(crypto.getRandomValues(new Uint8Array(16)))
}

/** Linear scan rather than `/\/+$/` — the same routine the SDK uses. */
export function stripTrailingSlashes(value: string): string {
  let end = value.length
  while (end > 0 && value.charCodeAt(end - 1) === 47 /* '/' */) end -= 1
  return value.slice(0, end)
}

export interface AuthorizeUrlParams {
  baseURL: string
  clientId: string
  redirectUri: string
  codeChallenge: string
  state: string
  scopes?: string
  nonce?: string
  prompt?: string
  /** Hosted-login method to offer first (`login_method=`); omitted when undefined. */
  loginMethod?: JanuaLoginMethod
}

/**
 * Build the Janua OIDC provider authorization URL (`GET /api/v1/oauth/authorize`).
 * Mirrors the SDK's `buildJanuaAuthorizeUrl` parameter for parameter.
 */
export function buildJanuaAuthorizeUrl(params: AuthorizeUrlParams): string {
  const {
    baseURL, clientId, redirectUri, codeChallenge, state,
    scopes = DEFAULT_SCOPES, nonce, prompt, loginMethod,
  } = params
  const url = new URL(`${stripTrailingSlashes(baseURL)}/api/v1/oauth/authorize`)
  url.searchParams.set('response_type', 'code')
  url.searchParams.set('client_id', clientId)
  url.searchParams.set('redirect_uri', redirectUri)
  url.searchParams.set('scope', scopes)
  url.searchParams.set('code_challenge', codeChallenge)
  url.searchParams.set('code_challenge_method', 'S256')
  url.searchParams.set('state', state)
  if (nonce) url.searchParams.set('nonce', nonce)
  if (prompt) url.searchParams.set('prompt', prompt)
  if (loginMethod) url.searchParams.set('login_method', loginMethod)
  return url.toString()
}

/**
 * Only a same-origin absolute path may be used as a post-sign-in destination.
 * Anything with a scheme or an authority (`https://…`, `//evil`, `javascript:`)
 * is dropped, so the value that comes back out of storage can never redirect
 * off-site.
 */
export function sanitizeReturnPath(candidate: string | null | undefined): string | null {
  if (typeof candidate !== 'string') return null
  const value = candidate.trim()
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return null
  return value
}

function currentPath(): string {
  const { pathname, search, hash } = window.location
  return `${pathname}${search}${hash}`
}

function clearPkce(): void {
  localStorage.removeItem(PKCE_STORAGE_KEYS.codeVerifier)
  localStorage.removeItem(PKCE_STORAGE_KEYS.state)
}

export interface BeginSignInOptions {
  /** Same-origin path to return to after the callback; defaults to the current page. */
  returnTo?: string
  /** Hosted-login method to ask for first; defaults to the Studio's (`magic_link`). */
  loginMethod?: JanuaLoginMethod
  /** Navigation hook, injectable for tests. Defaults to `window.location.assign`. */
  navigate?: (url: string) => void
}

/**
 * Start the flow: mint the PKCE material, persist it (plus the return path)
 * and send the browser to Janua's hosted login. Resolves with the URL used.
 */
export async function beginJanuaSignIn(
  config: JanuaSsoConfig,
  options: BeginSignInOptions = {},
): Promise<string> {
  const verifier = generateCodeVerifier()
  const challenge = await generateCodeChallenge(verifier)
  const state = generateState()

  localStorage.setItem(PKCE_STORAGE_KEYS.codeVerifier, verifier)
  localStorage.setItem(PKCE_STORAGE_KEYS.state, state)

  const returnTo = sanitizeReturnPath(options.returnTo ?? currentPath())
  if (returnTo) localStorage.setItem(RETURN_PATH_KEY, returnTo)
  else localStorage.removeItem(RETURN_PATH_KEY)

  const url = buildJanuaAuthorizeUrl({
    baseURL: config.baseURL,
    clientId: config.clientId,
    redirectUri: config.redirectUri,
    codeChallenge: challenge,
    state,
    loginMethod: options.loginMethod ?? STUDIO_LOGIN_METHOD,
  })
  const navigate = options.navigate ?? ((target: string) => window.location.assign(target))
  navigate(url)
  return url
}

/** Janua answers errors as `{error:{message}}`, FastAPI as `{detail}`; OAuth as `error_description`. */
function errorDetail(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>
    const nested = record.error
    if (nested && typeof nested === 'object' && typeof (nested as Record<string, unknown>).message === 'string') {
      return (nested as Record<string, string>).message
    }
    for (const key of ['detail', 'error_description', 'error', 'message']) {
      if (typeof record[key] === 'string') return record[key] as string
    }
  }
  return fallback
}

/**
 * Finish the flow on the callback page: validate `state`, exchange the code
 * with the stored verifier (form-encoded, public client — no secret) and store
 * the tokens where `JanuaProvider` reads them on mount. The PKCE material is
 * one-time and is cleared whether the exchange succeeds or fails.
 */
export async function completeJanuaSignIn(
  config: JanuaSsoConfig,
  code: string,
  state: string,
  fetchImpl: typeof fetch = fetch,
): Promise<JanuaTokens> {
  const storedState = localStorage.getItem(PKCE_STORAGE_KEYS.state)
  const verifier = localStorage.getItem(PKCE_STORAGE_KEYS.codeVerifier)

  if (!code) {
    clearPkce()
    throw new JanuaSignInError('Authorization code is missing from the callback')
  }
  if (!storedState || storedState !== state) {
    clearPkce()
    throw new JanuaSignInError('Sign-in state did not match — the flow was not started from this browser')
  }
  if (!verifier) {
    clearPkce()
    throw new JanuaSignInError('PKCE verifier is missing — start the sign-in again')
  }

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: config.redirectUri,
    client_id: config.clientId,
    code_verifier: verifier,
  })

  let response: Response
  try {
    response = await fetchImpl(`${stripTrailingSlashes(config.baseURL)}/api/v1/oauth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    })
  } finally {
    clearPkce()
  }

  if (!response.ok) {
    const parsed = await response.json().catch(() => null)
    throw new JanuaSignInError(
      errorDetail(parsed, `Token exchange failed (${response.status})`),
      response.status,
    )
  }

  const tokens = (await response.json()) as JanuaTokens
  if (!tokens || typeof tokens.access_token !== 'string' || !tokens.access_token) {
    throw new JanuaSignInError('Token exchange answered without an access token')
  }

  localStorage.setItem(TOKEN_STORAGE_KEYS.accessToken, tokens.access_token)
  if (tokens.refresh_token) localStorage.setItem(TOKEN_STORAGE_KEYS.refreshToken, tokens.refresh_token)
  if (tokens.id_token) localStorage.setItem(TOKEN_STORAGE_KEYS.idToken, tokens.id_token)
  return tokens
}

/** Read and forget the remembered return path; `null` when there is none or it is unsafe. */
export function consumeReturnPath(): string | null {
  const stored = localStorage.getItem(RETURN_PATH_KEY)
  localStorage.removeItem(RETURN_PATH_KEY)
  return sanitizeReturnPath(stored)
}
