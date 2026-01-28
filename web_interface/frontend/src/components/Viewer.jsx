import React, { Suspense } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import { OrbitControls, Stage, Center, Grid } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'

const Model = ({ url }) => {
    const geom = useLoader(STLLoader, url)
    // Center geometry? 
    // <Center> component handles it.

    return (
        <mesh geometry={geom} rotation={[-Math.PI / 2, 0, 0]}>
            <meshStandardMaterial color="#6366f1" />
        </mesh>
    )
}

export default function Viewer({ stlUrl }) {
    return (
        <Canvas shadows camera={{ position: [50, 50, 50], fov: 50 }}>
            {/* Lights */}
            <ambientLight intensity={0.5} />
            <pointLight position={[100, 100, 100]} intensity={1} />

            <OrbitControls makeDefault />
            <Grid infiniteGrid sectionColor="#555" cellColor="#333" args={[10, 10]} />

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
