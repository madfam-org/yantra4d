import { Loader2 } from 'lucide-react'
import LoginPage from './LoginPage'

export default function AuthGuard({ auth, children }) {
    if (auth.isLoading) {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                <p className="text-sm">Verifying credentials…</p>
            </div>
        )
    }

    if (!auth.isAuthenticated) {
        return <LoginPage auth={auth} />
    }

    return children
}
