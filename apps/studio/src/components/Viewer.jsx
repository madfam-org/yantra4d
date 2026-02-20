import React, { Suspense, useState, useEffect, useMemo, memo, forwardRef, useImperativeHandle, useCallback, useRef } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import { OrbitControls, Grid, Environment, Edges, Bounds, GizmoHelper, GizmoViewport } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'
import { BoxHelper } from 'three'
import { useLanguage } from "../contexts/LanguageProvider"
import { useTheme } from "../contexts/ThemeProvider"
import { useManifest } from "../contexts/ManifestProvider"
import { ErrorBoundary } from './feedback/ErrorBoundary'
import SceneController from './viewer/SceneController'
import NumberedAxes from './viewer/NumberedAxes'
import AnimatedGrid from './viewer/AnimatedGrid'
import { computeVolumeMm3, computeBoundingBox, computeCentroid } from '../lib/printEstimator'

const DEFAULT_AXIS_COLORS = ['#ef4444', '#22c55e', '#3b82f6']
const GRID_SECTION_COLOR = '#4b5563'
const GRID_CELL_COLOR = '#374151'

const Model = ({ url, color, wireframe, onGeometry, highlightMode }) => {
    const geom = useLoader(STLLoader, url)
    useEffect(() => {
        if (geom && onGeometry) onGeometry(geom)
    }, [geom, onGeometry])

    // highlightMode: 'normal' | 'highlight' | 'ghost' | 'hidden'
    if (highlightMode === 'hidden') return null

    const isGhost = highlightMode === 'ghost'
    const isHighlight = highlightMode === 'highlight'
    const opacity = wireframe ? 0.08 : isGhost ? 0.15 : 1
    const emissive = isHighlight ? color : '#000000'
    const emissiveIntensity = isHighlight ? 0.15 : 0

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
            {!isGhost && <Edges threshold={15} color="#374151" />}
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

import { Box3, Vector3 } from 'three'
import { Html } from '@react-three/drei'

const BoundingBoxHelper = ({ boundingBox, children }) => {
    const groupRef = useRef()
    const [box, setBox] = useState(null)
    const [dims, setDims] = useState(null)

    useEffect(() => {
        if (!boundingBox || !groupRef.current) {
            setBox(null) // eslint-disable-line react-hooks/set-state-in-effect
            setDims(null)  
            return
        }

        // Delay slightly to let models mount and position
        const timer = setTimeout(() => {
            if (groupRef.current) {
                const b = new Box3().setFromObject(groupRef.current)
                if (!b.isEmpty()) {
                    setBox(b)
                    const size = new Vector3()
                    b.getSize(size)
                    setDims({
                        w: size.x.toFixed(1),
                        h: size.z.toFixed(1), // Z up
                        d: size.y.toFixed(1)
                    })
                }
            }
        }, 100)
        return () => clearTimeout(timer)
    }, [boundingBox, children])

    return (
        <group ref={groupRef}>
            {children}
            {box && dims && (
                <>
                    <box3Helper args={[box, 0x06b6d4]} />
                    {/* Width label (X axis) - bottom front edge */}
                    <Html
                        position={[box.min.x + (box.max.x - box.min.x) / 2, box.min.y, box.min.z]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {dims.w}mm
                        </div>
                    </Html>
                    {/* Depth label (Y axis) - bottom right edge */}
                    <Html
                        position={[box.max.x, box.min.y + (box.max.y - box.min.y) / 2, box.min.z]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {dims.d}mm
                        </div>
                    </Html>
                    {/* Height label (Z axis) - back left edge */}
                    <Html
                        position={[box.min.x, box.max.y, box.min.z + (box.max.z - box.min.z) / 2]}
                        center
                        className="pointer-events-none select-none"
                    >
                        <div className="bg-background/80 text-cyan-500 text-xs px-1 py-0.5 rounded shadow-sm border border-cyan-500/30 backdrop-blur-sm whitespace-nowrap">
                            {dims.h}mm
                        </div>
                    </Html>
                </>
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

    const handleGeometry = useCallback((partType, geometry) => {
        geometriesRef.current[partType] = geometry
        // DEBUG: Check geometry bounds on load
        geometry.computeBoundingBox()
        console.log(`[Viewer] Loaded ${partType}:`, geometry.boundingBox)

        // Aggregate stats across all parts
        let totalVolume = 0
        let weightedCenterSum = { x: 0, y: 0, z: 0 }
        let mergedBox = null
        for (const geom of Object.values(geometriesRef.current)) {
            const vol = computeVolumeMm3(geom)
            totalVolume += vol
            const centroid = computeCentroid(geom)

            weightedCenterSum.x += centroid.x * vol
            weightedCenterSum.y += centroid.y * vol
            weightedCenterSum.z += centroid.z * vol

            const bbox = computeBoundingBox(geom)
            if (!mergedBox) {
                mergedBox = bbox
            } else {
                mergedBox = {
                    width: Math.max(mergedBox.width, bbox.width),
                    depth: Math.max(mergedBox.depth, bbox.depth),
                    height: Math.max(mergedBox.height, bbox.height),
                }
            }
        }

        if (totalVolume > 0) {
            const newCenter = [
                weightedCenterSum.x / totalVolume,
                weightedCenterSum.y / totalVolume,
                weightedCenterSum.z / totalVolume
            ]
            setCenterOfMass(newCenter)
            console.log('[Viewer] New CenterOfMass:', newCenter)

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
        }

        onGeometryStats?.({ volumeMm3: totalVolume, boundingBox: mergedBox })
    }, [onGeometryStats])

    const { language, t } = useLanguage()
    const { theme } = useTheme()
    const { getCameraViews, getViewerConfig, getLabel, getMode, manifest } = useManifest()
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
                <Canvas shadows className="h-full w-full" camera={{ position: initialCameraPos, fov: 45, up: [0, 0, 1] }} gl={{ preserveDrawingBuffer: true }}>
                    <color attach="background" args={[bgColor]} />
                    <SceneController ref={sceneRef} cameraViews={cameraViews} />

                    <Environment preset="city" />
                    <ambientLight intensity={0.3} />
                    <pointLight position={[10, 10, 10]} intensity={0.5} />

                    <OrbitControls makeDefault up={[0, 0, 1]} minDistance={0.5} maxDistance={5000} target={centerOfMass} />
                    <Grid
                        infiniteGrid
                        sectionColor={GRID_SECTION_COLOR}
                        cellColor={GRID_CELL_COLOR}
                        fadeDistance={500}
                        args={[10, 10]}
                        rotation={[Math.PI / 2, 0, 0]}
                    />
                    <GizmoHelper alignment="bottom-left" margin={[60, 60]}>
                        <GizmoViewport axisColors={axisColors} labelColor="white" />
                    </GizmoHelper>

                    {showAxes && <NumberedAxes axisColors={axisColors} />}

                    <Suspense fallback={null}>
                        {parts.length > 0 ? (
                            <>
                                <BoundingBoxHelper boundingBox={boundingBox}>
                                    {/* Structural parts (grid-only, e.g. rods/stoppers) — always visible */}
                                    <group>
                                        {parts.filter(p => structuralPartIds.includes(p.type)).map((part) => (
                                            <Model
                                                key={part.type}
                                                url={part.url}
                                                color={colors[part.type] || defaultColor}
                                                wireframe={wireframe}
                                                onGeometry={(geom) => handleGeometry(part.type, geom)}
                                                highlightMode={getHighlightMode(part.type)}
                                            />
                                        ))}
                                    </group>
                                    {/* Assembly parts — hidden when animated grid is active */}
                                    <group visible={!(animating && mode === 'grid' && animReady)}>
                                        {parts.filter(p => !structuralPartIds.includes(p.type)).map((part) => (
                                            <Model
                                                key={part.type}
                                                url={part.url}
                                                color={colors[part.type] || defaultColor}
                                                wireframe={wireframe}
                                                onGeometry={(geom) => handleGeometry(part.type, geom)}
                                                highlightMode={getHighlightMode(part.type)}
                                            />
                                        ))}
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
