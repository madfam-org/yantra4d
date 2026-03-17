import { SignIn } from '@janua/ui'

/**
 * LoginPage — renders the Janua SignIn component with context-based auth.
 *
 * In production the SignIn component uses the JanuaProvider context (via
 * the `januaClient` prop) so all auth calls go through the SDK's PKCE
 * redirect flow instead of making direct CORS-blocked fetch requests.
 *
 * @param {{ auth: ReturnType<import('../../hooks/useJanuaAuth').useJanuaAuth> }} props
 */
export default function LoginPage({ auth }) {
    return (
        <div className="flex min-h-screen items-center justify-center bg-background px-4">
            <div className="w-full max-w-sm space-y-0">
                <div className="text-center mb-6">
                    <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground font-black text-sm tracking-tight">
                        Y4D
                    </div>
                    <h1 className="text-2xl font-bold">Admin Panel</h1>
                    <p className="text-sm text-muted-foreground">Yantra4D Project Management</p>
                </div>

                <SignIn
                    afterSignIn={() => {
                        // Auth state is managed by JanuaProvider context.
                        // AuthGuard re-renders automatically when isAuthenticated changes.
                    }}
                    onError={(err) => console.error('Login error:', err)}
                    apiUrl={import.meta.env.VITE_JANUA_BASE_URL || 'https://auth.madfam.io'}
                    enableJanuaSSO={true}
                    socialProviders={{ google: true, github: true, microsoft: false, apple: false }}
                    showRememberMe={true}
                    termsUrl="https://madfam.io/terms"
                    privacyUrl="https://madfam.io/privacy"
                />

                <p className="text-xs text-muted-foreground text-center mt-4">
                    Authentication powered by{' '}
                    <a href="https://github.com/madfam-org/janua" target="_blank" rel="noreferrer" className="underline hover:text-foreground transition-colors">
                        Janua
                    </a>
                </p>
            </div>
        </div>
    )
}
