import { useRef, useMemo, useState, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { Image, useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import { renderParts } from '../../services/engine/renderService'

interface ProjectData {
    slug: string
    parameters?: Array<{ id: string; default?: unknown }>
    modes?: Array<{ id: string }>
    thumbnail?: string
    [key: string]: unknown
}

interface CarouselItemProps {
    project: ProjectData
    position: [number, number, number]
    gap: number
    index?: number
}

export default function CarouselItem({ project, position, gap }: CarouselItemProps) {
    const groupRef = useRef<THREE.Group>(null)
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
        const d: Record<string, unknown> = {}
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

interface LiveModelProps {
    project: ProjectData
    defaults: Record<string, unknown>
}

function LiveModel({ project, defaults }: LiveModelProps) {
    const [renderResult, setRenderResult] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let cancelled = false

        renderParts(
            project.modes?.[0]?.id || 'default',
            defaults,
            project as never, // manifest
            { project: project.slug }
        )
            .then(parts => {
                if (cancelled) return
                // Use the first part's URL for the preview
                const url = parts?.[0]?.url
                if (url) {
                    setRenderResult(url)
                }
                setLoading(false)
            })
            .catch(err => {
                if (cancelled) return
                console.error("Carousel live render failed:", err)
                setLoading(false)
            })

        return () => {
            cancelled = true
        }
    }, [project, defaults])

    if (loading) {
        return (
            <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="gray" wireframe />
            </mesh>
        )
    }

    if (!renderResult) {
        return (
            <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="red" wireframe />
            </mesh>
        )
    }

    return <GLTFRenderer url={renderResult} />
}

interface GLTFRendererProps {
    url: string
}

function GLTFRenderer({ url }: GLTFRendererProps) {
    const gltf = useGLTF(url)
    if (!gltf.scene) return null

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
