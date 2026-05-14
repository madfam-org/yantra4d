module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  globals: {
    afterEach: 'readonly',
    beforeEach: 'readonly',
    describe: 'readonly',
    expect: 'readonly',
    it: 'readonly',
    vi: 'readonly',
  },
  extends: ['eslint:recommended'],
  rules: {
    'no-unused-vars': ['error', {
      varsIgnorePattern: '^[A-Z_]|^Icon$',
      argsIgnorePattern: '^_|^auth$|^Icon$',
    }],
  },
}
