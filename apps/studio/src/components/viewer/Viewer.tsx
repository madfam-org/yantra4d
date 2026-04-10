import React, { Suspense, useState, useEffect, useMemo, memo, forwardRef, useImperativeHandle, useCallback } from 'react'
import * as THREE from 'three'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, OrthographicCamera, Grid, Environment, Edges, Bounds, GizmoHelper, GizmoViewport, Html } from '@react-three/drei'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils'
import { useWorkerLoader } from '../../hooks/render/useWorkerLoader'
import { Box3, Box3Helper, Vector3, Color, Plane as ThreePlane } from 'three'
import { useIsMobile } from '../../hooks/system/useMediaQuery'
import { useLanguage } from "../../contexts/system/LanguageProvider"
import { useTheme } from "../../contexts/system/ThemeProvider"
import { useManifest } from "../../contexts/project/ManifestProvider"
import { ErrorBoundary } from '../feedback/ErrorBoundary'
import SceneController, { type SceneControllerHandle } from './SceneController'
import NumberedAxes from './NumberedAxes'
import AnimatedGrid from './AnimatedGrid'
import { computeVolumeMm3, computeBoundingBox, computeCentroid } from '../../lib/printEstimator'
import ClippingPlane from './ClippingPlane'
import MeasureTool from './MeasureTool'
import ThicknessOverlay from './ThicknessOverlay'
import OverhangOverlay from './OverhangOverlay'
import ParameterPreviewOverlay from './ParameterPreviewOverlay'
import type { GhostVariants } from './GhostGeometryOverlay'

const DEFAULT_AXIS_COLORS = ['#ef4444', '#22c55e', '#3b82f6']
// Grid colors will be evaluated dynamically based on theme.

/** Camera constants — kept as named values to avoid magic numbers in JSX */
const CAMERA_FOV_DESKTOP = 45
const CAMERA_FOV_MOBILE = 60
const ORBIT_MIN_DISTANCE_MM = 0.5
const ORBIT_MAX_DISTANCE_MM = 5000  // far enough for large assemblies (mm)
const SCENE_UP_VECTOR: [number, number, number] = [0, 0, 1]   // Z-up coordinate system

type HighlightMode = 'normal' | 'highlight' | 'ghost' | 'hidden' | 'preview'

interface PartData {
    type: string
    url: string
    isGlb?: boolean
}

interface ThicknessData {
    points: number[][]
    thicknesses: number[]
}

interface OverhangData {
    points: number[][]
    angles: number[]
    threshold_deg?: number
}

interface HoveredParam {
    paramId: string
    paramDef: { min?: number; max?: number }
    hint: { type: string; axis: string; scale_factor?: number; affected_parts?: string[] }
    currentValue?: number
}

interface Measurement {
    a: THREE.Vector3
    b: THREE.Vector3
    distance: number
}

interface GeometryStats {
    total: { volumeMm3: number; boundingBox: { width: number; depth: number; height: number } | null; triangleCount: number }
    parts: Record<string, { volumeMm3: number; boundingBox: { width: number; depth: number; height: number } }>
}

interface ModelProps {
    url: string
    isGlb?: boolean
    partType: string
    color: string
    wireframe: boolean
    glass: boolean
    onGeometry?: (partType: string, geometry: THREE.BufferGeometry) => void
    onGeometryRemove?: (partType: string) => void
    highlightMode: HighlightMode
    isDark: boolean
}

