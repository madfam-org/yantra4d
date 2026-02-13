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
    expect(html).toContain('#for-makers')
    expect(html).toContain('#for-creators')
    expect(html).toContain('#demo')
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

  it('has two CTA buttons', () => {
    expect(html).toContain('#gallery')
    expect(html).toContain('studioUrl')
    expect(html).toMatch(/Explorar|ctaPrimary/)
    expect(html).toMatch(/Sube Tu|ctaSecondary/)
  })

  it('has hero preview image with responsive srcset', () => {
    expect(html).toContain('hero-preview.webp')
    expect(html).toContain('srcset=')
    expect(html).toContain('640w')
    expect(html).toContain('1280w')
  })

  it('has alt text on hero image', () => {
    expect(html).toContain('alt="Yantra4D Studio')
  })

  it('has play button with aria-label', () => {
    expect(html).toContain('id="hero-play-btn"')
    expect(html).toContain('aria-label="Scroll to interactive demo"')
  })

  it('image has lazy loading and width/height for CLS prevention', () => {
    expect(html).toContain('loading="lazy"')
    expect(html).toContain('width="1280"')
    expect(html).toContain('height="720"')
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
    expect(html).toMatch(/20 Proyectos|statProjects/)
    expect(html).toMatch(/AGPLv3|statLicense/)
    expect(html).toContain('GitHub')
  })

  it('has GitHub link', () => {
    expect(html).toContain('https://github.com/madfam-org/yantra4d')
    expect(html).toMatch(/Ver en GitHub|openSourceSection\.cta/)
  })

  it('has tech stack note', () => {
    expect(html).toMatch(/OpenSCAD.*React.*Three\.js|techNote/)
  })
})

// ─── LiveDemo ───────────────────────────────────────────────────────────────
describe('LiveDemo.astro', () => {
  let html: string

  beforeAll(() => {
    html = loadTemplate('LiveDemo.astro')
  })

  it('has a section element', () => {
    expect(html).toContain('<section')
  })

  it('has demo id for anchor navigation', () => {
    expect(html).toContain('id="demo"')
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
