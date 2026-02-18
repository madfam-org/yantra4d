import { useState, useEffect } from 'react'
import { Copy, Check, ExternalLink, AlertCircle, RefreshCw, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

function authHeaders() {
    const token = sessionStorage.getItem('janua_access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
}

export default function TablacoLinkPanel() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [copied, setCopied] = useState(false)

    const fetchLink = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('/api/admin/projects/tablaco/public-link', {
                headers: authHeaders(),
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            setData(await res.json())
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { fetchLink() }, [])

    const copyToClipboard = async () => {
        if (!data?.public_url) return
        await navigator.clipboard.writeText(data.public_url)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                <p className="text-sm">Fetching Tablaco link…</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-destructive">
                <AlertCircle className="h-6 w-6" />
                <p className="text-sm">Failed to load link: {error}</p>
                <Button variant="outline" size="sm" onClick={fetchLink}>
                    <RefreshCw className="mr-2 h-3.5 w-3.5" /> Retry
                </Button>
            </div>
        )
    }

    return (
        <div className="max-w-2xl space-y-4">
            <Card>
                <CardHeader>
                    <div className="flex items-start gap-3">
                        <span className="text-3xl">🪵</span>
                        <div>
                            <CardTitle>Tablaco Public Storefront</CardTitle>
                            <CardDescription className="mt-1">
                                Share this URL with customers to give them access to the Tablaco
                                configurator in storefront mode. This link is only visible to admins.
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="space-y-4">
                    {/* URL display */}
                    <div className="rounded-md border border-border bg-muted/40 px-4 py-3">
                        <code className="break-all text-sm text-primary font-mono">
                            {data?.public_url}
                        </code>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                        <Button onClick={copyToClipboard} className={copied ? 'bg-green-600 hover:bg-green-700' : ''}>
                            {copied
                                ? <><Check className="mr-2 h-4 w-4" />Copied!</>
                                : <><Copy className="mr-2 h-4 w-4" />Copy link</>
                            }
                        </Button>
                        <Button variant="outline" asChild>
                            <a href={data?.public_url} target="_blank" rel="noreferrer">
                                <ExternalLink className="mr-2 h-4 w-4" />
                                Preview
                            </a>
                        </Button>
                    </div>

                    {/* Warning */}
                    <div className="flex items-start gap-2.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-amber-600 dark:text-amber-400">
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                        <p className="text-xs leading-relaxed">
                            This URL grants access to the Tablaco storefront without authentication.
                            Only share with intended customers. The URL is not exposed in any public API.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