const Model = ({ url, isGlb, partType, color, wireframe, glass, onGeometry, onGeometryRemove, highlightMode, isDark }: ModelProps) => {
    const bareUrl = (url || '').split('?')[0].toLowerCase()
    const isGLTF = isGlb || bareUrl.endsWith('.gltf') || bareUrl.endsWith('.glb')

    // Asynchronously loads geometries; .stl via WebWorker, .gltf natively.
    const { geometry: geom, scene: gltfScene } = useWorkerLoader(url, isGLTF)

    useEffect(() => {
        if (geom && onGeometry) onGeometry(partType, geom)
        return () => {
            if (onGeometryRemove) onGeometryRemove(partType)
        }
    }, [geom, partType, onGeometry, onGeometryRemove])

    // Apply the React-driven UI colors to native GLTF/GLB scenes.
    // The backend `stl_to_glb` optimizer generates default grey materials, 
    // so we must traverse and inject the correct dynamic part color here.
    useEffect(() => {
        if (gltfScene && color) {
            gltfScene.traverse((child) => {
                const mesh = child as THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>
                if (mesh.isMesh && mesh.material) {
                    // Update material color natively to reflect the UI color picker
                    mesh.material.color.set(color)
                    // If Emissive is active, copy the emissive props too
                    const isHighlight = highlightMode === 'highlight'
                    const isPreviewGltf = highlightMode === 'preview'
                    mesh.material.emissive.set(isHighlight ? color : isPreviewGltf ? '#f59e0b' : '#000000')
                    mesh.material.emissiveIntensity = isHighlight ? 0.15 : isPreviewGltf ? 0.25 : 0

                    mesh.material.needsUpdate = true
                }
            })
        }
    }, [gltfScene, color, highlightMode])

    // highlightMode: 'normal' | 'highlight' | 'ghost' | 'hidden' | 'preview'
    if (highlightMode === 'hidden') return null
    if (!geom) return null

    const isGhost = highlightMode === 'ghost'
    const isHighlight = highlightMode === 'highlight'
    const isPreview = highlightMode === 'preview'
    const emissive = isHighlight ? color : isPreview ? '#f59e0b' : '#000000'
    const emissiveIntensity = isHighlight ? 0.15 : isPreview ? 0.25 : 0

    // Glass material: physically-based transparent rendering
    if (glass) {
        const glassOpacity = wireframe ? 0.1 : 0.35
        return (
            <mesh geometry={geom}>
                <meshPhysicalMaterial
                    key={`glass-${wireframe}`}
                    color={color}
                    roughness={0.05}
                    metalness={0.0}
                    transmission={0.9}
                    transparent={true}
                    opacity={glassOpacity}
                    ior={1.5}
                    thickness={2}
                    depthWrite={false}
                />
                <Edges threshold={30} color={color} />
            </mesh>
        )
    }

    const opacity = wireframe ? 0.2 : isGhost ? 0.15 : 1

    // If it's a native GLTF scene and we have no material overrides (like wireframe/ghost), render the rich scene!
    if (gltfScene && !wireframe && !isGhost && !glass) {
        return (
            <group>
                <primitive object={gltfScene} />
                {!isGhost && <Edges geometry={geom} threshold={15} color={isDark ? "#ffffff" : "#18181b"} />}
            </group>
        )
    }

    return (
        <mesh geometry={geom}>
            <meshStandardMaterial
                key={`${wireframe}-${highlightMode}`}
                color={color}
                roughness={0.5}
                metalness={0.1}
                transparent={wireframe || isGhost}
                opacity={opacity}
                emissive={emissive}
                emissiveIntensity={emissiveIntensity}
                depthWrite={!isGhost}
            />
            {!isGhost && <Edges threshold={15} color={isDark ? "#ffffff" : "#18181b"} />}
        </mesh>
    )
}

interface LoadingOverlayProps {
    loading: boolean
    progress: number
    progressPhase?: string | null
    t: (key: string) => string
}

const LoadingOverlay = memo(function LoadingOverlay({ loading, progress, progressPhase, t }: LoadingOverlayProps) {
    if (!loading) return null
    return (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
            <div className="text-base sm:text-xl font-bold">{t("loader.loading")}</div>
            <div className="mt-2 h-2 w-32 sm:w-48 overflow-hidden rounded-full bg-secondary">
                <div
                    className="h-full bg-primary transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                />
            </div>
            <div className="mt-1 text-sm text-muted-foreground">{progress}%</div>
            {progressPhase && (
                <div className="text-sm text-muted-foreground mt-1 text-center max-w-[60vw]">{progressPhase}</div>
            )}
        </div>
    )
})

interface BoundingBoxHelperProps {
    boundingBox: boolean
    box: THREE.Box3 | null
    formatDimension: ((value: number, decimals?: number) => string) | null
    children: React.ReactNode
}

