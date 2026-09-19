import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { ScrollControls, useScroll, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { GLBErrorBoundary } from './GLBErrorBoundary';
import type { GalleryItem } from '../lib/gallery';
import type { GalleryLabels } from './CommonsGallery';
import { modelUrl, type ModelsManifest } from '../lib/models-manifest';
import type { Tier } from '../lib/tier';

/**
 * The 3D stage of the gallery: a ring of live meshes. This module — and the
 * `vendor-three` chunk it pulls in — is imported lazily by `CommonsGallery`
 * only on the lite/full tiers, so nothing here runs for a still-tier visitor.
 *
 * Meshes come from `public/models` via the manifest: meshopt-compressed LOD1
 * files when the pipeline has produced them (`GLTFLoader.setMeshoptDecoder`),
 * the legacy uncompressed `<slug>.glb` otherwise. The render loop pauses while
 * the stage is off-screen or the tab is hidden: a carousel nobody is looking
 * at should cost nothing.
 */

const MoveHorizontalIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    <polyline points="18 8 22 12 18 16"></polyline>
    <polyline points="6 8 2 12 6 16"></polyline>
    <line x1="2" y1="12" x2="22" y2="12"></line>
  </svg>
);
const ChevronLeftIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    <polyline points="15 18 9 12 15 6"></polyline>
  </svg>
);
const ChevronRightIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    <polyline points="9 18 15 12 9 6"></polyline>
  </svg>
);

const withMeshopt = (loader: GLTFLoader) => {
  loader.setMeshoptDecoder(MeshoptDecoder);
};

function LoadedModel({ url }: { url: string }) {
  const gltf = useLoader(GLTFLoader as any, url, withMeshopt as any);
  const scene = useMemo(() => {
    if (!gltf) return null;
    const root = gltf.scene.clone(true);
    const box = new THREE.Box3().setFromObject(root);
    const center = new THREE.Vector3();
    box.getCenter(center);
    const size = new THREE.Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = maxDim > 0 ? 2.5 / maxDim : 1;
    // The pipeline's LOD files carry POSITION only (no normals, no materials —
    // the page owns the look). GLTFLoader flat-shades its own material for such
    // primitives; since we replace it, we must say so too, or the lighting is
    // wrong. See docs/guides/landing-models-pipeline.md.
    const material = new THREE.MeshStandardMaterial({ color: '#cbd5e1', roughness: 0.4, metalness: 0.1, flatShading: true });
    root.traverse((child: any) => {
      if (child.isMesh) child.material = material;
    });
    return { root, scale, center };
  }, [gltf]);
  if (!scene) return null;
  const { root, scale, center } = scene;
  return (
    <group scale={scale} position={[-center.x * scale, -center.y * scale, -center.z * scale]}>
      <primitive object={root} />
    </group>
  );
}

function WireframeFallback() {
  return (
    <mesh>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="gray" wireframe />
    </mesh>
  );
}

function LiveModel({ url }: { url: string | null }) {
  if (!url) return <WireframeFallback />;
  return (
    <GLBErrorBoundary fallback={<WireframeFallback />}>
      <Suspense fallback={<WireframeFallback />}>
        <LoadedModel url={url} />
      </Suspense>
    </GLBErrorBoundary>
  );
}

function CarouselItem({ url, index, total, radius }: { url: string | null; index: number; total: number; radius: number }) {
  const groupRef = useRef<THREE.Group>(null as any);
  const [isActive, setIsActive] = useState(false);
  const angle = (index / total) * Math.PI * 2;
  const x = Math.sin(angle) * radius;
  const z = Math.cos(angle) * radius;
  const worldPos = useMemo(() => new THREE.Vector3(), []);
  const targetScale = useMemo(() => new THREE.Vector3(), []);

  useFrame(() => {
    if (!groupRef.current) return;
    groupRef.current.getWorldPosition(worldPos);
    const dist = Math.sqrt(worldPos.x * worldPos.x + worldPos.z * worldPos.z);
    const active = dist < radius * 0.5;
    if (active !== isActive) setIsActive(active);
    if (active) groupRef.current.rotation.y += 0.005;
    else groupRef.current.rotation.y += (angle - groupRef.current.rotation.y) * 0.1;
    const s = active ? 1.2 : 0.6;
    groupRef.current.scale.lerp(targetScale.set(s, s, s), 0.1);
  });

  return (
    <group ref={groupRef as any} position={[x, 0, z]} rotation={[0, angle, 0]}>
      <LiveModel url={url} />
    </group>
  );
}

