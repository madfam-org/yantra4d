import { useState } from 'react';
import { STUDIO_URL } from '../lib/env';

type DemoProject = {
  slug: string;
  label: string;
  description: string;
  descriptionEs: string;
  category: string;
  color: string;
};

const PROJECTS: DemoProject[] = [
  { slug: 'gridfinity', label: 'Gridfinity', description: 'Modular storage bins with snap-fit baseplates', descriptionEs: 'Contenedores modulares con bases de ensamble a presión', category: 'Storage', color: '#4a90d9' },
  { slug: 'voronoi', label: 'Voronoi', description: 'Organic Voronoi pattern generator — coasters, vases, lampshades', descriptionEs: 'Generador de patrones Voronoi — posavasos, jarrones, pantallas', category: 'Art', color: '#e8b84b' },
  { slug: 'gear-reducer', label: 'Gear Reducer', description: 'Parametric gear assembly with housing', descriptionEs: 'Ensamble paramétrico de engranes con carcasa', category: 'Mechanical', color: '#6b8cce' },
  { slug: 'polydice', label: 'PolyDice', description: 'RPG polyhedral dice — D4 through D20', descriptionEs: 'Dados poliédricos RPG — D4 a D20', category: 'Tabletop', color: '#f39c12' },
  { slug: 'torus-knot', label: 'Torus Knot', description: 'Mathematical knot sculpture from dotSCAD', descriptionEs: 'Escultura de nudo matemático con dotSCAD', category: 'Art', color: '#e74c3c' },
  { slug: 'ultimate-box', label: 'Ultimate Box', description: 'Electronics enclosure with ventilation and snap-fit lid', descriptionEs: 'Carcasa electrónica con ventilación y tapa a presión', category: 'Electronics', color: '#9b59b6' },
  { slug: 'julia-vase', label: 'Julia Vase', description: 'Twisted vase inspired by Julia set fractals', descriptionEs: 'Jarrón torcido inspirado en fractales de Julia', category: 'Art', color: '#2ecc71' },
  { slug: 'stemfie', label: 'STEMFIE', description: 'Modular construction system for education', descriptionEs: 'Sistema de construcción modular para educación', category: 'Education', color: '#e67e22' },
  { slug: 'fasteners', label: 'Fasteners', description: 'Parametric bolts and nuts with real threads', descriptionEs: 'Tornillos y tuercas paramétricas con hilos reales', category: 'Mechanical', color: '#7f8c8d' },
  { slug: 'maze', label: 'Maze', description: 'Maze generator for coasters, cubes, and cylinders', descriptionEs: 'Generador de laberintos para posavasos, cubos y cilindros', category: 'Art', color: '#1abc9c' },
];

export default function InteractiveShowcase() {
  const [active, setActive] = useState(PROJECTS[0]);

  const lang = typeof document !== 'undefined' ? document.documentElement.lang : 'en';
  const isEs = lang === 'es';

  const tabpanelId = 'showcase-tabpanel';

  return (
    <div>
      <div className="flex flex-wrap gap-2 justify-center p-3 border-b border-border" role="tablist" aria-label="Demo projects">
        {PROJECTS.map(p => (
          <button
            key={p.slug}
            role="tab"
            aria-selected={active.slug === p.slug}
            aria-controls={tabpanelId}
            id={`tab-${p.slug}`}
            onClick={() => setActive(p)}
            className={`px-3 py-1.5 text-sm rounded-md border transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
              active.slug === p.slug
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-border hover:text-foreground'
            }`}
            style={active.slug === p.slug ? { backgroundColor: p.color, borderColor: p.color } : undefined}
          >
            {p.label}
          </button>
        ))}
      </div>
      <p className="text-center text-sm text-muted-foreground py-2">
        <span className="text-xs bg-secondary/50 rounded-full px-2 py-0.5 mr-2">{active.category}</span>
        {isEs ? active.descriptionEs : active.description}
      </p>
      <div className="sr-only" aria-live="polite">
        {isEs ? active.descriptionEs : active.description}
      </div>
      <div
        id={tabpanelId}
        role="tabpanel"
        aria-labelledby={`tab-${active.slug}`}
        className="h-[350px] sm:h-[500px] md:h-[600px] w-full"
      >
        <iframe
          key={active.slug}
          src={`${STUDIO_URL}?embed=true#/${active.slug}`}
          className="w-full h-full border-0"
          allow="clipboard-write"
          title={`${active.label} interactive demo`}
          loading="lazy"
        />
      </div>
      <div className="text-center py-3 border-t border-border">
        <a
          href={`${STUDIO_URL}#/${active.slug}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary hover:underline"
        >
          {isEs ? `Abrir ${active.label} en Studio →` : `Open ${active.label} in Studio →`}
        </a>
      </div>
    </div>
  );
}
