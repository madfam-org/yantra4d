# Environment maps (HDRI)

The ten 1k HDR environment maps `@react-three/drei`'s `<Environment preset=…>` would
otherwise fetch at runtime from `raw.githack.com/pmndrs/drei-assets` (commit
`456060a26bbeb8fdf79326f224b6d99b8bcce736`). They are served from this origin because the
Studio's CSP (`apps/studio/nginx-security-headers.conf`) allows `connect-src 'self'` plus the
API, auth and landing origins only: a third-party fetch is blocked, and the viewer's
ErrorBoundary then replaces the whole canvas with "Could not load potsdamer_platz_1k.hdr".

Source: Poly Haven (CC0 1.0), packaged by pmndrs/drei-assets (MIT). Preset → file mapping
lives in `src/lib/environmentPresets.ts`; `src/lib/environmentPresets.test.ts` checks every
mapped file is here and is a Radiance HDR.
