import React, { Suspense, useState, useEffect, useMemo, memo, forwardRef, useImperativeHandle, useCallback } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Grid, Environment, Edges, Bounds, GizmoHelper, GizmoViewport, Html } from '@react-three/drei'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils'
import { useWorkerLoader } from '../../hooks/useWorkerLoader'
import { Box3, Box3Helper, Vector3, Color } from 'three'
import { useLanguage } from "../../contexts/LanguageProvider"
import { useTheme } from "../../contexts/ThemeProvider"
import { useManifest } from "../../contexts/ManifestProvider"
import { ErrorBoundary } from '../feedback/ErrorBoundary'
import SceneController from './SceneController'
import NumberedAxes from './NumberedAxes'
import AnimatedGrid from './AnimatedGrid'
import { computeVolumeMm3, computeBoundingBox, computeCentroid } from '../../lib/printEstimator'

const DEFAULT_AXIS_COLORS = ['#ef4444', '#22c55e', '#3b82f6']
// Grid colors will be evaluated dynamically based on theme.

/** Camera constants — kept as named values to avoid magic numbers in JSX */
const CAMERA_FOV_DEG = 45
const ORBIT_MIN_DISTANCE_MM = 0.5
const ORBIT_MAX_DISTANCE_MM = 5000  // far enough for large assemblies (mm)
const SCENE_UP_VECTOR = [0, 0, 1]   // Z-up coordinate system

const Model = ({ url, partType, color, wireframe, glass, onGeometry, onGeometryRemove, highlightMode, isDark }) => {
    const isGLTF = url?.toLowerCase().endsWith('.gltf') || url?.toLowerCase().endsWith('.glb')

    // Asynchronously loads geometries; .stl via WebWorker, .gltf natively.
    const { geometry: geom, scene: gltfScene } = useWorkerLoader(url, isGLTF)

    useEffect(() => {
        if (geom && onGeometry) onGeometry(partType, geom)
        return () => {
            if (onGeometryRemove) onGeometryRemove(partType)
        }
    }, [geom, partType, onGeometry, onGeometryRemove])

    // highlightMode: 'normal' | 'highlight' | 'ghost' | 'hidden'
    if (highlightMode === 'hidden') return null
    if (!geom) return null

    const isGhost = highlightMode === 'ghost'
    const isHighlight = highlightMode === 'highlight'
    const emissive = isHighlight ? color : '#000000'
    const emissiveIntensity = isHighlight ? 0.15 : 0

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

const LoadingOverlay = memo(function LoadingOverlay({ loading, progress, progressPhase, t }) {
    if (!loading) return null
    return (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
            <div className="text-xl font-bold">{t("loader.loading")}</div>
            <div className="mt-2 h-2 w-48 overflow-hidden rounded-full bg-secondary">
                <div
                    className="h-full bg-primary transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                />
            </div>
            <div className="mt-1 text-sm text-muted-foreground">{progress}%</div>
            {progressPhase && (
                <div className="text-sm text-muted-foreground mt-1">{progressPhase}</div>
            )}
        </div>
    )
})

const BoundingBoxHelper = ({ boundingBox, box, children }) => {
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
                            {(box.max.x - box.min.x).toFixed(1)}mm
                        </div>
                    </Html>
                    {/* Depth label (Y axis) - bottom right edge */}
                    <Html
                        position={[box.max.x, box.min.y + (box.max.y - box.min.y) / 2, box.min.z]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {(box.max.y - box.min.y).toFixed(1)}mm
                        </div>
                    </Html>
                    {/* Height label (Z axis) - back left edge */}
                    <Html
                        position={[box.min.x, box.max.y, box.min.z + (box.max.z - box.min.z) / 2]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {(box.max.z - box.min.z).toFixed(1)}mm
                        </div>
                    </Html>
                </group>
            )}
        </group>
    )
}

