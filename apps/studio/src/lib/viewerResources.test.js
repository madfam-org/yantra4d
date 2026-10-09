import { afterEach, describe, it, expect, vi } from 'vitest'
import { BufferGeometry, BoxGeometry, Cache, Mesh, MeshStandardMaterial, Scene, Texture } from 'three'
import { mergeGLTFGeometry, disposeGLTF } from './viewerResources'

afterEach(() => { vi.restoreAllMocks(); Cache.enabled = false })

describe('GLTF resource ownership', () => {
  it('releases temporary clones after merging and preserves world transforms', () => {
    const scene = new Scene()
    const first = new Mesh(new BoxGeometry(2, 2, 2))
    const second = new Mesh(new BoxGeometry(2, 2, 2))
    second.position.x = 10
    scene.add(first, second)
    const released = []
    vi.spyOn(BufferGeometry.prototype, 'dispose').mockImplementation(function () { released.push(this) })
    const merged = mergeGLTFGeometry(scene)
    merged.computeBoundingBox()
    expect(merged.boundingBox.min.x).toBe(-1)
    expect(merged.boundingBox.max.x).toBe(11)
    expect(released).toHaveLength(2)
    expect(released).not.toContain(merged)
    expect(released).not.toContain(first.geometry)
    expect(released).not.toContain(second.geometry)
  })

  it('releases all temporary clones if incompatible meshes cannot merge', () => {
    const scene = new Scene()
    const second = new Mesh(new BoxGeometry())
    second.geometry.deleteAttribute('uv')
    scene.add(new Mesh(new BoxGeometry()), second)
    const released = vi.spyOn(BufferGeometry.prototype, 'dispose')
    vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(mergeGLTFGeometry(scene)).toBeNull()
    expect(released).toHaveBeenCalledTimes(2)
  })

  it('releases unselected scenes and array materials without double disposal', () => {
    const first = new Scene(), second = new Scene()
    const geometry = new BoxGeometry()
    const material = new MeshStandardMaterial()
    const other = new MeshStandardMaterial()
    const bitmap = { close: vi.fn() }
    material.map = new Texture(bitmap)
    other.map = new Texture(bitmap)
    first.add(new Mesh(geometry, material))
    second.add(new Mesh(geometry, [material, other]))
    const release = vi.spyOn(geometry, 'dispose')
    const releaseMaterial = vi.spyOn(material, 'dispose')
    const releaseOther = vi.spyOn(other, 'dispose')
    disposeGLTF({ scene: first, scenes: [first, second] })
    expect(release).toHaveBeenCalledTimes(1)
    expect(releaseMaterial).toHaveBeenCalledTimes(1)
    expect(releaseOther).toHaveBeenCalledTimes(1)
    expect(bitmap.close).toHaveBeenCalledTimes(1)
  })

  it('does not close image bitmaps owned by an explicitly enabled external cache', () => {
    Cache.enabled = true
    const scene = new Scene()
    const mesh = new Mesh(new BoxGeometry(), new MeshStandardMaterial())
    const bitmap = { close: vi.fn() }
    mesh.material.map = new Texture(bitmap)
    scene.add(mesh)
    const releaseTexture = vi.spyOn(mesh.material.map, 'dispose')
    disposeGLTF({ scene })
    expect(releaseTexture).toHaveBeenCalledTimes(1)
    expect(bitmap.close).not.toHaveBeenCalled()
  })
})
