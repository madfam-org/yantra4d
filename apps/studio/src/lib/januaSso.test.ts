import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createHash, webcrypto } from 'node:crypto'
import {
  PKCE_STORAGE_KEYS,
  TOKEN_STORAGE_KEYS,
  RETURN_PATH_KEY,
  JanuaSignInError,
  beginJanuaSignIn,
  buildJanuaAuthorizeUrl,
  completeJanuaSignIn,
  consumeReturnPath,
  generateCodeChallenge,
  generateCodeVerifier,
  generateState,
  sanitizeReturnPath,
  stripTrailingSlashes,
  getStoredAccessToken,
  hasStoredJanuaSession,
} from './januaSso'

// jsdom ships getRandomValues but not SubtleCrypto; the S256 challenge needs it.
if (!globalThis.crypto?.subtle) {
  vi.stubGlobal('crypto', webcrypto)
}

// The real react-sdk requires @janua/ui, whose package resolves to TypeScript
// sources under node_modules that vitest will not transform. The contract test
// below only needs the SDK's storage-key constants, so the UI package is
// stubbed for this file while the SDK itself is imported for real.
vi.mock('@janua/ui', () => ({}))

const CONFIG = {
  baseURL: 'https://auth.example.test/',
  clientId: 'jnc_test',
  redirectUri: 'https://studio.example.test',
}

const base64UrlSha256 = (value: string) =>
  createHash('sha256').update(value).digest('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')

beforeEach(() => {
  localStorage.clear()
  localStorage.clear()
})

describe('PKCE material', () => {
  it('mints a 43-character base64url verifier and a matching S256 challenge', async () => {
    const verifier = generateCodeVerifier()
    expect(verifier).toMatch(/^[A-Za-z0-9_-]{43}$/)
    expect(await generateCodeChallenge(verifier)).toBe(base64UrlSha256(verifier))
  })

  it('mints a base64url state that differs between calls', () => {
    const a = generateState()
    expect(a).toMatch(/^[A-Za-z0-9_-]{22}$/)
    expect(generateState()).not.toBe(a)
  })
})

describe('buildJanuaAuthorizeUrl', () => {
  it('targets the OIDC provider endpoint, not the social proxy, with every required parameter', () => {
    const url = new URL(buildJanuaAuthorizeUrl({
      baseURL: 'https://auth.example.test///',
      clientId: 'jnc_test',
      redirectUri: 'https://studio.example.test',
      codeChallenge: 'chal',
      state: 'st',
    }))
    expect(url.origin + url.pathname).toBe('https://auth.example.test/api/v1/oauth/authorize')
    expect(url.pathname).not.toContain('/auth/oauth/authorize/')
    expect(Object.fromEntries(url.searchParams)).toEqual({
      response_type: 'code',
      client_id: 'jnc_test',
      redirect_uri: 'https://studio.example.test',
      scope: 'openid profile email',
      code_challenge: 'chal',
      code_challenge_method: 'S256',
      state: 'st',
    })
  })

  it('asks the hosted login for a method only when told to', () => {
    const plain = new URL(buildJanuaAuthorizeUrl({ baseURL: CONFIG.baseURL, clientId: 'c', redirectUri: 'r', codeChallenge: 'x', state: 's' }))
    expect(plain.searchParams.has('login_method')).toBe(false)
    const magic = new URL(buildJanuaAuthorizeUrl({ baseURL: CONFIG.baseURL, clientId: 'c', redirectUri: 'r', codeChallenge: 'x', state: 's', loginMethod: 'magic_link' }))
    expect(magic.searchParams.get('login_method')).toBe('magic_link')
  })

  it('adds nonce and prompt only when given', () => {
    const url = new URL(buildJanuaAuthorizeUrl({
      baseURL: CONFIG.baseURL, clientId: 'c', redirectUri: 'r', codeChallenge: 'x', state: 's',
      nonce: 'n1', prompt: 'none', scopes: 'openid',
    }))
    expect(url.searchParams.get('nonce')).toBe('n1')
    expect(url.searchParams.get('prompt')).toBe('none')
    expect(url.searchParams.get('scope')).toBe('openid')
  })

  it('strips trailing slashes without a regex', () => {
    expect(stripTrailingSlashes('https://a.test///')).toBe('https://a.test')
    expect(stripTrailingSlashes('https://a.test')).toBe('https://a.test')
    expect(stripTrailingSlashes('')).toBe('')
  })
})

