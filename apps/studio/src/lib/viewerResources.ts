import { BufferAttribute, BufferGeometry, Cache, Material, Mesh, Object3D, Skeleton, Texture } from 'three'
// @ts-expect-error three.js examples lack type declarations in this project's TS config
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils'
import type { STLPayload } from './stlPayloadCache'

export function createSTLGeometry(payload: STLPayload): BufferGeometry {
    const geometry = new BufferGeometry()
    try {
        geometry.setAttribute('position', new BufferAttribute(payload.positions.slice(), 3))
        if (payload.normals) geometry.setAttribute('normal', new BufferAttribute(payload.normals.slice(), 3))
        else geometry.computeVertexNormals()
        geometry.computeBoundingSphere()
        geometry.computeBoundingBox()
        return geometry
    } catch (error) {
        geometry.dispose()
        throw error
    }
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
            const clone = mesh.geometry.clone()
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
