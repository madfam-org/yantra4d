/**
 * Test stub for @janua/react-sdk.
 * Used in CI where the private registry is unavailable.
 * Remove once npm.madfam.io allows public reads.
 */
export function JanuaProvider({ children }) {
  return children
}

export function useJanua() {
  return {
    isAuthenticated: false,
    isLoading: false,
    user: null,
    login: () => {},
    logout: () => {},
    getToken: () => null,
  }
}
