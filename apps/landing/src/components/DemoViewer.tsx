import { Canvas } from '@react-three/fiber';
import { OrbitControls, Center, useProgress, Html } from '@react-three/drei';
import { Suspense, useState, useEffect } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

type Demo = {
  id: string;
  label: string;
  url: string;
  camera: [number, number, number];
  color?: string;
};

const DEMOS: Demo[] = [
  { id: 'tablaco', label: 'Tablaco', url: '/tablaco-assembly.stl', camera: [60, 60, 60] },
  { id: 'portacosas', label: 'Portacosas', url: '/demo-portacosas.stl', camera: [250, 200, 150] },
  { id: 'gridfinity', label: 'Gridfinity', url: '/gridfinity-cup.stl', camera: [100, 80, 60], color: '#4a90d9' },
];

function Loader({ text = 'loaded' }: { text?: string }) {
  const { progress } = useProgress();
  return <Html center><span style={{ color: '#888' }}>{progress.toFixed(0)}% {text}</span></Html>;
}

function Model({ url, color = '#94a3b8' }: { url: string; color?: string }) {
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
        <meshStandardMaterial color={color} roughness={0.4} metalness={0.1} />
      </mesh>
    </Center>
  );
}

export default function DemoViewer({ loadingText = 'loaded' }: { loadingText?: string }) {
  const [activeDemo, setActiveDemo] = useState(DEMOS[0]);

  return (
    <div>
      <div className="flex gap-2 justify-center p-3 border-b border-border">
        {DEMOS.map(d => (
          <button
            key={d.id}
            onClick={() => setActiveDemo(d)}
            className={`px-4 py-1.5 text-sm rounded-md border transition-colors ${
              activeDemo.id === d.id
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-border hover:text-foreground'
            }`}
          >
            {d.label}
          </button>
        ))}
      </div>
      <div className="h-[400px] w-full sm:h-[500px]">
        <Canvas camera={{ position: activeDemo.camera, fov: 45, up: [0, 0, 1] }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[10, 10, 10]} intensity={0.8} />
          <Suspense fallback={<Loader text={loadingText} />}>
            <Model url={activeDemo.url} color={activeDemo.color} />
          </Suspense>
          <OrbitControls enableDamping dampingFactor={0.1} />
        </Canvas>
      </div>
    </div>
  );
}
