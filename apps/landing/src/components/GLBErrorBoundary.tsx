import React from 'react';

type Props = { fallback: React.ReactNode; children: React.ReactNode };
type State = { hasError: boolean };

export class GLBErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };
  static getDerivedStateFromError(): State { return { hasError: true }; }
  componentDidCatch() { /* Intentionally silent — GLBs not yet pre-rendered */ }
  render() { return this.state.hasError ? this.props.fallback : this.props.children; }
}
