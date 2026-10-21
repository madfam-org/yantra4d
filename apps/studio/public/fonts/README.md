# Fonts served from this origin

`roboto-regular.woff` (Roboto Regular, Latin subset, Apache License 2.0; the file
`@react-three/drei`'s `<Text>` used to fetch from fonts.gstatic.com by default). The Studio's CSP
allows `connect-src 'self'` plus the API, auth and landing origins only, so troika-three-text's
runtime font resolution (`cdn.jsdelivr.net/gh/lojjic/unicode-font-resolver`, then a Google
font) is blocked and every `<Text>` logged "TypeError: Failed to fetch … getFontsForString" with
no glyphs drawn. Every `<Text>` passes `font="/fonts/roboto-regular.woff"`;
`src/lib/studioFonts.test.ts` keeps it that way.
