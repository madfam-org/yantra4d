import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/admin.css'
import { initPostHog } from "./lib/analytics";
initPostHog();

// Only wrap with JanuaProvider in production (AUTH_ENABLED=true)
const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true'

// Supplied at build time from the deployment secrets. There is deliberately no
// default: a value written here would put a client identity in this repository,
// and it would let a build whose secret was never set come up silently under
// somebody else's identity instead of telling us the build was wrong.
const JANUA_CLIENT_ID = import.meta.env.VITE_JANUA_CLIENT_ID || ''

const MISSING_CLIENT_ID_MESSAGE =
    'Admin authentication is not configured: the build-time variable ' +
    'VITE_JANUA_CLIENT_ID was empty when this bundle was built. Set the ' +
    'JANUA_ADMIN_CLIENT_ID deployment secret and rebuild the admin image.'

function ConfigurationError({ message }) {
    return (
        <div role="alert" style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
            <h1>Admin is misconfigured</h1>
            <p>{message}</p>
        </div>
    )
}

async function bootstrap() {
    const container = document.getElementById('root')
    let Root = App

    if (AUTH_ENABLED) {
        // Fail loudly and early: no guessed identity, and no admin surface
        // rendered with authentication quietly absent.
        if (!JANUA_CLIENT_ID) {
            console.error(`[admin] ${MISSING_CLIENT_ID_MESSAGE}`)
            ReactDOM.createRoot(container).render(
                <React.StrictMode>
                    <ConfigurationError message={MISSING_CLIENT_ID_MESSAGE} />
                </React.StrictMode>
            )
            return
        }

        const { JanuaProvider } = await import('@janua/react-sdk')
        const config = {
            baseURL: import.meta.env.VITE_JANUA_BASE_URL || 'https://auth.madfam.io',
            clientId: JANUA_CLIENT_ID,
            redirectUri: import.meta.env.VITE_JANUA_REDIRECT_URI || `${window.location.origin}/auth/callback`,
        }

        Root = () => (
            <JanuaProvider config={config}>
                <App />
            </JanuaProvider>
        )
    }

    ReactDOM.createRoot(container).render(
        <React.StrictMode>
            <Root />
        </React.StrictMode>
    )
}

bootstrap()