describe('sanitizeReturnPath', () => {
  it('keeps same-origin absolute paths with query and hash', () => {
    expect(sanitizeReturnPath('/project/tablaco?x=1#view')).toBe('/project/tablaco?x=1#view')
    expect(sanitizeReturnPath('  /projects ')).toBe('/projects')
  })

  it('drops anything that could leave the origin', () => {
    for (const bad of ['//evil.test/x', '/\\evil.test', 'https://evil.test', 'javascript:alert(1)', 'projects', '', null, undefined]) {
      expect(sanitizeReturnPath(bad)).toBeNull()
    }
  })
})

describe('beginJanuaSignIn', () => {
  it('persists the PKCE material under the SDK keys, remembers the page, and navigates to Janua', async () => {
    const navigate = vi.fn()
    const url = new URL(await beginJanuaSignIn(CONFIG, { returnTo: '/project/tablaco', navigate }))

    expect(navigate).toHaveBeenCalledWith(url.toString())
    expect(url.origin + url.pathname).toBe('https://auth.example.test/api/v1/oauth/authorize')

    const verifier = localStorage.getItem(PKCE_STORAGE_KEYS.codeVerifier)
    const state = localStorage.getItem(PKCE_STORAGE_KEYS.state)
    expect(verifier).toMatch(/^[A-Za-z0-9_-]{43}$/)
    expect(url.searchParams.get('code_challenge')).toBe(base64UrlSha256(verifier!))
    expect(url.searchParams.get('state')).toBe(state)
    expect(url.searchParams.get('client_id')).toBe('jnc_test')
    expect(url.searchParams.get('redirect_uri')).toBe('https://studio.example.test')
    expect(localStorage.getItem(RETURN_PATH_KEY)).toBe('/project/tablaco')
    // The Studio asks for the emailed sign-in link first; the password form
    // stays one click away on Janua's hosted page.
    expect(url.searchParams.get('login_method')).toBe('magic_link')
  })

  it('lets a caller ask for the password form first instead', async () => {
    const navigate = vi.fn()
    const url = new URL(await beginJanuaSignIn(CONFIG, { loginMethod: 'password', navigate }))
    expect(url.searchParams.get('login_method')).toBe('password')
  })

  it('keeps the one-time material where another tab can read it (an emailed link opens a new tab)', async () => {
    await beginJanuaSignIn(CONFIG, { navigate: vi.fn() })
    expect(localStorage.getItem(PKCE_STORAGE_KEYS.codeVerifier)).toBeTruthy()
    expect(localStorage.getItem(PKCE_STORAGE_KEYS.state)).toBeTruthy()
    expect(sessionStorage.getItem(PKCE_STORAGE_KEYS.codeVerifier)).toBeNull()
  })

  it('defaults the return path to the current page and refuses an off-site one', async () => {
    window.history.replaceState({}, '', '/project/gridfinity?mode=bin#3d')
    await beginJanuaSignIn(CONFIG, { navigate: vi.fn() })
    expect(localStorage.getItem(RETURN_PATH_KEY)).toBe('/project/gridfinity?mode=bin#3d')

    await beginJanuaSignIn(CONFIG, { returnTo: 'https://evil.test/', navigate: vi.fn() })
    expect(localStorage.getItem(RETURN_PATH_KEY)).toBeNull()
  })
})

