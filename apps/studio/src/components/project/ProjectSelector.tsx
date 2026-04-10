import React from 'react'
import { useManifest } from "../../contexts/project/ManifestProvider"
import { Github } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function ProjectSelector() {
  const { projects, projectSlug, switchProject, manifest } = useManifest()
  const navigate = useNavigate()

  if (!projects || projects.length <= 1) return null

  const isUnlisted = projectSlug && !projects.find((p: Record<string, unknown>) => p.slug === projectSlug)

  return (
    <div className="flex items-center gap-2">
      <select
        value={projectSlug}
        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
          if (e.target.value === '__github_import__') {
            navigate('/projects')
            return
          }
          switchProject(e.target.value)
        }}
        className="h-11 min-h-[44px] px-2 text-base md:text-sm rounded-md border border-border bg-background text-foreground"
        aria-label="Select project"
      >
        {isUnlisted && (
          <option value={projectSlug}>
            {(manifest as Record<string, unknown>)?.project
              ? ((manifest as Record<string, unknown>).project as Record<string, unknown>)?.name as string
              : projectSlug}
          </option>
        )}
        {projects.map((p: Record<string, unknown>) => (
          <option key={p.slug as string} value={p.slug as string}>
            {p.name as string}
          </option>
        ))}
        <option disabled>───────────</option>
        <option value="__github_import__">⊕ Import from GitHub…</option>
      </select>
    </div>
  )
}
