/**
 * Landing page Astro component structural tests.
 *
 * These tests validate the HTML template structure of Astro components by
 * reading the raw `.astro` source files and verifying key structural elements
 * (semantic HTML, accessibility attributes, required content, links).
 *
 * Since Astro components are server-rendered and can't be imported into jsdom
 * without the Astro rendering pipeline, we parse the template portion of each
 * component file (everything after the frontmatter `---` fence).
 */
import { describe, it, expect, beforeAll } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const COMPONENTS_DIR = resolve(__dirname, '.')

function loadTemplate(filename: string): string {
  const src = readFileSync(resolve(COMPONENTS_DIR, filename), 'utf-8')
  // Extract the template portion (after the second `---`)
  const parts = src.split('---')
  return parts.length >= 3 ? parts.slice(2).join('---') : src
}

// ─── Header ─────────────────────────────────────────────────────────────────
describe('Header.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('Header.astro')
  })

  it('has a fixed header element', () => {
    expect(html).toContain('<header')
    expect(html).toContain('fixed')
  })

  it('renders the brand name', () => {
    expect(html).toContain('Yantra4D')
  })

  it('has navigation with anchor links', () => {
    expect(html).toContain('<nav')
    expect(html).toContain('#gallery')
    expect(html).toContain('/concepts/hyperobjects/')
    expect(html).toContain('/concepts/commons/')
    expect(html).toContain('/concepts/common-denominator/')
  })

  it('has mobile menu button with accessibility attributes', () => {
    expect(html).toContain('id="mobile-menu-btn"')
    expect(html).toContain('aria-label="Open menu"')
    expect(html).toContain('aria-expanded="false"')
    expect(html).toContain('aria-controls="mobile-menu"')
  })

  it('has mobile menu overlay with aria-hidden', () => {
    expect(html).toContain('id="mobile-menu"')
    expect(html).toContain('aria-hidden="true"')
  })

  it('has close button for mobile menu', () => {
    expect(html).toContain('id="mobile-menu-close"')
    expect(html).toContain('aria-label="Close menu"')
  })

  it('has Open Studio CTA linking to studioUrl', () => {
    expect(html).toContain('studioUrl')
    expect(html).toMatch(/Abrir Studio|openStudio/)
  })

  it('has language switcher', () => {
    expect(html).toContain('switchLang')
  })
})

// ─── Hero ───────────────────────────────────────────────────────────────────
describe('Hero.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('Hero.astro')
  })

  it('has a single h1', () => {
    const h1Count = (html.match(/<h1/g) || []).length
    expect(h1Count).toBe(1)
  })

  it('renders the two-line title with primary accent span', () => {
    expect(html).toMatch(/Tus Diseños|titleLine1/)
    expect(html).toMatch(/Sus Dimensiones|titleLine2/)
    expect(html).toContain('text-primary')
  })

  it('has two CTA links', () => {
    expect(html).toContain('#adventure')
    expect(html).toContain('studioUrl')
    expect(html).toMatch(/Begin Your Journey|journeyBtn/)
    expect(html).toMatch(/Launch Studio|studioBtn/)
  })

  it('has scroll indicator animation', () => {
    expect(html).toContain('animate-bounce')
    expect(html).toContain('<svg')
    expect(html).toContain('bottom-8')
  })
})

// ─── HowItWorks ─────────────────────────────────────────────────────────────
describe('HowItWorks.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('HowItWorks.astro')
  })

  it('has a section with heading', () => {
    expect(html).toContain('<section')
    expect(html).toContain('<h2')
    expect(html).toMatch(/Cómo Funciona|howItWorks\.heading/)
  })

  it('has Maker and Creator tracks', () => {
    expect(html).toMatch(/Para Makers|makerTrack\.label/)
    expect(html).toMatch(/Para Creadores|creatorTrack\.label/)
  })

  it('has 3 steps in each track', () => {
    // Each track has 3 numbered step circles (1, 2, 3)
    const stepCircles = (html.match(/>1<|>2<|>3</g) || []).length
    expect(stepCircles).toBe(6) // 3 per track × 2 tracks
  })

  it('uses two-column grid layout', () => {
    expect(html).toContain('md:grid-cols-2')
  })
})

