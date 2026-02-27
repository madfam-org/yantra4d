import { SignIn } from '@janua/ui'
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'

export default function LoginPage({ auth }) {
    const handleAfterSignIn = () => {
        // Auth state is managed by the parent auth context
        // Redirect will be handled by the auth guard
    }

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
                    afterSignIn={handleAfterSignIn}
                    onError={(err) => console.error('Login error:', err)}
                    apiUrl={import.meta.env.VITE_JANUA_BASE_URL || 'https://auth.madfam.io'}
                    socialProviders={{ google: false, github: false, microsoft: false, apple: false }}
                    showRememberMe={false}
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
