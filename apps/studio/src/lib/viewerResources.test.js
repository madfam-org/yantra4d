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

    it('shades a preview smooth, keeps its real edges and its quantized positions', async () => {
        const { scene, mesh, geometry } = preview()
        const versionBefore = mesh.material.version
        const released = vi.spyOn(geometry, 'dispose')

        await addCreaseNormals(scene, 30)

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

    it('hands the same normals to the analysis geometry, at real size', async () => {
        const { scene } = preview(40)
        await addCreaseNormals(scene, 30)
        const merged = mergeGLTFGeometry(scene)
        merged.computeBoundingBox()
        expect(merged.boundingBox.max.x).toBeCloseTo(40, 3)
        expect(merged.getAttribute('normal').count).toBe(12)
        expect(merged.getAttribute('normal').getZ(0)).toBeCloseTo(1, 6)
    })

    it('draws the line between one surface and an edge at the crease angle', async () => {
        const smooth = fold(25), sharp = fold(25)
        await addCreaseNormals(smooth.scene, 30)
        await addCreaseNormals(sharp.scene, 20)
        expect(sameNormalAtFold(smooth.mesh)).toBe(true)
        expect(sameNormalAtFold(sharp.mesh)).toBe(false)
    })

    it('judges the crease at the size the node draws the part', async () => {
        // 20° apart as stored; the node flattens Z to a tenth, which leaves about 2° on screen.
        const { scene, mesh } = fold(20)
        mesh.scale.set(1, 1, 0.1)
        await addCreaseNormals(scene, 10)
        expect(sameNormalAtFold(mesh)).toBe(true)
        const n = mesh.geometry.getAttribute('normal')
        expect(Math.hypot(n.getX(0), n.getY(0), n.getZ(0))).toBeCloseTo(1, 5)
    })

    it('leaves a mesh that brought its own normals exactly as loaded', async () => {
        const scene = new Scene()
        const mesh = new Mesh(new BoxGeometry(), new MeshStandardMaterial({ flatShading: true }))
        scene.add(mesh)
        const geometry = mesh.geometry, normal = geometry.getAttribute('normal')
        const released = vi.spyOn(geometry, 'dispose')
        await addCreaseNormals(scene, 30)
        expect(mesh.geometry).toBe(geometry)
        expect(geometry.getAttribute('normal')).toBe(normal)
        expect(geometry.index).not.toBeNull()
        expect(mesh.material.flatShading).toBe(true)
        expect(released).not.toHaveBeenCalled()
    })

    it('releases a geometry two meshes share once, after both have their copy', async () => {
        const { scene, mesh, geometry } = preview()
        const twin = new Mesh(geometry, mesh.material)
        twin.position.x = 100
        scene.add(twin)
        const released = vi.spyOn(geometry, 'dispose')
        await addCreaseNormals(scene, 30)
        expect(released).toHaveBeenCalledTimes(1)
        expect(mesh.geometry.getAttribute('normal').count).toBe(12)
        expect(twin.geometry.getAttribute('normal').count).toBe(12)
        expect(twin.geometry).not.toBe(geometry)
    })

    it('gives an STL payload without normals crease-angle ones', async () => {
        const geometry = createSTLGeometry({ positions: new Float32Array([
            0, 0, 0, 1, 0, 0, 0, 1, 0,
            0, 0, 0, 0, 1, 0, -Math.cos(0.2), 0, -Math.sin(0.2), // 11.5° from the first
        ]) })
        const n = geometry.getAttribute('normal')
        expect(n.count).toBe(6)
        expect(n.getX(0)).toBeCloseTo(n.getX(3), 6)
        expect(n.getZ(0)).toBeLessThan(1)
    })

    it('turns the normals round under a mirroring transform', async () => {
        const { scene, mesh } = preview()
        mesh.scale.set(-1, 1, 1)
        await addCreaseNormals(scene, 30)
        const n = mesh.geometry.getAttribute('normal')
        // The floor's local normal is +Z; the mirror flips X only, so it must stay +Z, and the
        // wall's local normal (+X towards the floor's side) must stay +X in local space.
        for (let i = 0; i < 6; i++) expect(n.getZ(i)).toBeCloseTo(1, 6)
        for (let i = 6; i < 12; i++) expect(n.getX(i)).toBeCloseTo(1, 6)
    })

    it('gives a mesh flattened to nothing on one axis finite unit normals', async () => {
        const { scene, mesh } = fold(25)
        mesh.scale.set(1, 1, 0)
        await addCreaseNormals(scene, 30)
        const n = mesh.geometry.getAttribute('normal')
        for (let i = 0; i < n.count; i++) {
            expect(Number.isFinite(n.getX(i)) && Number.isFinite(n.getY(i)) && Number.isFinite(n.getZ(i))).toBe(true)
            expect(Math.hypot(n.getX(i), n.getY(i), n.getZ(i))).toBeCloseTo(1, 5)
        }
    })

    it('gives each mesh its own copy when two share a geometry without an index', async () => {
        const { scene, mesh } = fold(25)
        const shared = mesh.geometry
        const other = new Mesh(shared, new MeshStandardMaterial({ flatShading: true }))
        other.scale.set(1, 1, 0.1)
        scene.add(other)
        await addCreaseNormals(scene, 10)
        expect(mesh.geometry).not.toBe(shared)
        expect(other.geometry).not.toBe(mesh.geometry)
        expect(other.material.flatShading).toBe(false)
        // Judged under its own transform: 25° stays an edge for one, the flattened one is smooth.
        expect(sameNormalAtFold(mesh)).toBe(false)
        expect(sameNormalAtFold(other)).toBe(true)
        expect(shared.getAttribute('normal')).toBeUndefined()
    })

    it('hands the positions to the compute it is given, and leaves the scene alone if it fails', async () => {
        const { scene, mesh, geometry } = preview()
        const seen = []
        await addCreaseNormals(scene, 30, (world, angle) => { seen.push([world.length, angle]); return Promise.resolve(new Float32Array(world.length).fill(0).map((_, i) => (i % 3 === 2 ? 1 : 0))) })
        expect(seen).toEqual([[36, 30]])
        expect(mesh.geometry.getAttribute('normal').getZ(0)).toBe(1)

        expect(geometry.getAttribute('normal')).toBeUndefined()

        const failing = preview()
        const copies = []
        const toNonIndexed = failing.geometry.toNonIndexed.bind(failing.geometry)
        vi.spyOn(failing.geometry, 'toNonIndexed').mockImplementation(() => {
            const copy = toNonIndexed()
            copies.push(vi.spyOn(copy, 'dispose'))
            return copy
        })
        const releasedSource = vi.spyOn(failing.geometry, 'dispose')
        await expect(addCreaseNormals(failing.scene, 30, () => Promise.reject(new Error('worker gone')))).rejects.toThrow('worker gone')
        expect(failing.mesh.geometry).toBe(failing.geometry)
        expect(failing.mesh.material.flatShading).toBe(true)
        expect(failing.geometry.getAttribute('normal')).toBeUndefined()
        // The copy made for the failed attempt is released; the source still belongs to the scene.
        expect(copies).toHaveLength(1)
        expect(copies[0]).toHaveBeenCalledTimes(1)
        expect(releasedSource).not.toHaveBeenCalled()
    })
})