describe('completeJanuaSignIn', () => {
  const arm = (state = 'st', verifier = 'v'.repeat(43)) => {
    localStorage.setItem(PKCE_STORAGE_KEYS.state, state)
    localStorage.setItem(PKCE_STORAGE_KEYS.codeVerifier, verifier)
  }

  const okResponse = (body: unknown) =>
    new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })

  it('exchanges the code as a form-encoded public-client request and stores the tokens for the SDK', async () => {
    arm()
    const fetchImpl = vi.fn(async () => okResponse({
      access_token: 'at', refresh_token: 'rt', id_token: 'idt', token_type: 'Bearer', expires_in: 3600,
    }))

    const tokens = await completeJanuaSignIn(CONFIG, 'code123', 'st', fetchImpl as unknown as typeof fetch)

    expect(tokens.access_token).toBe('at')
    expect(fetchImpl).toHaveBeenCalledTimes(1)
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('https://auth.example.test/api/v1/oauth/token')
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/x-www-form-urlencoded')
    expect(Object.fromEntries(new URLSearchParams(init.body as string))).toEqual({
      grant_type: 'authorization_code',
      code: 'code123',
      redirect_uri: 'https://studio.example.test',
      client_id: 'jnc_test',
      code_verifier: 'v'.repeat(43),
    })

    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.accessToken)).toBe('at')
    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.refreshToken)).toBe('rt')
    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.idToken)).toBe('idt')
    // One-time material is gone once used.
    expect(localStorage.getItem(PKCE_STORAGE_KEYS.state)).toBeNull()
    expect(localStorage.getItem(PKCE_STORAGE_KEYS.codeVerifier)).toBeNull()
  })

  it('refuses a state that was not minted here, without calling Janua', async () => {
    arm('expected')
    const fetchImpl = vi.fn()
    await expect(completeJanuaSignIn(CONFIG, 'c', 'forged', fetchImpl as unknown as typeof fetch))
      .rejects.toBeInstanceOf(JanuaSignInError)
    expect(fetchImpl).not.toHaveBeenCalled()
    expect(localStorage.getItem(PKCE_STORAGE_KEYS.state)).toBeNull()
    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.accessToken)).toBeNull()
  })

  it("surfaces Janua's error message and status, and stores nothing", async () => {
    arm()
    const fetchImpl = vi.fn(async () => new Response(
      JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'invalid_client: Unknown client' } }),
      { status: 401 },
    ))
    const failure = await completeJanuaSignIn(CONFIG, 'c', 'st', fetchImpl as unknown as typeof fetch).catch((e) => e)
    expect(failure).toBeInstanceOf(JanuaSignInError)
    expect(failure.message).toBe('invalid_client: Unknown client')
    expect(failure.status).toBe(401)
    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.accessToken)).toBeNull()
    expect(localStorage.getItem(PKCE_STORAGE_KEYS.codeVerifier)).toBeNull()
  })

  it('reads FastAPI and OAuth error shapes too', async () => {
    arm()
    const detail = vi.fn(async () => new Response(JSON.stringify({ detail: 'invalid_grant: expired' }), { status: 400 }))
    await expect(completeJanuaSignIn(CONFIG, 'c', 'st', detail as unknown as typeof fetch)).rejects.toThrow('invalid_grant: expired')

    arm()
    const oauth = vi.fn(async () => new Response(JSON.stringify({ error: 'invalid_request', error_description: 'bad code' }), { status: 400 }))
    await expect(completeJanuaSignIn(CONFIG, 'c', 'st', oauth as unknown as typeof fetch)).rejects.toThrow('bad code')

    arm()
    const html = vi.fn(async () => new Response('<html>502</html>', { status: 502 }))
    await expect(completeJanuaSignIn(CONFIG, 'c', 'st', html as unknown as typeof fetch)).rejects.toThrow('Token exchange failed (502)')
  })

  it('rejects a 200 without an access token', async () => {
    arm()
    const fetchImpl = vi.fn(async () => okResponse({ token_type: 'Bearer' }))
    await expect(completeJanuaSignIn(CONFIG, 'c', 'st', fetchImpl as unknown as typeof fetch)).rejects.toThrow('without an access token')
    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.accessToken)).toBeNull()
  })
})

