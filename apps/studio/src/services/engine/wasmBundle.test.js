import { describe, it, expect } from 'vitest'
import {
  planBundleFsLayout,
  resolveEntryPath,
  toVirtualPath,
  FONT_DIR,
  FONTCONFIG_PATH,
  VIRTUAL_OPENSCADPATH,
} from './wasmBundle'

/**
 * The bundle -> virtual-filesystem mapping.
 *
 * This is the contract that makes `include <../../libs/BOSL2/std.scad>` resolve
 * in the browser, and it is pure, so it is pinned here rather than discovered in
 * a browser. The layout it produces was verified against the real
 * `openscad-wasm@0.0.4` build: `projects/gridfinity/cup.scad` written at
 * `/projects/gridfinity/cup.scad` alongside `libs/BOSL2/*.scad` at
 * `/libs/BOSL2/*` renders a 331,951-byte STL, exit code 0.
 */

const GRIDFINITY = {
  slug: 'gridfinity',
  engine: 'openscad',
  entry_files: ['cup.scad', 'lid.scad'],
  files: {
    'projects/gridfinity/cup.scad': 'include <../../libs/BOSL2/std.scad>\ncube(1);',
    'projects/gridfinity/lid.scad': 'cube(2);',
    'libs/BOSL2/std.scad': 'include <version.scad>',
    'libs/BOSL2/version.scad': '// version',
  },
}

describe('toVirtualPath', () => {
  it('makes a repo-relative key absolute', () => {
    expect(toVirtualPath('projects/x/a.scad')).toBe('/projects/x/a.scad')
  })

  it('accepts a key that is already absolute', () => {
    expect(toVirtualPath('/libs/BOSL2/std.scad')).toBe('/libs/BOSL2/std.scad')
  })

  it('refuses traversal, empty segments and empty keys', () => {
    // The bundle comes from our own API, but it is still remote input writing
    // to a filesystem. Refusing `..` costs nothing.
    expect(toVirtualPath('../../etc/passwd')).toBeNull()
    expect(toVirtualPath('projects/../../secret')).toBeNull()
    expect(toVirtualPath('projects/./a.scad')).toBeNull()
    expect(toVirtualPath('projects//a.scad')).toBeNull()
    expect(toVirtualPath('')).toBeNull()
    expect(toVirtualPath('/')).toBeNull()
    expect(toVirtualPath(null)).toBeNull()
  })
})

describe('planBundleFsLayout — the include-resolution layout', () => {
  const plan = planBundleFsLayout(GRIDFINITY)

  it('places project files under /projects/<slug>/', () => {
    const paths = plan.files.map(f => f.path)
    expect(paths).toContain('/projects/gridfinity/cup.scad')
    expect(paths).toContain('/projects/gridfinity/lid.scad')
  })

  it('places library files under /libs/, two levels up from the project dir', () => {
    // This is the whole point: `/projects/gridfinity/cup.scad` resolving
    // `../../libs/BOSL2/std.scad` must land on `/libs/BOSL2/std.scad`.
    const paths = plan.files.map(f => f.path)
    expect(paths).toContain('/libs/BOSL2/std.scad')
    expect(paths).toContain('/libs/BOSL2/version.scad')
  })

  it('creates parents before children — FS.mkdir makes no intermediates', () => {
    const depth = p => p.split('/').filter(Boolean).length
    const depths = plan.dirs.map(depth)
    expect(depths).toEqual([...depths].sort((a, b) => a - b))
    expect(plan.dirs).toContain('/projects')
    expect(plan.dirs).toContain('/projects/gridfinity')
    expect(plan.dirs).toContain('/libs')
    expect(plan.dirs).toContain('/libs/BOSL2')
    expect(plan.dirs.indexOf('/libs')).toBeLessThan(plan.dirs.indexOf('/libs/BOSL2'))
  })

  it('resolves entry files to absolute project paths, in order', () => {
    expect(plan.entryPaths).toEqual([
      '/projects/gridfinity/cup.scad',
      '/projects/gridfinity/lid.scad',
    ])
  })

  it('accepts an entry given repo-relative as well as project-relative', () => {
    const plan2 = planBundleFsLayout({
      ...GRIDFINITY,
      entry_files: ['projects/gridfinity/cup.scad'],
    })
    expect(plan2.entryPaths).toEqual(['/projects/gridfinity/cup.scad'])
  })

  it('writes no fontconfig when the cartridge ships no fonts', () => {
    expect(plan.fonts).toEqual([])
    expect(plan.fontsConf).toBeNull()
  })

  it('skips a key that tries to escape the root rather than writing it', () => {
    const escaped = planBundleFsLayout({
      slug: 'x',
      engine: 'openscad',
      entry_files: ['a.scad'],
      files: { 'projects/x/a.scad': 'cube(1);', '../../etc/passwd': 'root:x:0:0' },
    })
    expect(escaped.files.map(f => f.path)).toEqual(['/projects/x/a.scad'])
  })

  it('tolerates a bundle with no files or entries at all', () => {
    const empty = planBundleFsLayout({ slug: 'x', engine: 'openscad', entry_files: [], files: {} })
    expect(empty.files).toEqual([])
    expect(empty.dirs).toEqual([])
    expect(empty.entryPaths).toEqual([])
  })
})

