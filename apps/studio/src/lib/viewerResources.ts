import { BufferAttribute, BufferGeometry, Cache, Material, Mesh, Object3D, Skeleton, Texture, Vector3 } from 'three'
// @ts-expect-error three.js examples lack type declarations in this project's TS config
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils'
import { computeCreaseNormals, RENDER_CREASE_ANGLE_DEG } from './creaseNormals'
import type { STLPayload } from './stlPayloadCache'

export function createSTLGeometry(payload: STLPayload): BufferGeometry {
    const geometry = new BufferGeometry()
    try {
        geometry.setAttribute('position', new BufferAttribute(payload.positions.slice(), 3))
        // The worker sends crease-angle normals; a payload without them gets the same ones here.
        const normals = payload.normals?.slice() ?? computeCreaseNormals(payload.positions, RENDER_CREASE_ANGLE_DEG)
        geometry.setAttribute('normal', new BufferAttribute(normals, 3))
        geometry.computeBoundingSphere()
        geometry.computeBoundingBox()
        return geometry
    } catch (error) {
        geometry.dispose()
        throw error
    }
}

/**
 * Replace every quantized attribute with a float copy, in place.
 *
 * The models pipeline writes meshopt-compressed GLBs with KHR_mesh_quantization: positions are
 * normalized int16 under a node scale. `applyMatrix4` writes the transformed values back through
 * the attribute, and a normalized integer attribute can only hold [-1, 1], so every point was
 * clamped into a unit cube and every prerendered preview rendered as a box of scratches. Reading
 * the values out as floats first keeps them at their real size.
 */
export function toFloatAttributes(geometry: BufferGeometry): BufferGeometry {
    for (const name of Object.keys(geometry.attributes)) {
        const attr = geometry.getAttribute(name) as BufferAttribute
        if (attr.array instanceof Float32Array && !attr.normalized) continue
        const size = attr.itemSize
        const out = new Float32Array(attr.count * size)
        for (let i = 0; i < attr.count; i++) {
            for (let k = 0; k < size; k++) out[i * size + k] = attr.getComponent(i, k)
        }
        geometry.setAttribute(name, new BufferAttribute(out, size))
    }
    return geometry
}

type CreaseNormalsCompute = (worldPositions: Float32Array, creaseAngleDeg: number) => Float32Array | Promise<Float32Array>

/**
 * Give every mesh in a loaded scene that arrived without normals crease-angle normals, in place.
 *
 * Prerendered previews and the GLB the API converts from an STL carry positions only, and
 * GLTFLoader answers that by flat-shading the material. Each such mesh gets its own un-indexed
 * copy of its geometry (a corner on a crease needs a normal per face, and a geometry shared by
 * two meshes may sit under two different transforms), and the material's flat shading is
 * switched off. A mesh that brought its own normals is left exactly as loaded.
 *
 * Normals are worked out on world-space positions, so the crease test sees the part at its real
 * proportions whatever transform the node carries, then turned back into the mesh's own space;
 * the stored positions are not touched (a preview keeps its quantized ones). The scene belongs
 * to the load, so each replaced geometry is disposed here, once, after every mesh that shared it
 * has its copy.
 *
 * `compute` defaults to the main-thread routine; the loader passes the worker one.
 */
