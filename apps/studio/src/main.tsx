import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { initPostHog } from "./lib/analytics";
initPostHog();
import { ThemeProvider } from "./contexts/system/ThemeProvider"
import { AuthProvider } from "./contexts/auth/AuthProvider"
import { ManifestProvider } from "./contexts/project/ManifestProvider"
import { ProjectProvider } from "./contexts/project/ProjectProvider"
import { TierProvider } from "./contexts/auth/TierProvider"
import { UpgradePromptProvider } from "./contexts/auth/UpgradePromptProvider"
import ManifestAwareLanguageProvider from "./contexts/system/ManifestAwareLanguageProvider"
import { ErrorBoundary } from "./components/feedback/ErrorBoundary.jsx"
import { PlatformProvider } from "./contexts/system/PlatformProvider"
import { BrowserRouter } from 'react-router-dom'
import App from './App'

// Pre-mount hash-to-path redirect: convert legacy hash URLs (e.g. /#/slug/preset/mode)
// to BrowserRouter-compatible paths before React mounts (no flash).
;(function redirectHashToPath() {
  const { hash, search } = window.location
  if (!hash || !hash.startsWith('#/')) return
  const segments = hash.slice(2).split('/').filter(Boolean)
  if (segments.length === 0) return
  let newPath
  if (segments[0] === 'projects') {
    newPath = '/projects'
  } else if (segments[0] === 'demo') {
    newPath = '/' + segments.join('/')
  } else {
    newPath = '/project/' + segments.join('/')
  }
  window.history.replaceState(null, '', newPath + search)
})()

// Suppress harmless opentype.js font parser warnings from Three.js.
// These fire for advanced OpenType features (GPOS/GSUB) in system fonts
// and don't affect rendering — all text in the studio is HTML, not WebGL.
const _warn = console.warn;
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === 'string' && /unsupported G[A-Z]{3} table/.test(args[0])) return;
  _warn.apply(console, args);
};

createRoot(document.getElementById('root')!).render(
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

// Remove Layer 1 HTML splash after React mounts
requestAnimationFrame(() => {
  const splash = document.getElementById('yantra4d-splash')
  if (splash) {
    splash.classList.add('yantra4d-splash--exiting')
    const remove = () => { if (splash.parentNode) splash.remove() }
    splash.addEventListener('animationend', remove, { once: true })
    setTimeout(remove, 500)
  }
})
