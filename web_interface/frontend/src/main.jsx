import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { ThemeProvider } from "./contexts/ThemeProvider.jsx"
import { LanguageProvider } from "./contexts/LanguageProvider.jsx"
import { ErrorBoundary } from "./components/ErrorBoundary.jsx"
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
        <LanguageProvider defaultLanguage="es" storageKey="tablaco-lang">
          <App />
        </LanguageProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </StrictMode>,
)