const BoundingBoxHelper = ({ boundingBox, box, formatDimension, children }: BoundingBoxHelperProps) => {
    // Only compute center and size if box exists
    const center = box ? box.getCenter(new Vector3()) : new Vector3()
    const size = box ? box.getSize(new Vector3()) : new Vector3()

    return (
        <group>
            {children}
            {boundingBox && box && (
                <group>
                    <mesh position={center}>
                        <boxGeometry args={[size.x, size.y, size.z]} />
                        <meshBasicMaterial visible={false} />
                        <Edges color="#06b6d4" linewidth={1.5} />
                    </mesh>
                    {/* Width label (X axis) - bottom front edge */}
                    <Html
                        position={[box.min.x + (box.max.x - box.min.x) / 2, box.min.y, box.min.z]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {formatDimension ? formatDimension(box.max.x - box.min.x) : `${(box.max.x - box.min.x).toFixed(1)}mm`}
                        </div>
                    </Html>
                    {/* Depth label (Y axis) - bottom right edge */}
                    <Html
                        position={[box.max.x, box.min.y + (box.max.y - box.min.y) / 2, box.min.z]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {formatDimension ? formatDimension(box.max.y - box.min.y) : `${(box.max.y - box.min.y).toFixed(1)}mm`}
                        </div>
                    </Html>
                    {/* Height label (Z axis) - back left edge */}
                    <Html
                        position={[box.min.x, box.max.y, box.min.z + (box.max.z - box.min.z) / 2]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {formatDimension ? formatDimension(box.max.z - box.min.z) : `${(box.max.z - box.min.z).toFixed(1)}mm`}
                        </div>
                    </Html>
                </group>
            )}
        </group>
    )
}

/** Use wider FOV on narrow viewports so models fit better on mobile */
function useResponsiveFov() {
    const isMobile = useIsMobile()
    return isMobile ? CAMERA_FOV_MOBILE : CAMERA_FOV_DESKTOP
}

export interface ViewerHandle {
    captureSnapshot: () => string | undefined
    setCameraView: (view: string) => void
    animateTo: (position: number[], target?: number[] | null, duration?: number) => void
    getCameraState: () => { position: number[]; target: number[] } | undefined
}

interface ViewerProps {
    parts?: PartData[]
    colors: Record<string, string>
    wireframe: boolean
    boundingBox: boolean
    loading: boolean
    progress: number
    progressPhase?: string | null
    animating: boolean
    setAnimating: React.Dispatch<React.SetStateAction<boolean>>
    mode: string
    params: Record<string, unknown>
    onGeometryStats?: (stats: GeometryStats) => void
    assemblyActive: boolean
    highlightedParts?: string[]
    visibleParts?: string[]
    headDiffMode?: boolean
    headParts?: PartData[]
    hoveredParam?: HoveredParam | null
    cachedVariants?: Map<string, GhostVariants> | null
    orthoCamera?: boolean
    setOrthoCamera?: React.Dispatch<React.SetStateAction<boolean>>
    clippingEnabled?: boolean
    clippingAxis?: 'x' | 'y' | 'z'
    clippingPosition?: number
    measureMode?: boolean
    onMeasure?: (measurement: Measurement) => void
    measurements?: Measurement[]
    explodeFactor?: number
    lightIntensity?: number
    environmentPreset?: string
    thicknessData?: ThicknessData | null
    overhangData?: OverhangData | null
    formatDimension?: ((value: number, decimals?: number) => string) | null
    unit?: string
}

const Viewer = forwardRef<ViewerHandle, ViewerProps>(({ parts = [], colors, wireframe, boundingBox, loading, progress, progressPhase, animating, setAnimating, mode, params, onGeometryStats, assemblyActive, highlightedParts = [], visibleParts = [], headDiffMode = false, headParts = [], hoveredParam = null, cachedVariants = null, orthoCamera = false, setOrthoCamera, clippingEnabled = false, clippingAxis = 'z', clippingPosition = 0.5, measureMode = false, onMeasure, measurements = [], explodeFactor = 0, lightIntensity = 1.0, environmentPreset = 'city', thicknessData = null, overhangData = null, formatDimension = null, unit = 'mm' }, ref) => {
    const geometriesRef = React.useRef<Record<string, THREE.BufferGeometry>>({})
    const prevCenterRef = React.useRef<number[] | null>(null)
    const prevMaxDimRef = React.useRef<number | null>(null)
    const sceneRef = React.useRef<SceneControllerHandle>(null)
    const [centerOfMass, setCenterOfMass] = useState<number[]>([0, 0, 0])
    const [sceneBox, setSceneBox] = useState<THREE.Box3 | null>(null)

    const recalculateSceneStats = useCallback(() => {
        // Aggregate stats across all parts, and collect per-part stats for individual estimates
        let totalVolume = 0
        let totalTriangles = 0
        const weightedCenterSum = { x: 0, y: 0, z: 0 }
        let mergedBox: { width: number; depth: number; height: number } | null = null
        let absoluteBox: Box3 | null = null
        const perPartStats: Record<string, { volumeMm3: number; boundingBox: { width: number; depth: number; height: number } }> = {}

        for (const [partType, geom] of Object.entries(geometriesRef.current)) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const geomAny = geom as any
            const vol = computeVolumeMm3(geomAny)
            totalVolume += vol

            // Count triangles from geometry
            const triCount = geom.index
                ? geom.index.count / 3
                : (geom.attributes?.position?.count || 0) / 3
            totalTriangles += triCount
            const centroid = computeCentroid(geomAny)

            weightedCenterSum.x += centroid.x * vol
            weightedCenterSum.y += centroid.y * vol
            weightedCenterSum.z += centroid.z * vol

            const bbox = computeBoundingBox(geomAny)

            // Collect individual part stats for per-part print estimates
            perPartStats[partType] = { volumeMm3: vol, boundingBox: bbox }

            if (!mergedBox) {
                mergedBox = bbox
            } else {
                mergedBox = {
                    width: Math.max(mergedBox.width, bbox.width),
                    depth: Math.max(mergedBox.depth, bbox.depth),
                    height: Math.max(mergedBox.height, bbox.height),
                }
            }

            if (!geom.boundingBox) geom.computeBoundingBox()
            if (!absoluteBox) {
                absoluteBox = new Box3().copy(geom.boundingBox!)
            } else {
                absoluteBox.union(geom.boundingBox!)
            }
        }

        setSceneBox(absoluteBox)

        if (totalVolume > 0) {
            const newCenter = [
                weightedCenterSum.x / totalVolume,
                weightedCenterSum.y / totalVolume,
                weightedCenterSum.z / totalVolume
            ]
            setCenterOfMass(newCenter)

            if (mergedBox) {
                const maxDim = Math.max(mergedBox.width, mergedBox.depth, mergedBox.height)

                let shouldAnimate = false
                if (!prevCenterRef.current || !prevMaxDimRef.current) {
                    shouldAnimate = true
                } else {
                    const dist = Math.hypot(
                        newCenter[0] - prevCenterRef.current[0],
                        newCenter[1] - prevCenterRef.current[1],
                        newCenter[2] - prevCenterRef.current[2]
                    )
                    const scaleDiff = Math.abs(maxDim - prevMaxDimRef.current)
                    if (dist > 1.0 || scaleDiff > 1.0) {
                        shouldAnimate = true
                    }
                }

                if (shouldAnimate) {
                    const offset = maxDim * 1.5
                    const newPos = [
                        newCenter[0] + offset,
                        newCenter[1] + offset,
                        newCenter[2] + offset
                    ]
                    sceneRef.current?.animateTo(newPos, newCenter, 0.5)
                }

                prevCenterRef.current = newCenter
                prevMaxDimRef.current = maxDim
            }
        } else {
            // Handle complete empty state
            setCenterOfMass([0, 0, 0])
        }

        onGeometryStats?.({
            total: { volumeMm3: totalVolume, boundingBox: mergedBox, triangleCount: Math.round(totalTriangles) },
            parts: perPartStats,
        })
    }, [onGeometryStats])

    const handleGeometry = useCallback((partType: string, geometry: THREE.BufferGeometry) => {
        geometriesRef.current[partType] = geometry
        geometry.computeBoundingBox()
        recalculateSceneStats()
    }, [recalculateSceneStats])

    const handleGeometryRemove = useCallback((partType: string) => {
        if (geometriesRef.current[partType]) {
            delete geometriesRef.current[partType]
            recalculateSceneStats()
        }
    }, [recalculateSceneStats])

    const { language, t } = useLanguage()
    const { theme } = useTheme()
    const { getCameraViews, getViewerConfig, getLabel, getMode, manifest } = useManifest()

    // Helper: get the precomputed initial bounding box for the current mode from the manifest
    const getModeBbox = useCallback((modeId: string): { center_mm: number[]; max_dim_mm: number } | null => {
        const mode = manifest?.modes?.find(m => m.id === modeId)
        return (mode?.initial_bbox as { center_mm: number[]; max_dim_mm: number } | undefined) || null
    }, [manifest])

    const viewerAxisColors = manifest?.viewer?.axis_colors as { x?: string; y?: string; z?: string } | undefined
    const axisColors: [string, string, string] = viewerAxisColors
        ? [viewerAxisColors.x || DEFAULT_AXIS_COLORS[0], viewerAxisColors.y || DEFAULT_AXIS_COLORS[1], viewerAxisColors.z || DEFAULT_AXIS_COLORS[2]]
        : DEFAULT_AXIS_COLORS as [string, string, string]
    const cameraViews = getCameraViews()
    const viewerConfig = getViewerConfig()
    const defaultColor = (viewerConfig.default_color as string) || "#e5e7eb"
    const isoView = cameraViews.find(v => v.id === 'iso') || cameraViews[0]
    const initialCameraPos: [number, number, number] = (isoView?.position || [50, 50, 50]) as [number, number, number]

    // Structural parts: in grid mode but not in assembly mode (e.g. rods, stoppers)
    const gridMode = getMode('grid')
    const assemblyMode = getMode('assembly')
    const structuralPartIds = useMemo(() => {
        if (!gridMode || !assemblyMode) return []
        return gridMode.parts.filter(p => !assemblyMode.parts.includes(p))
    }, [gridMode, assemblyMode])

    const [showAxes, setShowAxes] = useState(true)
    const [activeView, setActiveView] = useState('iso')
    const [animReady, setAnimReady] = useState(false)
    const [animError, setAnimError] = useState(false)

    // When the mode changes AND loading completes (progress reaches 100), position the camera
    useEffect(() => {
        const bbox = getModeBbox(mode)
        if (!bbox || !sceneRef.current || progress < 100) return

        const [cx, cy, cz] = bbox.center_mm
        const maxDim = bbox.max_dim_mm
        const offset = maxDim * 1.5
        const camPos = [cx + offset, cy + offset, cz + offset]

        // Seed the prev-refs so geometry load won't trigger a redundant jump
        // (only re-animates if the actual centerOfMass differs by >1mm from precomputed)
        prevCenterRef.current = [cx, cy, cz]
        prevMaxDimRef.current = maxDim

        sceneRef.current.animateTo(camPos, [cx, cy, cz], 0.4)
    }, [mode, getModeBbox, progress])

    // Reset animReady and animError when animation is toggled off or mode changes
    useEffect(() => {
        if (!animating) { setAnimReady(false); setAnimError(false) }
    }, [animating, mode])


    const getHighlightMode = useCallback((partType: string): HighlightMode => {
        // Assembly mode takes priority
        if (assemblyActive) {
            const isVisible = visibleParts.includes(partType)
            if (!isVisible) return 'hidden'
            const isHighlighted = highlightedParts.includes(partType)
            return isHighlighted ? 'highlight' : 'ghost'
        }

        // Parameter preview: highlight affected parts, ghost others
        if (hoveredParam?.hint?.affected_parts && hoveredParam.hint.affected_parts.length > 0) {
            const isAffected = hoveredParam.hint.affected_parts.includes(partType)
            return isAffected ? 'preview' : 'ghost'
        }

        return 'normal'
    }, [assemblyActive, highlightedParts, visibleParts, hoveredParam])

    useImperativeHandle(ref, () => ({
        captureSnapshot: () => sceneRef.current?.captureSnapshot(),
        setCameraView: (view: string) => {
            sceneRef.current?.setCameraView(view)
            setActiveView(view)
        },
        animateTo: (position: number[], target?: number[] | null, duration?: number) => sceneRef.current?.animateTo?.(position, target, duration),
        getCameraState: () => sceneRef.current?.getCameraState?.(),
    }))

    const handleViewChange = useCallback((view: string) => {
        sceneRef.current?.setCameraView(view)
        setActiveView(view)
    }, [])

    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    const bgColor = isDark ? '#09090b' : '#f4f4f5'
    const isMobile = useIsMobile()
    const fov = useResponsiveFov()

    return (
        <div className="relative h-full w-full" style={{ touchAction: 'none' }}>
            <LoadingOverlay loading={loading} progress={progress} progressPhase={progressPhase} t={t} />

            {animating && mode === 'grid' && !animReady && !animError && (
                <div className="absolute inset-0 z-40 flex items-center justify-center pointer-events-none" aria-live="polite">
                    <div className="flex flex-col items-center gap-2 rounded-lg bg-background backdrop-blur-sm px-6 py-4 opacity-90">
                        <div className="text-sm font-medium">{t("anim.preparing")}</div>
                        <div className="h-1.5 w-32 overflow-hidden rounded-full bg-secondary">
                            <div className="h-full w-full bg-primary motion-safe:animate-pulse rounded-full" />
                        </div>
                    </div>
                </div>
            )}

            <button
                onClick={() => setShowAxes(s => !s)}
                className="absolute top-2 left-2 z-10 flex items-center justify-center w-11 h-11 rounded bg-background/70 border border-border text-xs font-bold hover:bg-background/90 backdrop-blur-sm"
                title={showAxes ? t("viewer.hide_axes") : t("viewer.show_axes")}
                aria-pressed={showAxes}
            >
                {showAxes ? "⊞" : "⊟"}
            </button>

            <button
                onClick={() => setOrthoCamera?.(v => !v)}
                className="absolute top-2 left-14 z-10 flex items-center justify-center w-11 h-11 rounded bg-background/70 border border-border text-xs font-bold hover:bg-background/90 backdrop-blur-sm"
                title={orthoCamera ? t("viewer.ortho_on") : t("viewer.ortho_off")}
                aria-pressed={orthoCamera}
                data-testid="ortho-toggle"
            >
                {orthoCamera ? "⬜" : "▣"}
            </button>

            {mode === 'grid' && (
                <button
                    data-testid="animation-toggle"
                    onClick={() => setAnimating(a => !a)}
                    className="absolute top-16 left-2 z-10 flex items-center justify-center w-11 h-11 rounded bg-background/70 border border-border text-lg hover:bg-background/90 backdrop-blur-sm"
                    title={animating ? t("viewer.pause_anim") : t("viewer.play_anim")}
                >
                    {animating ? "⏸" : "▶"}
                </button>
            )}

            {/* Camera view controls — compact dropdown on mobile, button grid on desktop */}
            <div className="absolute top-2 right-2 z-10">
                {/* Mobile: compact select dropdown */}
                <select
                    value={activeView}
                    onChange={(e) => handleViewChange(e.target.value)}
                    className="sm:hidden min-h-[44px] px-2 py-1 text-xs font-medium rounded bg-background/70 border border-border backdrop-blur-sm appearance-none cursor-pointer"
                    aria-label="Camera view"
                >
                    {cameraViews.map(view => (
                        <option key={view.id} value={view.id}>
                            {getLabel(view, 'label', language)}
                        </option>
                    ))}
                </select>

                {/* Desktop: button grid */}
                <div className="hidden sm:flex flex-wrap gap-1 rounded bg-background/70 border border-border p-0.5 backdrop-blur-sm max-w-[calc(100vw-5rem)]">
                    {cameraViews.map(view => (
                        <button
                            key={view.id}
                            onClick={() => handleViewChange(view.id)}
                            className={`px-2 py-1 min-h-[44px] min-w-[44px] text-xs rounded font-medium transition-colors ${activeView === view.id
                                ? 'bg-primary text-primary-foreground'
                                : 'hover:bg-muted text-muted-foreground'
                                }`}
                        >
                            {getLabel(view, 'label', language)}
                        </button>
                    ))}
                </div>
            </div>

            <ErrorBoundary t={t}>
                <Canvas shadows className="h-full w-full" camera={{ position: initialCameraPos, fov, up: SCENE_UP_VECTOR }} gl={{ preserveDrawingBuffer: true, localClippingEnabled: clippingEnabled }}>
                    <color attach="background" args={[bgColor]} />
                    <SceneController ref={sceneRef} cameraViews={cameraViews} />

                    {orthoCamera && (
                        <OrthographicCamera makeDefault position={initialCameraPos} zoom={50} up={SCENE_UP_VECTOR} />
                    )}

                    <Environment preset={environmentPreset as 'city' | 'sunset' | 'dawn' | 'night' | 'warehouse' | 'forest' | 'apartment' | 'studio' | 'lobby' | 'park'} />
                    <ambientLight intensity={0.3 * lightIntensity} />
                    <pointLight position={[10, 10, 10]} intensity={0.5 * lightIntensity} />

                    {/* @ts-expect-error target accepts number[] at runtime */}
                    <OrbitControls makeDefault up={SCENE_UP_VECTOR} minDistance={ORBIT_MIN_DISTANCE_MM} maxDistance={ORBIT_MAX_DISTANCE_MM} target={centerOfMass} />
                    <Grid
                        infiniteGrid
                        sectionSize={unit === 'in' ? 25.4 : 10}
                        sectionThickness={1.5}
                        sectionColor={isDark ? '#4b5563' : '#9ca3af'}
                        cellSize={unit === 'in' ? 2.54 : 1}
                        cellThickness={0.8}
                        cellColor={isDark ? '#4b5563' : '#cbd5e1'}
                        fadeDistance={500}
                        fadeStrength={1.5}
                        rotation={[Math.PI / 2, 0, 0]}
                    />
                    <GizmoHelper alignment="bottom-left" margin={isMobile ? [40, 40] : [60, 60]}>
                        <GizmoViewport axisColors={axisColors} labelColor="white" />
                    </GizmoHelper>

                    {showAxes && <NumberedAxes axisColors={axisColors} />}

                    {clippingEnabled && (
                        <ClippingPlane axis={clippingAxis} position={clippingPosition} bbox={sceneBox} />
                    )}

                    {measureMode && (
                        <MeasureTool active={measureMode} onMeasure={onMeasure} measurements={measurements} formatDimension={formatDimension ?? undefined} />
                    )}

                    {thicknessData && thicknessData.points?.length > 0 && (
                        <ThicknessOverlay points={thicknessData.points} thicknesses={thicknessData.thicknesses} />
                    )}

                    {overhangData && overhangData.points?.length > 0 && (
                        <OverhangOverlay points={overhangData.points} angles={overhangData.angles} threshold={overhangData.threshold_deg} />
                    )}

                    {hoveredParam && !assemblyActive && !headDiffMode && !loading && parts.length > 0 && (
                        <ParameterPreviewOverlay
                            hoveredParam={hoveredParam}
                            sceneBox={sceneBox}
                            centerOfMass={centerOfMass}
                            cachedVariants={cachedVariants}
                        />
                    )}

                    <Suspense fallback={null}>
                        {parts.length > 0 ? (
                            <>
                                <BoundingBoxHelper boundingBox={boundingBox} box={sceneBox} formatDimension={formatDimension ?? null}>
                                    {/* 3D Git Diff Mode */}
                                    {headDiffMode ? (
                                        <group>
                                            {headParts.map((part) => (
                                                <Model
                                                    key={`head-${part.type}`}
                                                    url={part.url}
                                                    isGlb={part.isGlb}
                                                    partType={`head-${part.type}`}
                                                    color="#ef4444" // red
                                                    wireframe={false}
                                                    glass={false}
                                                    onGeometry={handleGeometry}
                                                    onGeometryRemove={handleGeometryRemove}
                                                    highlightMode="ghost"
                                                    isDark={isDark}
                                                />
                                            ))}
                                            {parts.map((part) => (
                                                <Model
                                                    key={`diff-${part.type}`}
                                                    url={part.url}
                                                    isGlb={part.isGlb}
                                                    partType={`diff-${part.type}`}
                                                    color="#22c55e" // green
                                                    wireframe={false}
                                                    glass={false}
                                                    onGeometry={handleGeometry}
                                                    onGeometryRemove={handleGeometryRemove}
                                                    highlightMode="ghost"
                                                    isDark={isDark}
                                                />
                                            ))}
                                        </group>
                                    ) : (
                                        <>
                                            {/* Structural parts (grid-only, e.g. rods/stoppers) — always visible */}
                                            <group>
                                                {/* eslint-disable-next-line react-hooks/refs -- R3F geometry ref for explode displacement */}
                                                {parts.filter(p => structuralPartIds.includes(p.type)).map((part) => {
                                                    const partDef = manifest?.parts?.find(p => p.id === part.type)
                                                    const geom = geometriesRef.current[part.type]
                                                    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- BufferGeometry structurally matches GeometryLike
                                                    const centroidVec = geom ? new Vector3(computeCentroid(geom as any).x, computeCentroid(geom as any).y, computeCentroid(geom as any).z) : null
                                                    const displacement: [number, number, number] = explodeFactor > 0 && centroidVec
                                                        ? centroidVec.sub(new Vector3(...centerOfMass)).multiplyScalar(explodeFactor).toArray() as [number, number, number]
                                                        : [0, 0, 0]
                                                    return (
                                                        <group key={part.type} position={displacement}>
                                                            <Model
                                                                url={part.url}
                                                                isGlb={part.isGlb}
                                                                partType={part.type}
                                                                color={colors[part.type] || defaultColor}
                                                                wireframe={wireframe}
                                                                glass={partDef?.glass === true}
                                                                onGeometry={handleGeometry}
                                                                onGeometryRemove={handleGeometryRemove}
                                                                highlightMode={getHighlightMode(part.type)}
                                                                isDark={isDark}
                                                            />
                                                        </group>
                                                    )
                                                })}
                                            </group>
                                            {/* Assembly parts — hidden when animated grid is active */}
                                            <group visible={!(animating && mode === 'grid' && animReady)}>
                                                {/* eslint-disable-next-line react-hooks/refs -- R3F geometry ref for explode displacement */}
                                                {parts.filter(p => !structuralPartIds.includes(p.type)).map((part) => {
                                                    const partDef = manifest?.parts?.find(p => p.id === part.type)
                                                    const geom = geometriesRef.current[part.type]
                                                    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- BufferGeometry structurally matches GeometryLike
                                                    const centroidVec = geom ? new Vector3(computeCentroid(geom as any).x, computeCentroid(geom as any).y, computeCentroid(geom as any).z) : null
                                                    const displacement: [number, number, number] = explodeFactor > 0 && centroidVec
                                                        ? centroidVec.sub(new Vector3(...centerOfMass)).multiplyScalar(explodeFactor).toArray() as [number, number, number]
                                                        : [0, 0, 0]
                                                    return (
                                                        <group key={part.type} position={displacement}>
                                                            <Model
                                                                url={part.url}
                                                                isGlb={part.isGlb}
                                                                partType={part.type}
                                                                color={colors[part.type] || defaultColor}
                                                                wireframe={wireframe}
                                                                glass={partDef?.glass === true}
                                                                onGeometry={handleGeometry}
                                                                onGeometryRemove={handleGeometryRemove}
                                                                highlightMode={getHighlightMode(part.type)}
                                                                isDark={isDark}
                                                            />
                                                        </group>
                                                    )
                                                })}
                                            </group>
                                        </>
                                    )}
                                </BoundingBoxHelper>
                                {/* Animated grid — mounted when animating, visible once ready */}
                                {animating && mode === 'grid' && (
                                    <group visible={animReady}>
                                        <AnimatedGrid
                                            params={params}
                                            colors={colors}
                                            wireframe={wireframe}
                                            onReady={() => setAnimReady(true)}
                                            onError={() => { setAnimError(true); setAnimating(false) }}
                                        />
                                    </group>
                                )}
                            </>
                        ) : null}
                    </Suspense>
                </Canvas>
            </ErrorBoundary>
        </div>
    )
})

Viewer.displayName = "Viewer"

export default Viewer