const Viewer = forwardRef(({ parts = [], colors, wireframe, boundingBox, loading, progress, progressPhase, animating, setAnimating, mode, params, onGeometryStats, assemblyActive, highlightedParts = [], visibleParts = [] }, ref) => {
    const geometriesRef = React.useRef({})
    const prevCenterRef = React.useRef(null)
    const prevMaxDimRef = React.useRef(null)
    const sceneRef = React.useRef()
    const [centerOfMass, setCenterOfMass] = useState([0, 0, 0])
    const [sceneBox, setSceneBox] = useState(null)

    const recalculateSceneStats = useCallback(() => {
        // Aggregate stats across all parts, and collect per-part stats for individual estimates
        let totalVolume = 0
        let weightedCenterSum = { x: 0, y: 0, z: 0 }
        let mergedBox = null
        let absoluteBox = null
        const perPartStats = {}

        for (const [partType, geom] of Object.entries(geometriesRef.current)) {
            const vol = computeVolumeMm3(geom)
            totalVolume += vol
            const centroid = computeCentroid(geom)

            weightedCenterSum.x += centroid.x * vol
            weightedCenterSum.y += centroid.y * vol
            weightedCenterSum.z += centroid.z * vol

            const bbox = computeBoundingBox(geom)

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
                absoluteBox = new Box3().copy(geom.boundingBox)
            } else {
                absoluteBox.union(geom.boundingBox)
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
            total: { volumeMm3: totalVolume, boundingBox: mergedBox },
            parts: perPartStats,
        })
    }, [onGeometryStats])

    const handleGeometry = useCallback((partType, geometry) => {
        geometriesRef.current[partType] = geometry
        // DEBUG: Check geometry bounds on load
        geometry.computeBoundingBox()
        console.log(`[Viewer] Loaded ${partType}:`, geometry.boundingBox)
        recalculateSceneStats()
    }, [recalculateSceneStats])

    const handleGeometryRemove = useCallback((partType) => {
        if (geometriesRef.current[partType]) {
            delete geometriesRef.current[partType]
            recalculateSceneStats()
        }
    }, [recalculateSceneStats])

    const { language, t } = useLanguage()
    const { theme } = useTheme()
    const { getCameraViews, getViewerConfig, getLabel, getMode, manifest } = useManifest()

    // Helper: get the precomputed initial bounding box for the current mode from the manifest
    const getModeBbox = useCallback((modeId) => {
        return manifest?.modes?.find(m => m.id === modeId)?.initial_bbox || null
    }, [manifest])

    const axisColors = manifest?.viewer?.axis_colors
        ? [manifest.viewer.axis_colors.x || DEFAULT_AXIS_COLORS[0], manifest.viewer.axis_colors.y || DEFAULT_AXIS_COLORS[1], manifest.viewer.axis_colors.z || DEFAULT_AXIS_COLORS[2]]
        : DEFAULT_AXIS_COLORS
    const cameraViews = getCameraViews()
    const viewerConfig = getViewerConfig()
    const defaultColor = viewerConfig.default_color || "#e5e7eb"
    const isoView = cameraViews.find(v => v.id === 'iso') || cameraViews[0]
    const initialCameraPos = isoView?.position || [50, 50, 50]

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

    // Reset animReady when animation is toggled off or mode changes
    useEffect(() => {
        if (!animating) setAnimReady(false) // eslint-disable-line react-hooks/set-state-in-effect
    }, [animating, mode])


    const getHighlightMode = useCallback((partType) => {
        if (!assemblyActive) return 'normal'
        const isVisible = visibleParts.includes(partType)
        if (!isVisible) return 'hidden'
        const isHighlighted = highlightedParts.includes(partType)
        return isHighlighted ? 'highlight' : 'ghost'
    }, [assemblyActive, highlightedParts, visibleParts])

    useImperativeHandle(ref, () => ({
        captureSnapshot: () => sceneRef.current?.captureSnapshot(),
        setCameraView: (view) => {
            sceneRef.current?.setCameraView(view)
            setActiveView(view)
        },
        animateTo: (position, target, duration) => sceneRef.current?.animateTo?.(position, target, duration),
        getCameraState: () => sceneRef.current?.getCameraState?.(),
    }))

    const handleViewChange = useCallback((view) => {
        sceneRef.current?.setCameraView(view)
        setActiveView(view)
    }, [])

    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    const bgColor = isDark ? '#09090b' : '#f4f4f5'

    return (
        <div className="relative h-full w-full">
            <LoadingOverlay loading={loading} progress={progress} progressPhase={progressPhase} t={t} />

            {animating && mode === 'grid' && !animReady && (
                <div className="absolute inset-0 z-40 flex items-center justify-center pointer-events-none" aria-live="polite">
                    <div className="flex flex-col items-center gap-2 rounded-lg bg-background backdrop-blur-sm px-6 py-4 opacity-90">
                        <div className="text-sm font-medium">{t("anim.preparing")}</div>
                        <div className="h-1.5 w-32 overflow-hidden rounded-full bg-secondary">
                            <div className="h-full w-full bg-primary animate-pulse rounded-full" />
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

            <div className="absolute top-2 right-2 z-10 flex gap-1 rounded bg-background/70 border border-border p-0.5 backdrop-blur-sm">
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

            <ErrorBoundary t={t}>
                <Canvas shadows className="h-full w-full" camera={{ position: initialCameraPos, fov: CAMERA_FOV_DEG, up: SCENE_UP_VECTOR }} gl={{ preserveDrawingBuffer: true }}>
                    <color attach="background" args={[bgColor]} />
                    <SceneController ref={sceneRef} cameraViews={cameraViews} />

                    <Environment preset="city" />
                    <ambientLight intensity={0.3} />
                    <pointLight position={[10, 10, 10]} intensity={0.5} />

                    <OrbitControls makeDefault up={SCENE_UP_VECTOR} minDistance={ORBIT_MIN_DISTANCE_MM} maxDistance={ORBIT_MAX_DISTANCE_MM} target={centerOfMass} />
                    <Grid
                        infiniteGrid
                        sectionSize={10}
                        sectionThickness={1.5}
                        sectionColor={isDark ? '#4b5563' : '#9ca3af'}
                        cellSize={1}
                        cellThickness={0.8}
                        cellColor={isDark ? '#4b5563' : '#cbd5e1'}
                        fadeDistance={500}
                        fadeStrength={1.5}
                        rotation={[Math.PI / 2, 0, 0]}
                    />
                    <GizmoHelper alignment="bottom-left" margin={[60, 60]}>
                        <GizmoViewport axisColors={axisColors} labelColor="white" />
                    </GizmoHelper>

                    {showAxes && <NumberedAxes axisColors={axisColors} />}

                    <Suspense fallback={null}>
                        {parts.length > 0 ? (
                            <>
                                <BoundingBoxHelper boundingBox={boundingBox} box={sceneBox}>
                                    {/* Structural parts (grid-only, e.g. rods/stoppers) — always visible */}
                                    <group>
                                        {parts.filter(p => structuralPartIds.includes(p.type)).map((part) => {
                                            const partDef = manifest?.parts?.find(p => p.id === part.type)
                                            return (
                                                <Model
                                                    key={part.type}
                                                    url={part.url}
                                                    partType={part.type}
                                                    color={colors[part.type] || defaultColor}
                                                    wireframe={wireframe}
                                                    glass={partDef?.glass === true}
                                                    onGeometry={handleGeometry}
                                                    onGeometryRemove={handleGeometryRemove}
                                                    highlightMode={getHighlightMode(part.type)}
                                                    isDark={isDark}
                                                />
                                            )
                                        })}
                                    </group>
                                    {/* Assembly parts — hidden when animated grid is active */}
                                    <group visible={!(animating && mode === 'grid' && animReady)}>
                                        {parts.filter(p => !structuralPartIds.includes(p.type)).map((part) => {
                                            const partDef = manifest?.parts?.find(p => p.id === part.type)
                                            return (
                                                <Model
                                                    key={part.type}
                                                    url={part.url}
                                                    partType={part.type}
                                                    color={colors[part.type] || defaultColor}
                                                    wireframe={wireframe}
                                                    glass={partDef?.glass === true}
                                                    onGeometry={handleGeometry}
                                                    onGeometryRemove={handleGeometryRemove}
                                                    highlightMode={getHighlightMode(part.type)}
                                                    isDark={isDark}
                                                />
                                            )
                                        })}
                                    </group>
                                </BoundingBoxHelper>
                                {/* Animated grid — mounted when animating, visible once ready */}
                                {animating && mode === 'grid' && (
                                    <group visible={animReady}>
                                        <AnimatedGrid
                                            params={params}
                                            colors={colors}
                                            wireframe={wireframe}
                                            onReady={() => setAnimReady(true)}
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
