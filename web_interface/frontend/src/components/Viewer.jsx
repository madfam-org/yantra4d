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
                                    key={part.url}
                                    url={part.url}
                                    color={colors[part.type] || "#e5e7eb"}
                                />
                            ))}
                        </Center>
                    </Bounds>
                </Suspense>
            </Canvas>
        </div>
    )
})

Viewer.displayName = "Viewer"

export default Viewer
