import { useState } from 'react';
import { PROJECTS, CATEGORIES } from '../data/projects';
import { STUDIO_URL } from '../lib/env';
import type { Translations } from '../lib/i18n';

type Props = {
  lang?: string;
  t?: Translations;
};

const DOMAIN_LABELS: Record<string, { en: string; es: string }> = {
  household: { en: 'Household', es: 'Hogar' },
  industrial: { en: 'Industrial', es: 'Industrial' },
  medical: { en: 'Medical', es: 'Médico' },
  commercial: { en: 'Commercial', es: 'Comercial' },
  commercial: { en: 'Commercial', es: 'Comercial' },
  hybrid: { en: 'Hybrid', es: 'Híbrido' },
  culture: { en: 'Culture', es: 'Cultura' },
};

export default function ProjectGalleryGrid({ lang = 'es', t }: Props) {
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const isEs = lang === 'es';

  const filtered = activeCategory === 'commons'
    ? PROJECTS.filter(p => p.isHyperobject)
    : activeCategory === 'all'
      ? PROJECTS
      : PROJECTS.filter(p => p.category === activeCategory);

  const categoryLabels: Record<string, string> = {
    all: t?.gallery.categories.all ?? 'Todos',
    commons: (t as any)?.gallery?.categories?.commons ?? (isEs ? '🔷 Commons' : '🔷 Commons'),
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
            className={`px-4 py-1.5 text-sm rounded-full border transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${activeCategory === cat
                ? cat === 'commons'
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-blue-500'
                  : 'bg-primary text-primary-foreground border-primary'
                : cat === 'commons'
                  ? 'bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/40'
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
            href={`${STUDIO_URL}#/${project.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className={`group rounded-xl border overflow-hidden transition-shadow hover:shadow-lg focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${project.isHyperobject
                ? 'border-blue-300 dark:border-blue-700 bg-gradient-to-b from-blue-50/50 to-card dark:from-blue-950/20 dark:to-card'
                : 'border-border bg-card'
              }`}
          >
            <div className="aspect-video bg-secondary/30 overflow-hidden relative">
              <img
                src={project.thumbnail}
                alt={project.name}
                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                loading="lazy"
                width="640"
                height="360"
              />
              {project.isHyperobject && (
                <span className="absolute top-2 right-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shadow-sm">
                  🔷 Hyperobject
                </span>
              )}
            </div>
            <div className="p-4">
              <div className="flex items-center justify-between mb-1 gap-1">
                <h3 className="font-semibold text-sm truncate">{project.name}</h3>
                <div className="flex gap-1 shrink-0">
                  {project.isHyperobject && project.domain && (
                    <span className="text-[10px] text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/40 rounded-full px-1.5 py-0.5 font-medium">
                      {isEs
                        ? DOMAIN_LABELS[project.domain]?.es ?? project.domain
                        : DOMAIN_LABELS[project.domain]?.en ?? project.domain}
                    </span>
                  )}
                  <span className="text-xs text-muted-foreground bg-secondary/50 rounded-full px-2 py-0.5">
                    {categoryLabels[project.category]}
                  </span>
                </div>
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

