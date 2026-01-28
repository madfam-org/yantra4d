import React, { Suspense } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import { OrbitControls, Center, Grid, Environment, Edges } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'

const Model = ({ url }) => {
    const geom = useLoader(STLLoader, url)
    // Fix rotation for Z-up STL
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

export default function Viewer({ stlUrl }) {
    return (
        <Canvas shadows camera={{ position: [50, 50, 50], fov: 45 }}>
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
    )
}
