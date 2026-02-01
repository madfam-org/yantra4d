import { Canvas } from '@react-three/fiber';
import { OrbitControls, Center, useProgress, Html } from '@react-three/drei';
import { Suspense, useState, useEffect } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

function Loader() {
  const { progress } = useProgress();
  return <Html center><span style={{ color: '#888' }}>{progress.toFixed(0)}% loaded</span></Html>;
}

function Model({ url }: { url: string }) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    const loader = new STLLoader();
    loader.load(url, (geo) => {
      geo.computeVertexNormals();
      setGeometry(geo);
    });
  }, [url]);

  if (!geometry) return null;

  return (
    <Center>
      <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]}>
        <meshStandardMaterial color="#94a3b8" roughness={0.4} metalness={0.1} />
      </mesh>
    </Center>
  );
}

export default function DemoViewer() {
  return (
    <div className="h-[400px] w-full sm:h-[500px]">
      <Canvas camera={{ position: [60, 60, 60], fov: 45, up: [0, 0, 1] }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 10]} intensity={0.8} />
        <Suspense fallback={<Loader />}>
          <Model url="/tablaco-assembly.stl" />
        </Suspense>
        <OrbitControls enableDamping dampingFactor={0.1} />
      </Canvas>
    </div>
  );
}
