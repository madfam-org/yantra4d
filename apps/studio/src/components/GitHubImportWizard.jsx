import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'
import { getApiBase } from '../services/backendDetection'
import { apiFetch } from '../services/apiClient'
const STEPS = ['url', 'review', 'confirm']

export default function GitHubImportWizard({ onClose, onImported }) {
  const [step, setStep] = useState(0)
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [validation, setValidation] = useState(null)
  const [slug, setSlug] = useState('')
  const [manifest, setManifest] = useState(null)

  const handleValidate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch(`${getApiBase()}/api/github/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Validation failed')
        setLoading(false)
        return
      }
      setValidation(data)
      // Auto-generate slug from repo URL
      const repoName = repoUrl.replace(/\.git\/?$/, '').split('/').pop() || 'imported'
      setSlug(repoName.toLowerCase().replace(/[^a-z0-9-_]/g, '-'))
      setManifest(data.manifest || null)
      setStep(1)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const handleImport = async () => {
    if (!manifest) {
      setError('A valid manifest is required to import')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch(`${getApiBase()}/api/github/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl, slug, manifest }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Import failed')
        setLoading(false)
        return
      }
      setStep(2)
      onImported?.(data.slug)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg mx-4">
        <CardHeader>
          <CardTitle>Import from GitHub</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {step === 0 && (
            <>
              <label htmlFor="gh-repo-url" className="block text-sm font-medium">Repository URL</label>
              <input
                id="gh-repo-url"
                type="url"
                value={repoUrl}
                onChange={e => setRepoUrl(e.target.value)}
                placeholder="https://github.com/user/repo"
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <p className="text-xs text-muted-foreground">
                Paste a public GitHub repo URL containing .scad files.{' '}
                <a
                  href="https://github.com/qubic-quest/qubic-template"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline"
                >
                  Use template
                </a>
              </p>
            </>
          )}

          {step === 1 && validation && (
            <>
              <div>
                <label htmlFor="gh-project-slug" className="block text-sm font-medium mb-1">Project slug</label>
                <input
                  id="gh-project-slug"
                  type="text"
                  value={slug}
                  onChange={e => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ''))}
                  className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <div>
                <p className="text-sm font-medium mb-1">Detected files ({validation.scad_files.length})</p>
                <ul className="text-xs text-muted-foreground max-h-32 overflow-y-auto space-y-0.5">
                  {validation.scad_files.map(f => (
                    <li key={f.path}>{f.path} ({Math.round(f.size / 1024)}KB)</li>
                  ))}
                </ul>
              </div>
              {validation.has_manifest ? (
                <p className="text-sm text-green-600 dark:text-green-400">
                  Found project.json in repository
                </p>
              ) : (
                <p className="text-sm text-yellow-600 dark:text-yellow-400">
                  No project.json found — a manifest will need to be created via the onboarding wizard after import.
                </p>
              )}
            </>
          )}

          {step === 2 && (
            <div className="text-center py-4">
              <p className="text-lg font-medium">Project imported</p>
              <p className="text-sm text-muted-foreground mt-1">
                <code>{slug}</code> is now available in your project gallery.
              </p>
            </div>
          )}
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          {step < 2 && (
            <Button variant="ghost" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
          )}
          {step === 0 && (
            <Button onClick={handleValidate} disabled={loading || !repoUrl.trim()}>
              {loading ? 'Validating...' : 'Validate'}
            </Button>
          )}
          {step === 1 && (
            <>
              <Button variant="outline" onClick={() => setStep(0)} disabled={loading}>
                Back
              </Button>
              <Button onClick={handleImport} disabled={loading || !slug}>
                {loading ? 'Importing...' : 'Import'}
              </Button>
            </>
          )}
          {step === 2 && (
            <Button onClick={() => { onClose(); window.location.hash = `#/${slug}` }}>
              Open Project
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  )
}
