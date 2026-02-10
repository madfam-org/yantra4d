import { useManifest } from "../../contexts/ManifestProvider"
import { Github } from 'lucide-react'

export default function ProjectSelector() {
  const { projects, projectSlug, switchProject } = useManifest()

  if (!projects || projects.length <= 1) return null

  return (
    <div className="flex items-center gap-2">
      <select
        value={projectSlug}
        onChange={(e) => {
          if (e.target.value === '__github_import__') {
            window.location.hash = '#/projects'
            return
          }
          switchProject(e.target.value)
        }}
        className="h-8 px-2 text-sm rounded-md border border-border bg-background text-foreground"
        aria-label="Select project"
      >
        {projects.map((p) => (
          <option key={p.slug} value={p.slug}>
            {p.name}
          </option>
        ))}
        <option disabled>───────────</option>
        <option value="__github_import__">⊕ Import from GitHub…</option>
      </select>
    </div>
  )
}
