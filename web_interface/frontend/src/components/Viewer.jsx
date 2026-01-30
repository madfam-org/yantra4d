import React, { Suspense, useState, forwardRef, useImperativeHandle, useCallback } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import { OrbitControls, Center, Grid, Environment, Edges, Bounds, GizmoHelper, GizmoViewport } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'
import { useLanguage } from "../contexts/LanguageProvider"
import { useTheme } from "../contexts/ThemeProvider"
import { ErrorBoundary } from './ErrorBoundary'
import SceneController from './viewer/SceneController'
import NumberedAxes from './viewer/NumberedAxes'

const VIEWS = ['iso', 'top', 'front', 'right']

const Model = ({ url, color }) => {
    const geom = useLoader(STLLoader, url)
    return (
        <mesh geometry={geom}>
            <meshStandardMaterial
                color={color || "#e5e7eb"}
                roughness={0.5}
                metalness={0.1}
            />
            <Edges threshold={15} color="#374151" />
        </mesh>
    )
}

const Viewer = forwardRef(({ parts = [], colors, loading, progress, progressPhase }, ref) => {
    const { t } = useLanguage()
    const { theme } = useTheme()
    const [showAxes, setShowAxes] = useState(true)
    const [activeView, setActiveView] = useState('iso')
    const sceneRef = React.useRef()

    useImperativeHandle(ref, () => ({
        captureSnapshot: () => sceneRef.current?.captureSnapshot(),
        setCameraView: (view) => {
            sceneRef.current?.setCameraView(view)
            setActiveView(view)
        }
    }))

    const handleViewChange = useCallback((view) => {
        sceneRef.current?.setCameraView(view)
        setActiveView(view)
    }, [])

    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    const bgColor = isDark ? '#09090b' : '#f4f4f5'

    return (
        <div className="relative h-full w-full">
            {loading && (
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
            )}

            <button
                onClick={() => setShowAxes(s => !s)}
                className="absolute top-2 left-2 z-10 flex items-center justify-center w-8 h-8 rounded bg-background/70 border border-border text-xs font-bold hover:bg-background/90 backdrop-blur-sm"
                title={showAxes ? "Hide axes" : "Show axes"}
            >
                {showAxes ? "⊞" : "⊟"}
            </button>

            <div className="absolute top-2 right-2 z-10 flex gap-1 rounded bg-background/70 border border-border p-0.5 backdrop-blur-sm">
                {VIEWS.map(view => (
                    <button
                        key={view}
                        onClick={() => handleViewChange(view)}
                        className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
                            activeView === view
                                ? 'bg-primary text-primary-foreground'
                                : 'hover:bg-muted text-muted-foreground'
                        }`}
                    >
                        {view.charAt(0).toUpperCase() + view.slice(1)}
                    </button>
                ))}
            </div>

            <ErrorBoundary>
            <Canvas shadows className="h-full w-full" camera={{ position: [50, 50, 50], fov: 45, up: [0, 0, 1] }} gl={{ preserveDrawingBuffer: true }}>
                <color attach="background" args={[bgColor]} />
                <SceneController ref={sceneRef} />

                <Environment preset="city" />
                <ambientLight intensity={0.3} />
                <pointLight position={[10, 10, 10]} intensity={0.5} />

                <OrbitControls makeDefault up={[0, 0, 1]} />
                <Grid
                    infiniteGrid
                    sectionColor="#4b5563"
                    cellColor="#374151"
                    fadeDistance={500}
                    args={[10, 10]}
                    rotation={[Math.PI / 2, 0, 0]}
                />
                <GizmoHelper alignment="bottom-left" margin={[60, 60]}>
                    <GizmoViewport axisColors={['#ef4444', '#22c55e', '#3b82f6']} labelColor="white" />
                </GizmoHelper>

                {showAxes && <NumberedAxes />}

                <Suspense fallback={null}>
                    <Bounds fit clip observe margin={1.2}>
                        <Center top>
                            {parts.map((part) => (
                                <Model
                                    key={part.type}
                                    url={part.url}
                                    color={colors[part.type] || "#e5e7eb"}
                                />
                            ))}
                        </Center>
                    </Bounds>
                </Suspense>
            </Canvas>
            </ErrorBoundary>
        </div>
    )
})

Viewer.displayName = "Viewer"

export default Viewer
