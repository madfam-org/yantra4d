import { useState } from 'react';
import { PROJECTS, CATEGORIES } from '../data/projects';
import type { Translations } from '../lib/i18n';

type Props = {
  lang?: string;
  t?: Translations;
};

const STUDIO_BASE = import.meta.env.DEV
  ? 'http://localhost:5173'
  : 'https://4d-app.madfam.io';

export default function ProjectGalleryGrid({ lang = 'es', t }: Props) {
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const isEs = lang === 'es';

  const filtered = activeCategory === 'all'
    ? PROJECTS
    : PROJECTS.filter(p => p.category === activeCategory);

  const categoryLabels: Record<string, string> = {
    all: t?.gallery.categories.all ?? 'Todos',
    storage: t?.gallery.categories.storage ?? 'Almacenamiento',
    mechanical: t?.gallery.categories.mechanical ?? 'Mecánico',
    art: t?.gallery.categories.art ?? 'Arte y Generativo',
    tabletop: t?.gallery.categories.tabletop ?? 'Mesa de Juego',
    education: t?.gallery.categories.education ?? 'Educación',
    electronics: t?.gallery.categories.electronics ?? 'Electrónica',
  };

  const openLabel = t?.gallery.openInStudio ?? 'Abrir en Studio →';

  return (
    <div>
      <div className="flex flex-wrap gap-2 justify-center mb-8" role="tablist" aria-label="Project categories">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            role="tab"
            aria-selected={activeCategory === cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-1.5 text-sm rounded-full border transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
              activeCategory === cat
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-border hover:text-foreground'
            }`}
          >
            {categoryLabels[cat]}
          </button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map(project => (
          <a
            key={project.slug}
            href={`${STUDIO_BASE}#/${project.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="group rounded-xl border border-border bg-card overflow-hidden transition-shadow hover:shadow-lg focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <div className="aspect-video bg-secondary/30 overflow-hidden">
              <img
                src={project.thumbnail}
                alt={project.name}
                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                loading="lazy"
                width="640"
                height="360"
              />
            </div>
            <div className="p-4">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-semibold text-sm">{project.name}</h3>
                <span className="text-xs text-muted-foreground bg-secondary/50 rounded-full px-2 py-0.5">
                  {categoryLabels[project.category]}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mb-2">
                {isEs ? project.descriptionEs : project.description}
              </p>
              <span className="text-xs text-primary group-hover:underline">{openLabel}</span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
