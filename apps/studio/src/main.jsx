import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { ThemeProvider } from "./contexts/ThemeProvider.jsx"
import { AuthProvider } from "./contexts/AuthProvider.jsx"
import { ManifestProvider } from "./contexts/ManifestProvider.jsx"
import { ProjectProvider } from "./contexts/ProjectProvider.jsx"
import { TierProvider } from "./contexts/TierProvider.jsx"
import { UpgradePromptProvider } from "./contexts/UpgradePromptProvider.jsx"
import ManifestAwareLanguageProvider from "./contexts/ManifestAwareLanguageProvider.jsx"
import { ErrorBoundary } from "./components/feedback/ErrorBoundary.jsx"
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
          <AuthProvider>
            <TierProvider>
              <UpgradePromptProvider>
                <ManifestProvider>
                  <ManifestAwareLanguageProvider>
                    <ProjectProvider>
                      <App />
                    </ProjectProvider>
                  </ManifestAwareLanguageProvider>
                </ManifestProvider>
              </UpgradePromptProvider>
            </TierProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
