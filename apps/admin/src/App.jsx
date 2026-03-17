import { useJanuaAuth } from './hooks/useJanuaAuth'
import AuthGuard from './components/auth/AuthGuard'
import AdminShell from './components/AdminShell'
import OAuthCallback from './components/auth/OAuthCallback'

export default function App() {
    const auth = useJanuaAuth()

    // Handle the OIDC/PKCE redirect callback at /auth/callback
    if (window.location.pathname === '/auth/callback') {
        return <OAuthCallback auth={auth} />
    }

    return <AuthGuard auth={auth}><AdminShell auth={auth} /></AuthGuard>
}
