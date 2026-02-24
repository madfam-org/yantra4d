import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { ThemeProvider } from "./contexts/system/ThemeProvider.jsx"
import { AuthProvider } from "./contexts/auth/AuthProvider.jsx"
import { ManifestProvider } from "./contexts/project/ManifestProvider.jsx"
import { ProjectProvider } from "./contexts/project/ProjectProvider.jsx"
import { TierProvider } from "./contexts/auth/TierProvider.jsx"
import { UpgradePromptProvider } from "./contexts/auth/UpgradePromptProvider.jsx"
import ManifestAwareLanguageProvider from "./contexts/system/ManifestAwareLanguageProvider.jsx"
import { ErrorBoundary } from "./components/feedback/ErrorBoundary.jsx"
import { PlatformProvider } from "./contexts/system/PlatformProvider.jsx"
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'

// Suppress harmless opentype.js font parser warnings from Three.js.
// These fire for advanced OpenType features (GPOS/GSUB) in system fonts
// and don't affect rendering — all text in the studio is HTML, not WebGL.
const _warn = console.warn;
console.warn = (...args) => {
  if (typeof args[0] === 'string' && /unsupported G[A-Z]{3} table/.test(args[0])) return;
  _warn.apply(console, args);
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
          <AuthProvider>
            <TierProvider>
              <ManifestProvider>
                <ManifestAwareLanguageProvider>
                  <PlatformProvider>
                    <UpgradePromptProvider>
                      <ProjectProvider>
                        <App />
                      </ProjectProvider>
                    </UpgradePromptProvider>
                  </PlatformProvider>
                </ManifestAwareLanguageProvider>
              </ManifestProvider>
            </TierProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