describe('planBundleFsLayout — fonts', () => {
  // The shape the API actually sends: virtual paths for the typefaces, plus one
  // `fonts.conf` key whose value is fontconfig XML rather than base64.
  const SUPPLIED_CONF = '<?xml version="1.0"?><fontconfig>'
    + '<dir>/projects/relief/fonts</dir><dir>/fonts</dir>'
    + '<cachedir>/tmp/fontconfig</cachedir></fontconfig>'

  const withFonts = planBundleFsLayout({
    slug: 'relief',
    engine: 'openscad',
    entry_files: ['plaque.scad'],
    files: { 'projects/relief/plaque.scad': 'text("A");' },
    fonts: {
      'projects/relief/fonts/Label.ttf': 'AAAA',
      'fonts/AllertaStencil-Regular.ttf': 'BBBB',
      'fonts.conf': SUPPLIED_CONF,
    },
  })

  it('mounts each font at the virtual path the bundle gave it', () => {
    // NOT flattened into /fonts: the supplied fonts.conf names these exact
    // directories, so flattening would silently unmount the cartridge's own
    // typeface while leaving the config pointing at an empty directory.
    expect(withFonts.fonts.map(f => f.path).sort()).toEqual([
      '/fonts/AllertaStencil-Regular.ttf',
      '/projects/relief/fonts/Label.ttf',
    ])
  })

  it('writes the API\'s fonts.conf verbatim rather than generating its own', () => {
    // One generator for both renderers: a typeface that resolves on the server
    // and not in the browser is the kind of divergence nobody notices until a
    // customer does.
    expect(withFonts.fontsConf).toBe(SUPPLIED_CONF)
  })

  it('keeps the fonts.conf key out of the font list', () => {
    expect(withFonts.fonts.some(f => f.path.endsWith('fonts.conf'))).toBe(false)
  })

  it('creates every font directory plus the fontconfig cache directory', () => {
    expect(withFonts.dirs).toContain(FONT_DIR)
    expect(withFonts.dirs).toContain('/projects/relief/fonts')
    expect(withFonts.dirs).toContain('/tmp')
    expect(withFonts.dirs).toContain('/tmp/fontconfig')
    expect(FONTCONFIG_PATH).toBe(`${FONT_DIR}/fonts.conf`)
  })

  it('synthesises a fontconfig document when the bundle supplied none', () => {
    // Only the dev-only /scad/ fallback can reach this: it has no API to ask.
    // Without any fonts.conf the WASM build answers every text() with
    // "Fontconfig error: Cannot load default config file: No such file: (null)"
    // and renders the model minus its lettering, at exit code 0. Measured
    // against projects/relief/plaque.scad: 1,479 bytes without, 424,910 with.
    const generated = planBundleFsLayout({
      slug: 'relief',
      engine: 'openscad',
      entry_files: ['plaque.scad'],
      files: { 'projects/relief/plaque.scad': 'text("A");' },
      fonts: { 'fonts/A.ttf': 'AAAA' },
    })
    expect(generated.fontsConf).toContain('<dir>/fonts</dir>')
    expect(generated.fontsConf).toContain('<cachedir>')
  })
})

describe('OPENSCADPATH', () => {
  it('mirrors the search path the server resolved the bundle with', () => {
    // Relative includes need nothing set, but `include <BOSL2/std.scad>` and
    // `include <dotSCAD/src/...>` resolve through this path. A different order
    // would let the browser render a different model from identical source.
    expect(VIRTUAL_OPENSCADPATH).toBe('/libs:/libs/dotSCAD/src:/projects')
  })
})

describe('resolveEntryPath', () => {
  it('maps a mode scad_file onto its bundled path', () => {
    expect(resolveEntryPath(GRIDFINITY, 'cup.scad')).toBe('/projects/gridfinity/cup.scad')
  })

  it('accepts a scad_file the bundle already keys repo-relatively', () => {
    expect(resolveEntryPath(GRIDFINITY, 'projects/gridfinity/lid.scad'))
      .toBe('/projects/gridfinity/lid.scad')
  })

  it('falls back to the project directory for a file the bundle omitted', () => {
    // Better a legible "can\'t open file" from OpenSCAD than a silent wrong path.
    expect(resolveEntryPath(GRIDFINITY, 'missing.scad'))
      .toBe('/projects/gridfinity/missing.scad')
  })
})