function CarouselTrack({ urls, onActiveChange }: { urls: Array<string | null>; onActiveChange: (idx: number) => void }) {
  const scroll = useScroll();
  const numItems = urls.length;
  const gap = 3.5;
  const radius = Math.max(4, (numItems * gap) / (2 * Math.PI));
  const trackRef = useRef<THREE.Group>(null as any);
  const lastOffset = useRef(0);
  const revolutions = useRef(0);

  useFrame((_state, delta) => {
    const offset = scroll.offset;
    if (offset < 0.2 && lastOffset.current > 0.8) revolutions.current += 1;
    else if (offset > 0.8 && lastOffset.current < 0.2) revolutions.current -= 1;
    lastOffset.current = offset;
    const rawIndex = (offset + revolutions.current) * numItems;
    let activeIdx = Math.round(rawIndex) % numItems;
    if (activeIdx < 0) activeIdx += numItems;
    onActiveChange(activeIdx);
    if (trackRef.current) {
      const targetRotation = -rawIndex * ((Math.PI * 2) / numItems);
      trackRef.current.rotation.y += (targetRotation - trackRef.current.rotation.y) * 5 * delta;
    }
  });

  return (
    <group ref={trackRef as any} position={[0, -0.5, -radius]}>
      {urls.map((url, i) => (
        <CarouselItem key={`${i}:${url ?? 'none'}`} url={url} index={i} total={numItems} radius={radius} />
      ))}
    </group>
  );
}

function CarouselUIOverlay({ project, index, total, labels, studioUrl }: { project: GalleryItem; index: number; total: number; labels: GalleryLabels; studioUrl: string }) {
  return (
    <div className="absolute inset-0 z-10 pointer-events-none flex flex-col justify-between p-4 sm:p-8">
      <div className="flex justify-between items-start pointer-events-auto">
        <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-full border border-border shadow-sm text-foreground">
          <span className="text-sm font-medium" data-testid="stage-counter">
            {index + 1} <span className="text-muted-foreground mr-1">/</span> {total}
          </span>
        </div>
      </div>
      <div className="w-full max-w-[calc(100%-2rem)] sm:max-w-md pointer-events-auto mt-auto">
        <div className="bg-card/90 backdrop-blur-xl border border-border/50 shadow-2xl rounded-xl overflow-hidden flex flex-col">
          <div className="p-3 sm:p-6 pb-2 sm:pb-3">
            <h3 className="text-lg sm:text-2xl font-bold tracking-tight text-card-foreground truncate mb-2">{project.name}</h3>
            <p className="text-base text-muted-foreground line-clamp-1 sm:line-clamp-2 leading-relaxed">{project.description}</p>
          </div>
          <div className="p-3 sm:p-6 pt-0 pb-3 sm:pb-4 flex flex-col items-start gap-4">
            <div className="flex flex-wrap gap-2">
              {project.isHyperobject && (
                <span className="px-2.5 py-1 rounded border border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium tracking-wide uppercase">{labels.hyperobject}</span>
              )}
              <span className="px-2 py-1 rounded bg-muted text-muted-foreground text-xs font-medium">{labels.categories[project.category] ?? project.category}</span>
            </div>
            <div className="w-full border-t border-border/40 pt-4 flex flex-row items-center justify-between">
              <p className="text-xs text-muted-foreground italic hidden sm:block">{labels.live}</p>
              <a
                href={`${studioUrl}/project/${project.slug}`}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium text-sm px-4 py-2 rounded-md transition-colors flex items-center justify-center gap-2 group min-h-[44px]"
              >
                {labels.openStudio}
                <span className="transform group-hover:translate-x-1 transition-transform" aria-hidden="true">→</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Render only while someone can see it: on-screen and in a visible tab. */
function useShouldRender(ref: React.RefObject<HTMLElement | null>): boolean {
  const [inView, setInView] = useState(true);
  const [visible, setVisible] = useState(() => (typeof document === 'undefined' ? true : document.visibilityState !== 'hidden'));
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.05 });
    io.observe(el);
    return () => io.disconnect();
  }, [ref]);
  useEffect(() => {
    const onVis = () => setVisible(document.visibilityState !== 'hidden');
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, []);
  return inView && visible;
}

export interface ProjectCarousel3DProps {
  lang?: string;
  tier: Tier;
  labels: GalleryLabels;
  projects: GalleryItem[];
  manifest: ModelsManifest | null;
  note?: string;
  studioUrl: string;
}

