/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  darkMode: 'class',
  theme: {
    extend: {
      screens: {
        'xs': '360px',
        // MUST NOT be named `landscape`: Tailwind ships a built-in `landscape`
        // variant (`@media (orientation: landscape)`). A custom screen with that
        // key collides with it and the built-in wins, silently dropping the
        // `max-width` guard so the utility fires at desktop widths too.
        'phone-landscape': { raw: '(orientation: landscape) and (max-width: 1023px)' },
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
          // Small-text-safe accent. --primary itself measures 3.83:1 on
          // dark surfaces, which is under the 4.5:1 floor for body copy;
          // use `text-primary-readable` for accent text below 24px.
          readable: 'hsl(var(--primary-readable))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        border: 'hsl(var(--border))',
        ring: 'hsl(var(--ring))',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
};
