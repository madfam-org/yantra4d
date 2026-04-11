import React from 'react'
import { Button } from "@/components/ui/button"

interface ErrorBoundaryProps {
  children: React.ReactNode
  t?: (key: string) => string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    const fallbacks: Record<string, string> = {
      'error.title': 'Something went wrong',
      'error.fallback': 'An unexpected error occurred',
      'error.retry': 'Try Again',
    }
    const translate = this.props.t || ((key: string) => fallbacks[key] || key)

    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-dvh bg-background text-foreground">
          <div className="text-center space-y-4 max-w-md p-8">
            <h1 className="text-2xl font-bold">{translate("error.title")}</h1>
            <p className="text-muted-foreground text-sm font-mono">
              {this.state.error?.message || translate('error.fallback')}
            </p>
            <Button onClick={this.handleReset}>
              {translate("error.retry")}
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
