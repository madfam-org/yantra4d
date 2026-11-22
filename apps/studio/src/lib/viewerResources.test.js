import { afterEach, describe, it, expect, vi } from 'vitest'
import { BufferAttribute, BufferGeometry, BoxGeometry, Cache, Group, Mesh, MeshStandardMaterial, Scene, Texture } from 'three'
import { addCreaseNormals, createSTLGeometry, mergeGLTFGeometry, disposeGLTF, toFloatAttributes } from './viewerResources'

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

describe('prerendered previews from the models pipeline', () => {
    // Pipeline GLBs carry KHR_mesh_quantization: normalized int16 positions under a node scale.
    const quantized = (length) => {
        const scene = new Scene()
        const node = new Group()
        node.scale.setScalar(length / 2)
        node.position.set(5, 0, 0)
        const g = new BufferGeometry()
        g.setAttribute('position', new BufferAttribute(new Int16Array([0, 0, 0, 32767, 0, 0, 0, 32767, 0, -32767, 0, 32767]), 3, true))
        g.setAttribute('normal', new BufferAttribute(new Int8Array([0, 0, 127, 0, 0, 127, 0, 0, 127, 0, 0, 127]), 3, true))
        node.add(new Mesh(g, new MeshStandardMaterial()))
        scene.add(node)
        return scene
    }

    it('keeps a quantized mesh at its real size instead of clamping it into a unit cube', () => {
        const merged = mergeGLTFGeometry(quantized(480))
        merged.computeBoundingBox()
        expect(merged.boundingBox.max.x).toBeCloseTo(245, 0)
        expect(merged.boundingBox.min.x).toBeCloseTo(-235, 0)
        expect(merged.boundingBox.max.z).toBeCloseTo(240, 0)
        expect(merged.getAttribute('position').array).toBeInstanceOf(Float32Array)
        expect(merged.getAttribute('normal').getZ(0)).toBeCloseTo(1, 2)
    })

    it('leaves float geometry as it was', () => {
        const g = new BoxGeometry(2, 2, 2)
        const before = g.getAttribute('position')
        expect(toFloatAttributes(g).getAttribute('position')).toBe(before)
    })
})

