import React, { Suspense, forwardRef, useImperativeHandle } from 'react'
import { Canvas, useLoader, useThree } from '@react-three/fiber'
import { OrbitControls, Center, Grid, Environment, Edges, Bounds } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'
import { useLanguage } from "../contexts/LanguageProvider"
import { useTheme } from "../contexts/ThemeProvider"

const SceneController = forwardRef((props, ref) => {
    const { gl, camera, scene } = useThree()

    useImperativeHandle(ref, () => ({
        captureSnapshot: () => {
            gl.render(scene, camera)
            return gl.domElement.toDataURL('image/png')
        },
        setCameraView: (view) => {
            const dist = 100
            switch (view) {
                case 'iso':
                    camera.position.set(50, 50, 50)
                    break
                case 'top':
                    camera.position.set(0, dist, 0)
                    break
                case 'front':
                    camera.position.set(0, 0, dist)
                    break
                case 'right':
                    camera.position.set(dist, 0, 0)
                    break
            }
            camera.lookAt(0, 0, 0)
            camera.updateProjectionMatrix()
        }
    }))
    return null
})

SceneController.displayName = "SceneController"

const Model = ({ url, color }) => {
    const geom = useLoader(STLLoader, url)
    return (
        <mesh geometry={geom} rotation={[-Math.PI / 2, 0, 0]}>
            <meshStandardMaterial
                color={color || "#e5e7eb"}
                roughness={0.5}
                metalness={0.1}
            />
            <Edges threshold={15} color="#374151" />
        </mesh>
    )
}

class ViewerErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = { hasError: false }
    }
    static getDerivedStateFromError() {
        return { hasError: true }
    }
    componentDidCatch(error, info) {
        console.error('Viewer error:', error, info)
    }
    render() {
        if (this.state.hasError) {
            return (
                <div className="flex items-center justify-center h-full bg-muted text-muted-foreground">
                    <div className="text-center p-8">
                        <p className="text-lg font-semibold">3D viewer failed to load</p>
                        <p className="text-sm mt-2">Try refreshing the page</p>
                        <button
                            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded"
                            onClick={() => this.setState({ hasError: false })}
                        >
                            Retry
                        </button>
                    </div>
                </div>
            )
        }
        return this.props.children
    }
}

const Viewer = forwardRef(({ parts = [], colors, loading, progress, progressPhase }, ref) => {
    const { t } = useLanguage()
    const { theme } = useTheme()

    // Resolve effective theme for canvas background
    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    const bgColor = isDark ? '#09090b' : '#f4f4f5'

    return (
        <div className="relative h-full w-full">
            {/* Loading Overlay */}
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

            <ViewerErrorBoundary>
            <Canvas shadows className="h-full w-full" camera={{ position: [50, 50, 50], fov: 45 }} gl={{ preserveDrawingBuffer: true }}>
                <color attach="background" args={[bgColor]} />
                <SceneController ref={ref} />

                <Environment preset="city" />
                <ambientLight intensity={0.3} />
                <pointLight position={[10, 10, 10]} intensity={0.5} />

                <OrbitControls makeDefault />
                <Grid
                    infiniteGrid
                    sectionColor="#4b5563"
                    cellColor="#374151"
                    fadeDistance={500}
                    args={[10, 10]}
                />

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
            </ViewerErrorBoundary>
        </div>
    )
})

Viewer.displayName = "Viewer"

export default Viewer