// ─── BeforeAfter ────────────────────────────────────────────────────────────
describe('BeforeAfter.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('BeforeAfter.astro')
  })

  it('has a section with tagline heading', () => {
    expect(html).toContain('<h2')
    expect(html).toMatch(/De código a configurador|beforeAfter\.tagline/)
  })

  it('has code side with OpenSCAD preview', () => {
    expect(html).toContain('<pre')
    expect(html).toContain('<code>')
    expect(html).toContain('gridfinity_bin')
    expect(html).toMatch(/Código OpenSCAD|codeSide/)
  })

  it('has UI side with mock sliders', () => {
    expect(html).toMatch(/Configurador Yantra4D|uiSide/)
    expect(html).toContain('Width')
    expect(html).toContain('Depth')
    expect(html).toContain('Height')
    expect(html).toContain('Dividers')
  })

  it('has mock checkbox toggles for Lip and Magnets', () => {
    expect(html).toContain('Lip')
    expect(html).toContain('Magnets')
  })

  it('uses two-column comparison layout', () => {
    expect(html).toContain('md:grid-cols-2')
  })
})

// ─── ForMakers ──────────────────────────────────────────────────────────────
describe('ForMakers.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('ForMakers.astro')
  })

  it('has section with id for-makers', () => {
    expect(html).toContain('id="for-makers"')
  })

  it('has heading', () => {
    expect(html).toContain('<h2')
    expect(html).toMatch(/Hecho para Makers|forMakers\.heading/)
  })

  it('has 5 feature cards', () => {
    const h3Count = (html.match(/<h3/g) || []).length
    expect(h3Count).toBe(5)
  })

  it('has feature emojis', () => {
    expect(html).toContain('🎛️')
    expect(html).toContain('🖨️')
    expect(html).toContain('📦')
    expect(html).toContain('🔧')
    expect(html).toContain('🌐')
  })

  it('uses responsive grid', () => {
    expect(html).toContain('sm:grid-cols-2')
    expect(html).toContain('lg:grid-cols-3')
  })
})

// ─── ForCreators ────────────────────────────────────────────────────────────
describe('ForCreators.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('ForCreators.astro')
  })

  it('has section with id for-creators', () => {
    expect(html).toContain('id="for-creators"')
  })

  it('has heading', () => {
    expect(html).toContain('<h2')
    expect(html).toMatch(/Hecho para Creadores|forCreators\.heading/)
  })

  it('has 5 feature cards', () => {
    const h3Count = (html.match(/<h3/g) || []).length
    expect(h3Count).toBe(5)
  })

  it('has feature emojis', () => {
    expect(html).toContain('⬆️')
    expect(html).toContain('🔗')
    expect(html).toContain('⚙️')
    expect(html).toContain('📂')
    expect(html).toContain('💚')
  })
})

// ─── CallToAction ───────────────────────────────────────────────────────────
describe('CallToAction.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('CallToAction.astro')
  })

  it('has heading', () => {
    expect(html).toContain('<h2')
    expect(html).toMatch(/Tu próxima impresión|cta\.heading/)
  })

  it('has subtitle', () => {
    expect(html).toMatch(/Sin cuenta|cta\.subtitle/)
  })

  it('has two CTA buttons', () => {
    expect(html).toContain('#gallery')
    expect(html).toContain('studioUrl')
  })
})

// ─── Footer ─────────────────────────────────────────────────────────────────
describe('Footer.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('Footer.astro')
  })

  it('has footer element', () => {
    expect(html).toContain('<footer')
  })

  it('has copyright text', () => {
    expect(html).toMatch(/Yantra4D|copyright/)
  })

  it('has navigation links', () => {
    expect(html).toContain('#gallery')
    expect(html).toContain('github.com/madfam-org/yantra4d')
  })

  it('has outside links with rel=noopener', () => {
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('links to docs and studio', () => {
    expect(html).toContain('studioUrl')
    expect(html).toMatch(/Docs|footer\.docs/)
  })
})

// ─── OpenSource ─────────────────────────────────────────────────────────────
describe('OpenSource.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('OpenSource.astro')
  })

  it('has section with id', () => {
    expect(html).toContain('id="open-source"')
  })

  it('has heading about open source', () => {
    expect(html).toContain('<h2')
    expect(html).toMatch(/Código Abierto|openSourceSection\.heading/)
  })

  it('shows stats badges', () => {
    expect(html).toMatch(/statProjects/)
    expect(html).toMatch(/statLicense/)
    expect(html).toContain('GitHub')
  })

  it('renders its figures from bound values, never from literal copy', () => {
    // The badges once advertised "21 Projects" against a commons of 326. The
    // numbers must be bound from generated stats so they cannot go stale.
    expect(html).toMatch(/\{cartridges\}/)
    expect(html).toMatch(/\{standards\}/)
    expect(html).not.toMatch(/\b21 (Proyectos|Projects)\b/)
  })

  it('does not credit the designs to the platform licence', () => {
    // Cartridges are CERN-OHL-W; AGPLv3 covers the platform code only.
    expect(html).not.toMatch(/>AGPLv3</)
  })

  it('has GitHub link', () => {
    expect(html).toContain('https://github.com/madfam-org/yantra4d')
    expect(html).toMatch(/Ver en GitHub|openSourceSection\.cta/)
  })

  it('has tech stack note', () => {
    expect(html).toMatch(/OpenSCAD.*React.*Three\.js|techNote/)
  })
})