export default function ProjectCarousel3D({ tier, labels, projects, manifest, note, studioUrl }: ProjectCarousel3DProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldRender = useShouldRender(containerRef);

  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth < 768);
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 767px)');
    const handler = (e: MediaQueryListEvent | MediaQueryList) => setIsMobile(e.matches);
    handler(mql);
    mql.addEventListener('change', handler as (e: MediaQueryListEvent) => void);
    return () => mql.removeEventListener('change', handler as (e: MediaQueryListEvent) => void);
  }, []);

  useEffect(() => {
    if (activeIndex >= projects.length) setActiveIndex(Math.max(0, projects.length - 1));
  }, [projects.length, activeIndex]);

  const urls = useMemo(() => projects.map((p) => modelUrl(manifest, p.slug, 'lod1')), [projects, manifest]);
  const activeProject = projects[activeIndex];
  const lite = tier === 'lite';
  const fov = isMobile ? 60 : 45;
  const dpr: [number, number] = lite || isMobile ? [1, 1] : [1, 2];

  return (
    <div
      ref={containerRef}
      data-testid="commons-stage"
      data-stage-tier={tier}
      className="relative w-full h-[60vh] phone-landscape:h-[70vh] sm:h-[60vh] lg:h-[70vh] rounded-xl overflow-hidden bg-zinc-950 border border-zinc-800 shadow-xl flex flex-col hide-scrollcontrols-scrollbar"
    >
      {note && projects.length > 0 && (
        <div className="absolute top-4 left-4 z-20 pointer-events-none bg-black/40 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 shadow-lg">
          <span className="text-xs text-zinc-300 font-medium">{note}</span>
        </div>
      )}

      <Canvas
        camera={{ position: [0, 0, 6], fov }}
        className="w-full h-full flex-grow"
        dpr={dpr}
        frameloop={shouldRender ? 'always' : 'never'}
        gl={{ antialias: !lite, powerPreference: lite ? 'low-power' : 'default' }}
      >
        <color attach="background" args={['#0a0a0a']} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[-5, 5, 5]} intensity={0.6} />
        <pointLight position={[0, 5, -5]} intensity={0.5} />
        <Suspense fallback={null}>
          {projects.length > 0 && (
            <ScrollControls pages={Math.max(1, projects.length * 0.5)} damping={0.2} horizontal infinite distance={1}>
              <CarouselTrack urls={urls} onActiveChange={setActiveIndex} />
            </ScrollControls>
          )}
          {!lite && !isMobile && <ContactShadows position={[0, -2, 0]} opacity={0.4} scale={20} blur={2} far={4.5} />}
        </Suspense>
      </Canvas>

      {projects.length === 0 && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center pointer-events-none">
          <p className="text-zinc-500 text-lg">{labels.noResults}</p>
        </div>
      )}

      {activeProject && (
        <CarouselUIOverlay project={activeProject} index={activeIndex} total={projects.length} labels={labels} studioUrl={studioUrl} />
      )}

      {projects.length > 1 && (
        <>
          <button
            type="button"
            onClick={() => setActiveIndex((i) => (i - 1 + projects.length) % projects.length)}
            className="sm:hidden absolute left-2 top-1/2 -translate-y-1/2 z-20 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-full bg-black/50 backdrop-blur-md border border-white/10 text-white/80 active:bg-white/20"
            aria-label={labels.prev}
          >
            <ChevronLeftIcon className="w-5 h-5" />
          </button>
          <button
            type="button"
            onClick={() => setActiveIndex((i) => (i + 1) % projects.length)}
            className="sm:hidden absolute right-2 top-1/2 -translate-y-1/2 z-20 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-full bg-black/50 backdrop-blur-md border border-white/10 text-white/80 active:bg-white/20"
            aria-label={labels.next}
          >
            <ChevronRightIcon className="w-5 h-5" />
          </button>
          <div className="absolute bottom-6 right-6 z-20 pointer-events-none flex items-center gap-2 bg-black/50 backdrop-blur-md px-4 py-2 rounded-full border border-white/10 shadow-lg text-white/80 motion-safe:animate-pulse">
            <MoveHorizontalIcon className="w-5 h-5" />
            <span className="text-sm font-medium tracking-wide">{isMobile ? labels.swipe : labels.drag}</span>
          </div>
        </>
      )}

      <style>{`
        .hide-scrollcontrols-scrollbar div { scrollbar-width: none !important; -ms-overflow-style: none !important; }
        .hide-scrollcontrols-scrollbar div::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }
      `}</style>
    </div>
  );
}