describe('consumeReturnPath', () => {
  it('returns the remembered path once', () => {
    localStorage.setItem(RETURN_PATH_KEY, '/project/tablaco')
    expect(consumeReturnPath()).toBe('/project/tablaco')
    expect(consumeReturnPath()).toBeNull()
  })

  it('never returns an off-site value even if storage was tampered with', () => {
    localStorage.setItem(RETURN_PATH_KEY, 'https://evil.test/')
    expect(consumeReturnPath()).toBeNull()
  })
})

describe('storage-key contract with the installed @janua/react-sdk', () => {
  // The whole point of this module is that JanuaProvider picks the session up
  // on its next mount. That only holds while the key names agree, so pin them
  // against the real package (bypassing the test-wide mock) whenever it is
  // installed; the registry-less stub has no keys to compare against.
  it('uses the same localStorage and localStorage keys as the SDK', async () => {
    const sdk = await vi.importActual<Record<string, unknown>>('@janua/react-sdk').catch(() => null)
    const pkce = sdk?.PKCE_STORAGE_KEYS as Record<string, string> | undefined
    const tokens = sdk?.STORAGE_KEYS as Record<string, string> | undefined
    if (!pkce || !tokens) return // stub build without the private registry
    expect(PKCE_STORAGE_KEYS).toEqual({ codeVerifier: pkce.codeVerifier, state: pkce.state })
    expect(TOKEN_STORAGE_KEYS).toEqual({
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      idToken: tokens.idToken,
    })
  })
})


// A minimal unsigned JWT with the given payload — enough for the exp check,
// which reads the claim without verifying the signature.
const makeJwt = (payload: Record<string, unknown>) => {
  const b64url = (o: unknown) =>
    Buffer.from(JSON.stringify(o)).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${b64url({ alg: 'none', typ: 'JWT' })}.${b64url(payload)}.sig`
}

describe('getStoredAccessToken / hasStoredJanuaSession', () => {
  it('returns null with no stored token', () => {
    expect(getStoredAccessToken()).toBeNull()
    expect(hasStoredJanuaSession()).toBe(false)
  })

  it('returns a token whose exp is in the future', () => {
    const token = makeJwt({ sub: 'u', exp: Math.floor(Date.now() / 1000) + 3600 })
    localStorage.setItem(TOKEN_STORAGE_KEYS.accessToken, token)
    expect(getStoredAccessToken()).toBe(token)
    expect(hasStoredJanuaSession()).toBe(true)
  })

  it('treats an expired token as no session', () => {
    localStorage.setItem(
      TOKEN_STORAGE_KEYS.accessToken,
      makeJwt({ sub: 'u', exp: Math.floor(Date.now() / 1000) - 60 }),
    )
    expect(getStoredAccessToken()).toBeNull()
    expect(hasStoredJanuaSession()).toBe(false)
  })

  it('treats a token with no readable exp as usable (the API is the authority)', () => {
    const token = makeJwt({ sub: 'u' })
    localStorage.setItem(TOKEN_STORAGE_KEYS.accessToken, token)
    expect(getStoredAccessToken()).toBe(token)
    expect(hasStoredJanuaSession()).toBe(true)
  })

  it('is null-safe when the token is not a JWT', () => {
    localStorage.setItem(TOKEN_STORAGE_KEYS.accessToken, 'not-a-jwt')
    // Unparseable exp -> treated as usable rather than throwing.
    expect(getStoredAccessToken()).toBe('not-a-jwt')
    expect(hasStoredJanuaSession()).toBe(true)
  })
})
