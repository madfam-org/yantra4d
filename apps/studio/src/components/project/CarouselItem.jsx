import { useRef, useMemo, useState, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { Image, useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import { getApiBase } from '../../services/backendDetection'

export default function CarouselItem({ project, position, gap }) {
    const groupRef = useRef()
    const [isActive, setIsActive] = useState(false)

    // We use a global state equivalent or prop-driven active check.
    // In our architecture, the parent ScrollControls handles the global panning X offset.
    // The closest item to world X=0 is active.

    useFrame(() => {
        if (!groupRef.current) return

        // Find world position of this item
        const worldPos = new THREE.Vector3()
        groupRef.current.getWorldPosition(worldPos)

        // It is "active" if it's within 0.5 distance of the center X=0
        const dist = Math.abs(worldPos.x)
        const active = dist < (gap * 0.5)

        if (active !== isActive) {
            setIsActive(active)
        }

        // Turntable rotation only if active
        if (active) {
            groupRef.current.rotation.y += 0.005
        } else {
            // Lerp back to front-facing when inactive
            groupRef.current.rotation.y += (0 - groupRef.current.rotation.y) * 0.1
        }

        // Z Depth Parallax effect: push inactive items slightly back
        const targetZ = active ? 1 : 0
        groupRef.current.position.z += (targetZ - groupRef.current.position.z) * 0.1

        // Scale effect
        const targetScale = active ? 1.2 : 1.0
        groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1)
    })

    // Conditional Rendering Hook Logic
    // Only attempt to load complex 3D geometry if active or hovered to save system resources.

    // We'll construct a mock parameters object from defaults just to get a mesh output
    const defaults = useMemo(() => {
        const d = {}
        if (project.parameters) {
            project.parameters.forEach(p => {
                if (p.default !== undefined) d[p.id] = p.default
            })
        }
        return d
    }, [project.parameters])

    return (
        <group ref={groupRef} position={position}>

            {/* If Not Active, show highly optimized Thumbnail Plane */}
            {(!isActive && project.thumbnail) && (
                <Image
                    url={project.thumbnail}
                    transparent
                    opacity={1}
                    scale={[3, 2, 1]}
                    radius={0.1}
                />
            )}

            {/* If Active (or fallback no-thumbnail), try to render Live Model */}
            {isActive && (
                <LiveModel project={project} defaults={defaults} />
            )}
        </group>
    )
}

function LiveModel({ project, defaults }) {
    // For simplicity in the gallery, we look for a cached `.glb` if possible?
    // In Yantra4D, if it's a demo hyperobject like Tablaco, maybe it has a `project / tablaco / cache / main.glb`
    // Alternatively, we use the `useWorkerLoader` hook which triggers OpenSCAD directly.

    const [renderResult, setRenderResult] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Trigger generic WebWorker compilation of default parameters
        const url = `${getApiBase()}/api/render/${project.slug}`

        const payload = {
            mode: project.modes?.[0]?.id || 'default',
            parameters: defaults,
            format: 'gltf'
        }

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(res => res.blob())
            .then(blob => {
                const objectUrl = URL.createObjectURL(blob)
                setRenderResult(objectUrl)
                setLoading(false)
            })
            .catch(err => {
                console.error("Carousel live render failed:", err)
                // Fallback to static if failed
                setLoading(false)
            })

        return () => {
            // Cleanup Object URLs here if we unmount
        }
    }, [project.slug, project.modes, defaults])

    const gltf = useGLTF(renderResult || '/default-placeholder.glb')

    if (loading) {
        return (
            <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="gray" wireframe />
            </mesh>
        )
    }

    if (!renderResult || !gltf.scene) return null

    // Center and normalize the imported GLTF scale for uniform gallery viewing
    const box = new THREE.Box3().setFromObject(gltf.scene)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)

    // Scale down to roughly 2-3 units wide
    const normalizedScale = 2.5 / maxDim

    return (
        <group scale={normalizedScale} position={[-center.x * normalizedScale, -center.y * normalizedScale, -center.z * normalizedScale]}>
            <primitive object={gltf.scene} />
        </group>
    )
}

// Preload the placeholder just in case
useGLTF.preload('/default-placeholder.glb')