describe('crease-angle normals for meshes that arrive without any', () => {
    const Q = 32767
    // A floor in the XY plane and a wall standing on its X = 0 edge, the way the models pipeline
    // writes a preview: indexed, normalized int16 positions, no normals, under a node scale.
    const preview = (scale = 40) => {
        const scene = new Scene()
        const node = new Group()
        node.scale.setScalar(scale)
        const geometry = new BufferGeometry()
        geometry.setAttribute('position', new BufferAttribute(new Int16Array([
            0, 0, 0, Q, 0, 0, Q, Q, 0, 0, Q, 0,
            0, 0, Q, 0, Q, Q,
        ]), 3, true))
        geometry.setIndex([0, 1, 2, 0, 2, 3, 0, 3, 5, 0, 5, 4])
        // GLTFLoader flat-shades the material of a primitive without normals.
        const mesh = new Mesh(geometry, new MeshStandardMaterial({ flatShading: true }))
        node.add(mesh)
        scene.add(node)
        return { scene, mesh, geometry }
    }
    // Two triangles sharing the Y axis, folded by `degrees`.
    const fold = (degrees) => {
        const a = (degrees * Math.PI) / 180
        const geometry = new BufferGeometry()
        geometry.setAttribute('position', new BufferAttribute(new Float32Array([
            0, 0, 0, 1, 0, 0, 0, 1, 0,
            0, 0, 0, 0, 1, 0, -Math.cos(a), 0, -Math.sin(a),
        ]), 3))
        const mesh = new Mesh(geometry, new MeshStandardMaterial({ flatShading: true }))
        return { scene: new Scene().add(mesh), mesh }
    }
    const sameNormalAtFold = (mesh) => {
        const n = mesh.geometry.getAttribute('normal')
        return Math.abs(n.getX(0) - n.getX(3)) < 1e-6 && Math.abs(n.getZ(0) - n.getZ(3)) < 1e-6
    }

    it('shades a preview smooth, keeps its real edges and its quantized positions', () => {
        const { scene, mesh, geometry } = preview()
        const versionBefore = mesh.material.version
        const released = vi.spyOn(geometry, 'dispose')

        addCreaseNormals(scene, 30)

        expect(mesh.geometry).not.toBe(geometry)
        expect(released).toHaveBeenCalledTimes(1)
        expect(mesh.geometry.index).toBeNull()
        const position = mesh.geometry.getAttribute('position')
        expect(position.array).toBeInstanceOf(Int16Array)
        expect(position.normalized).toBe(true)
        const normal = mesh.geometry.getAttribute('normal')
        expect(normal.count).toBe(12)
        // The floor points along Z and the wall along X: the 90° edge between them stays.
        for (let i = 0; i < 6; i++) expect(normal.getZ(i)).toBeCloseTo(1, 6)
        for (let i = 6; i < 12; i++) expect(normal.getX(i)).toBeCloseTo(1, 6)
        expect(mesh.material.flatShading).toBe(false)
        expect(mesh.material.version).toBeGreaterThan(versionBefore)
    })

    it('hands the same normals to the analysis geometry, at real size', () => {
        const { scene } = preview(40)
        addCreaseNormals(scene, 30)
        const merged = mergeGLTFGeometry(scene)
        merged.computeBoundingBox()
        expect(merged.boundingBox.max.x).toBeCloseTo(40, 3)
        expect(merged.getAttribute('normal').count).toBe(12)
        expect(merged.getAttribute('normal').getZ(0)).toBeCloseTo(1, 6)
    })

    it('draws the line between one surface and an edge at the crease angle', () => {
        const smooth = fold(25), sharp = fold(25)
        addCreaseNormals(smooth.scene, 30)
        addCreaseNormals(sharp.scene, 20)
        expect(sameNormalAtFold(smooth.mesh)).toBe(true)
        expect(sameNormalAtFold(sharp.mesh)).toBe(false)
    })

    it('judges the crease at the size the node draws the part', () => {
        // 20° apart as stored; the node flattens Z to a tenth, which leaves about 2° on screen.
        const { scene, mesh } = fold(20)
        mesh.scale.set(1, 1, 0.1)
        addCreaseNormals(scene, 10)
        expect(sameNormalAtFold(mesh)).toBe(true)
        const n = mesh.geometry.getAttribute('normal')
        expect(Math.hypot(n.getX(0), n.getY(0), n.getZ(0))).toBeCloseTo(1, 5)
    })

    it('leaves a mesh that brought its own normals exactly as loaded', () => {
        const scene = new Scene()
        const mesh = new Mesh(new BoxGeometry(), new MeshStandardMaterial({ flatShading: true }))
        scene.add(mesh)
        const geometry = mesh.geometry, normal = geometry.getAttribute('normal')
        const released = vi.spyOn(geometry, 'dispose')
        addCreaseNormals(scene, 30)
        expect(mesh.geometry).toBe(geometry)
        expect(geometry.getAttribute('normal')).toBe(normal)
        expect(geometry.index).not.toBeNull()
        expect(mesh.material.flatShading).toBe(true)
        expect(released).not.toHaveBeenCalled()
    })

    it('releases a geometry two meshes share once, after both have their copy', () => {
        const { scene, mesh, geometry } = preview()
        const twin = new Mesh(geometry, mesh.material)
        twin.position.x = 100
        scene.add(twin)
        const released = vi.spyOn(geometry, 'dispose')
        addCreaseNormals(scene, 30)
        expect(released).toHaveBeenCalledTimes(1)
        expect(mesh.geometry.getAttribute('normal').count).toBe(12)
        expect(twin.geometry.getAttribute('normal').count).toBe(12)
        expect(twin.geometry).not.toBe(geometry)
    })

    it('gives an STL payload without normals crease-angle ones', () => {
        const geometry = createSTLGeometry({ positions: new Float32Array([
            0, 0, 0, 1, 0, 0, 0, 1, 0,
            0, 0, 0, 0, 1, 0, -Math.cos(0.2), 0, -Math.sin(0.2), // 11.5° from the first
        ]) })
        const n = geometry.getAttribute('normal')
        expect(n.count).toBe(6)
        expect(n.getX(0)).toBeCloseTo(n.getX(3), 6)
        expect(n.getZ(0)).toBeLessThan(1)
    })
})
