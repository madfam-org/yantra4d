import React, { Suspense, forwardRef, useImperativeHandle } from 'react'
import { Canvas, useLoader, useThree } from '@react-three/fiber'
import { OrbitControls, Center, Grid, Environment, Edges } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'
import { useLanguage } from "../contexts/LanguageProvider" // Use translation for loading text

// Helper for API access inside Canvas context
const SceneController = forwardRef((props, ref) => {
    const { gl, camera, scene } = useThree()

    useImperativeHandle(ref, () => ({
        captureSnapshot: () => {
            // Render explicitly to ensure the buffer is fresh
            gl.render(scene, camera)
            return gl.domElement.toDataURL('image/png')
        },
        setCameraView: (view) => {
            const dist = 100
            const animDur = 0 // Immediate for now, could animate

            // Standard ThreeJS Y-up (Model is rotated to match)
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

const Model = ({ url }) => {
    const geom = useLoader(STLLoader, url)
    // Fix rotation for Z-up STL to Y-up ThreeJS
    return (
        <mesh geometry={geom} rotation={[-Math.PI / 2, 0, 0]}>
            {/* Main Material: Grey matte with slight sheen */}
            <meshStandardMaterial
                color="#e5e7eb"
                roughness={0.5}
                metalness={0.1}
            />
            {/* Edges: Dark grey for highlighting geometry topology */}
            <Edges threshold={15} color="#374151" />
        </mesh>
    )
}

const Viewer = forwardRef(({ stlUrl, loading, progress }, ref) => {
    const { t } = useLanguage()

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
                </div>
            )}

            <Canvas shadows className="h-full w-full" camera={{ position: [50, 50, 50], fov: 45 }} gl={{ preserveDrawingBuffer: true }}>
                <SceneController ref={ref} />

                {/* Lighting Setup */}
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
                    {stlUrl && (
                        <Center top>
                            <Model url={stlUrl} />
                        </Center>
                    )}
                </Suspense>
            </Canvas>
        </div>
    )
})

Viewer.displayName = "Viewer"

export default Viewer
