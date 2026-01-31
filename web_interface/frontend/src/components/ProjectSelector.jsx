import { useManifest } from "../contexts/ManifestProvider"

export default function ProjectSelector() {
  const { projects, projectSlug, switchProject } = useManifest()

  if (!projects || projects.length <= 1) return null

  return (
    <select
      value={projectSlug}
      onChange={(e) => switchProject(e.target.value)}
      className="h-8 px-2 text-sm rounded-md border border-border bg-background text-foreground"
    >
      {projects.map((p) => (
        <option key={p.slug} value={p.slug}>
          {p.name}
        </option>
      ))}
    </select>
  )
}
