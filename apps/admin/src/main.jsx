import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/admin.css'
import { initPostHog } from "./lib/analytics";
initPostHog();

// Only wrap with JanuaProvider in production (AUTH_ENABLED=true)
const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true'

async function bootstrap() {
    let Root = App

    if (AUTH_ENABLED) {
        const { JanuaProvider } = await import('@janua/react-sdk')
        const config = {
            baseURL: import.meta.env.VITE_JANUA_BASE_URL || 'https://auth.madfam.io',
            clientId: import.meta.env.VITE_JANUA_CLIENT_ID || 'jnc_-v2RiP_TMO-XSExftpCh41K46xeszlKh',
            redirectUri: import.meta.env.VITE_JANUA_REDIRECT_URI || `${window.location.origin}/auth/callback`,
        }

        Root = () => (
            <JanuaProvider config={config}>
                <App />
            </JanuaProvider>
        )
    }

    ReactDOM.createRoot(document.getElementById('root')).render(
        <React.StrictMode>
            <Root />
        </React.StrictMode>
    )
}

bootstrap()