export async function addCreaseNormals(
    scene: Object3D,
    creaseAngleDeg: number,
    compute: CreaseNormalsCompute = computeCreaseNormals,
): Promise<void> {
    const point = new Vector3()
    const pending: { mesh: Mesh; geometry: BufferGeometry; world: Float32Array }[] = []
    const replaced = new Set<BufferGeometry>()
    scene.updateMatrixWorld(true)
    scene.traverse(child => {
        const mesh = child as Mesh
        const source = mesh.isMesh ? mesh.geometry : null
        if (!source?.getAttribute('position') || source.getAttribute('normal')) return
        const geometry = source.index ? source.toNonIndexed() : source.clone()
        const position = geometry.getAttribute('position')
        const world = new Float32Array(position.count * 3)
        for (let i = 0; i < position.count; i++) {
            point.fromBufferAttribute(position, i).applyMatrix4(mesh.matrixWorld).toArray(world, i * 3)
        }
        pending.push({ mesh, geometry, world })
        replaced.add(source)
    })
    let results: Float32Array[]
    try {
        results = await Promise.all(pending.map(({ world }) => compute(world, creaseAngleDeg)))
    } catch (error) {
        for (const { geometry } of pending) geometry.dispose()
        throw error
    }
    pending.forEach(({ mesh, geometry }, k) => {
        const normals = results[k]
        // A normal n in world space is M^-T applied to the local one, so the local one is M^T n.
        // A mirroring transform (negative determinant) reverses the winding the world normals
        // were taken from, so they point inwards: turn them round. A transform that flattens an
        // axis to nothing has no local normal; any unit vector keeps the shader out of NaN.
        const m = mesh.matrixWorld.elements
        const det = mesh.matrixWorld.determinant()
        const sign = det < 0 ? -1 : 1
        for (let i = 0; i < normals.length; i += 3) {
            const x = normals[i], y = normals[i + 1], z = normals[i + 2]
            const lx = m[0] * x + m[1] * y + m[2] * z
            const ly = m[4] * x + m[5] * y + m[6] * z
            const lz = m[8] * x + m[9] * y + m[10] * z
            const length = Math.hypot(lx, ly, lz)
            if (length > 0 && Number.isFinite(length)) {
                normals[i] = (sign * lx) / length; normals[i + 1] = (sign * ly) / length; normals[i + 2] = (sign * lz) / length
            } else {
                normals[i] = 0; normals[i + 1] = 0; normals[i + 2] = 1
            }
        }
        geometry.setAttribute('normal', new BufferAttribute(normals, 3))
        mesh.geometry = geometry
        for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
            const shaded = material as Material & { flatShading?: boolean }
            if (shaded?.flatShading) {
                shaded.flatShading = false
                shaded.needsUpdate = true
            }
        }
    })
    for (const geometry of replaced) geometry.dispose()
}

/** Analysis geometry is independent of the loaded scene and its materials. */
export function mergeGLTFGeometry(scene: Object3D): BufferGeometry | null {
    const clones: BufferGeometry[] = []
    let result: BufferGeometry | null = null
    try {
        scene.updateMatrixWorld(true)
        scene.traverse(child => {
            const mesh = child as Mesh
            if (!mesh.isMesh || !mesh.geometry) return
            const clone = toFloatAttributes(mesh.geometry.clone())
            clones.push(clone)
            clone.applyMatrix4(child.matrixWorld)
        })
        result = clones.length === 1 ? clones[0]
            : clones.length > 1 ? BufferGeometryUtils.mergeGeometries(clones, false) : null
        return result
    } finally {
        for (const clone of clones) if (clone !== result) clone.dispose()
    }
}

/** Dispose each resource once, including resources shared by meshes/scenes. */
export function disposeGLTF(data: { scene: Object3D; scenes?: Object3D[] }): void {
    const geometries = new Set<BufferGeometry>()
    const materials = new Set<Material>()
    const textures = new Set<Texture>()
    const skeletons = new Set<Skeleton>()
    for (const scene of new Set([data.scene, ...(data.scenes ?? [])])) {
        scene.traverse(child => {
            const mesh = child as Mesh & { skeleton?: Skeleton }
            if (mesh.geometry) geometries.add(mesh.geometry)
            if (mesh.skeleton) skeletons.add(mesh.skeleton)
            for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
                if (material) materials.add(material)
            }
        })
    }
    for (const material of materials) {
        for (const value of Object.values(material)) {
            if (value?.isTexture) textures.add(value)
        }
    }
    const images = new Set<{ close?: () => void }>()
    for (const texture of textures) {
        for (const image of Array.isArray(texture.image) ? texture.image : [texture.image]) {
            if (image) images.add(image)
        }
        texture.dispose()
    }
    // With Three's optional global cache enabled, bitmap ownership is external.
    // The Studio leaves it disabled; locally loaded bitmaps must be closed.
    if (!Cache.enabled) for (const image of images) image.close?.()
    for (const material of materials) material.dispose()
    for (const geometry of geometries) geometry.dispose()
    for (const skeleton of skeletons) skeleton.dispose()
}
