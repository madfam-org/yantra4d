import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/admin.css'

// Only wrap with JanuaProvider in production (AUTH_ENABLED=true)
const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true'

async function bootstrap() {
    let Root = App

    if (AUTH_ENABLED) {
        const { JanuaProvider } = await import('@janua/react-sdk')
        const baseURL = import.meta.env.VITE_JANUA_BASE_URL || 'https://auth.madfam.io'

        Root = () => (
            <JanuaProvider baseURL={baseURL}>
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