// ─── CDGSection ────────────────────────────────────────────────────────────
describe('CDGSection.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('CDGSection.astro')
  })

  it('has a section with id cdg-section', () => {
    expect(html).toContain('id="cdg-section"')
  })

  it('has heading about CDG interfaces', () => {
    expect(html).toContain('<h2')
    expect(html).toMatch(/The Interfaces That Connect Everything|cdg\.heading/)
  })

  it('has CDG badge', () => {
    expect(html).toMatch(/Common Denominator Geometry|cdg\.badge/)
  })

  it('has explainer section with What is CDG', () => {
    expect(html).toContain('<h3')
    expect(html).toMatch(/What is CDG|explainerTitle/)
  })

  it('has CDG catalog grid', () => {
    expect(html).toMatch(/The CDG Catalog|catalogTitle/)
    expect(html).toContain('sm:grid-cols-2')
    expect(html).toContain('lg:grid-cols-3')
  })

  it('has SVG diagram with center CDG node', () => {
    expect(html).toContain('<svg')
    expect(html).toContain('>CDG<')
  })

  it('has interface strategy section', () => {
    expect(html).toMatch(/The Interface Strategy|impactTitle/)
  })

  it('has stats grid', () => {
    expect(html).toContain('md:grid-cols-4')
    expect(html).toContain('stat.value')
    expect(html).toContain('stat.label')
  })

  it('has graph paper background with aria-hidden', () => {
    expect(html).toContain('cdg-graph-bg')
    expect(html).toContain('aria-hidden="true"')
  })

  it('has fade-in animation classes', () => {
    expect(html).toContain('cdg-fade-in')
  })
})

// ─── HyperCommons ──────────────────────────────────────────────────────────
describe('HyperCommons.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('HyperCommons.astro')
  })

  it('has a section with id hyper-commons', () => {
    expect(html).toContain('id="hyper-commons"')
  })

  it('has heading about parametric commons', () => {
    expect(html).toContain('<h2')
    expect(html).toMatch(/Los Comunes Paramétricos|hyperCommons\.heading/)
  })

  it('has Open Commons badge', () => {
    expect(html).toContain('Open Commons')
  })

  it('has What is a Hyperobject section', () => {
    expect(html).toMatch(/Qué es un Hiperobjeto|whatIsHeading/)
  })

  it('has parametric morph SVG visualization', () => {
    expect(html).toContain('<svg')
    expect(html).toContain('hc-shape-morph')
    expect(html).toContain('width')
    expect(html).toContain('height')
  })

  it('has paradigm shift comparison (STL vs SCAD)', () => {
    expect(html).toMatch(/El Cambio de Paradigma|shiftHeading/)
    expect(html).toMatch(/\.STL Estático|shiftFrom/)
    expect(html).toMatch(/\.SCAD Paramétrico|shiftTo/)
  })

  it('has four domain impact cards', () => {
    expect(html).toContain('lg:grid-cols-4')
    expect(html).toContain('🏠')
    expect(html).toContain('🏭')
    expect(html).toContain('🏥')
    expect(html).toContain('⚙️')
  })

  it('has impact stats section', () => {
    expect(html).toMatch(/Impacto Real|impactHeading/)
    expect(html).toContain('sm:grid-cols-4')
  })

  it('has fade-in animation classes', () => {
    expect(html).toContain('hc-fade-in')
  })

  it('has reduced motion media query in styles', () => {
    expect(html).toContain('prefers-reduced-motion')
  })
})

// ─── ProjectGallery ─────────────────────────────────────────────────────────
describe('ProjectGallery.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('ProjectGallery.astro')
  })

  it('has a section element', () => {
    expect(html).toContain('<section')
  })

  it('has gallery id for anchor navigation', () => {
    expect(html).toContain('id="gallery"')
  })
})
