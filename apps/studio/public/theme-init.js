// Applies the saved or system theme class to <html> before the app boots, so the first paint
// is not a flash of the wrong theme. Served from public/ as a real file because the Studio's
// nginx CSP (apps/studio/nginx-security-headers.conf) allows script-src 'self' only: an inline
// script is blocked there (a console error on every load; ThemeProvider then applies the theme late).
// Keep in step with ThemeProvider's storageKey 'vite-ui-theme' in src/main.tsx.
;(function() {
  try {
    var theme = localStorage.getItem('vite-ui-theme')
    if (theme === 'dark' || (!theme || theme === 'system') && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.add('light')
    }
  } catch (e) {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.classList.add('dark')
    }
  }
})()
