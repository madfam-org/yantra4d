import React from 'react'
import { Button } from "@/components/ui/button"

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    const translate = this.props.t || ((key) => key)

    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-screen bg-background text-foreground">
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
