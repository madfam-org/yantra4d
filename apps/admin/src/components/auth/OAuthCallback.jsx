import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

/**
 * OAuthCallback — handles the OIDC/PKCE redirect callback.
 *
 * When Janua redirects back to /auth/callback?code=...&state=...,
 * this component extracts the parameters and exchanges the authorization
 * code for tokens via the JanuaProvider context.
 *
 * On success the auth state updates automatically and AuthGuard
 * renders the admin shell. On failure an error message is shown
 * with a retry link.
 */
export default function OAuthCallback({ auth }) {
    const [error, setError] = useState(null)

    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const code = params.get('code')
        const state = params.get('state')
        const errorParam = params.get('error')
        const errorDescription = params.get('error_description')

        if (errorParam) {
            setError(errorDescription || errorParam)
            return
        }

        if (!code || !state) {
            setError('Missing authorization code or state parameter.')
            return
        }

        auth
            .handleOAuthCallback(code, state)
            .then(() => {
                // Clean the URL — remove query params after successful exchange
                window.history.replaceState({}, '', window.location.pathname.replace('/auth/callback', '/'))
            })
            .catch((err) => {
                console.error('OAuth callback error:', err)
                setError(err?.message || 'Authentication failed. Please try again.')
            })
    }, [auth])

    if (error) {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
                <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 max-w-sm">
                    <h2 className="text-lg font-semibold text-destructive mb-2">Authentication Failed</h2>
                    <p className="text-sm text-muted-foreground mb-4">{error}</p>
                    <a
                        href="/"
                        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                    >
                        Back to sign in
                    </a>
                </div>
            </div>
        )
    }

    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin" />
            <p className="text-sm">Completing sign-in...</p>
        </div>
    )
}
