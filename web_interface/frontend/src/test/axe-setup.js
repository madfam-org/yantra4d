import { configureAxe } from 'jest-axe'

export const axe = configureAxe({
  rules: { 'color-contrast': { enabled: false } }
})
