import React, { useRef, useState, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { ScrollControls, Scroll, useScroll, Environment, ContactShadows, Image, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
const SearchIcon = ({ className }: { className?: string }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    </svg>
);
const MoveHorizontalIcon = ({ className }: { className?: string }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <polyline points="18 8 22 12 18 16"></polyline>
        <polyline points="6 8 2 12 6 16"></polyline>
        <line x1="2" y1="12" x2="22" y2="12"></line>
    </svg>
);
import { API_URL, STUDIO_URL } from '../lib/env';
import { CATEGORIES } from '../data/projects';
import type { Translations } from '../lib/i18n';

function LoadedModel({ url }: { url: string }) {
    const geom = useLoader(STLLoader as any, url) as THREE.BufferGeometry;
    if (!geom) return null;

    geom.computeBoundingBox();
    const box = geom.boundingBox || new THREE.Box3();
    const center = new THREE.Vector3();
    box.getCenter(center);
    const size = new THREE.Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    const normalizedScale = 2.5 / maxDim;

    return (
        <group scale={normalizedScale} position={[-center.x * normalizedScale, -center.y * normalizedScale, -center.z * normalizedScale]}>
            <mesh geometry={geom}>
                <meshStandardMaterial color="#cbd5e1" roughness={0.4} metalness={0.1} />
            </mesh>
        </group>
    );
}

function LiveModel({ project, defaults }: { project: any, defaults: any }) {
    const [renderResult, setRenderResult] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const url = `${API_URL}/api/render`;
        const payload = {
            project: project.slug,
            parameters: defaults,
            export_format: 'stl'
        };

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(res => {
                if (!res.ok) throw new Error(`Render failed: ${res.status}`);
                return res.json();
            })
            .then(data => {
                if (data.status === 'success' && data.parts && data.parts.length > 0) {
                    const stlUrl = `${API_URL}${data.parts[0].url}`;
                    setRenderResult(stlUrl);
                } else {
                    throw new Error(data.error || 'No parts generated');
                }
                setLoading(false);
            })
            .catch(err => {
                console.error("Carousel live render failed:", err);
                setLoading(false);
            });

        return () => { };
    }, [project.slug, defaults]);

    if (loading || !renderResult) {
        return (
            <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="gray" wireframe />
            </mesh>
        );
    }

    return (
        <Suspense fallback={
            <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="gray" wireframe />
            </mesh>
        }>
            <LoadedModel url={renderResult} />
        </Suspense>
    );
}

function CarouselItem({ project, index, total, radius }: { project: any, index: number, total: number, radius: number }) {
    const groupRef = useRef<THREE.Group>(null as any);
    const [isActive, setIsActive] = useState(false);

    // Spread items in a circle
    const angle = (index / total) * Math.PI * 2;
    const x = Math.sin(angle) * radius;
    const z = Math.cos(angle) * radius;

    useFrame(() => {
        if (!groupRef.current) return;
        const worldPos = new THREE.Vector3();
        groupRef.current.getWorldPosition(worldPos);

        // Active if item is at the front (world Z is roughly 0, world X is roughly 0)
        const dist = Math.sqrt(worldPos.x * worldPos.x + worldPos.z * worldPos.z);
        const active = dist < (radius * 0.5);

        if (active !== isActive) {
            setIsActive(active);
        }

        // Slightly rotate it continuously if active to let user see the model spinning, 
        // or just let it sit if inactive
        if (active) {
            groupRef.current.rotation.y += 0.005;
        } else {
            groupRef.current.rotation.y += (angle - groupRef.current.rotation.y) * 0.1;
        }

        const targetScale = active ? 1.2 : 0.6;
        groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
    });

    const defaults = useMemo(() => {
        return {};
    }, [project]);

    return (
        <group ref={groupRef as any} position={[x, 0, z]} rotation={[0, angle, 0]}>
            {/* Show LiveModel directly to pre-load all */}
            <LiveModel project={project} defaults={defaults} />
        </group>
    );
}

function CarouselTrack({ projects, onActiveChange }: { projects: any[], onActiveChange: (idx: number) => void }) {
    const scroll = useScroll();
    const numItems = projects.length;

    // Auto-calculate an expanding radius depending on item count so they don't crash into each other
    const gap = 3.5;
    const radius = Math.max(4, (numItems * gap) / (2 * Math.PI));

    const trackRef = useRef<THREE.Group>(null as any);
    const lastOffset = useRef(0);
    const revolutions = useRef(0);

    useFrame((state, delta) => {
        let offset = scroll.offset;

        // Detect wrap-around when using infinite scroll
        // threshold 0.8 / 0.2 handles the jump from ~1 back to 0 or 0 to ~1
        if (offset < 0.2 && lastOffset.current > 0.8) {
            revolutions.current += 1;
        } else if (offset > 0.8 && lastOffset.current < 0.2) {
            revolutions.current -= 1;
        }
        lastOffset.current = offset;

        // The continuous offset can exceed 1
        const continuousOffset = offset + revolutions.current;

        // Treat 1.0 continuous offset as a full traverse of all items
        const rawIndex = continuousOffset * numItems;

        let activeIdx = Math.round(rawIndex) % numItems;
        if (activeIdx < 0) activeIdx += numItems;

        onActiveChange(activeIdx);

        if (trackRef.current) {
            // Spin the entire track in place (around Y axis) to bring the active index to the front
            const targetRotation = -rawIndex * (Math.PI * 2 / numItems);
            trackRef.current.rotation.y += (targetRotation - trackRef.current.rotation.y) * 5 * delta;
        }
    });

    return (
        <group ref={trackRef as any} position={[0, -0.5, -radius]}>
            {projects.map((project, i) => (
                <CarouselItem
                    key={project.slug}
                    project={project}
                    index={i}
                    total={numItems}
                    radius={radius}
                />
            ))}
        </group>
    );
}

function CarouselUIOverlay({ project, t, index, total, lang }: { project: any, t?: Translations, index: number, total: number, lang: string }) {
    if (!project) return null;
    const isEs = lang === 'es';

    return (
        <div className="absolute inset-0 z-10 pointer-events-none flex flex-col justify-between p-4 sm:p-8 pt-20 sm:pt-24">
            <div className="flex justify-between items-start pointer-events-auto">
                <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-full border border-border shadow-sm text-foreground">
                    <span className="text-sm font-medium">
                        {index + 1} <span className="text-muted-foreground mr-1">/</span> {total}
                    </span>
                </div>
            </div>

            <div className="w-full max-w-md pointer-events-auto mt-auto">
                <div className="bg-card/90 backdrop-blur-xl border border-border/50 shadow-2xl rounded-xl overflow-hidden transition-all duration-300 flex flex-col">
                    <div className="p-6 pb-3">
                        <div className="flex items-center justify-between mb-2">
                            <h3 className="text-2xl font-bold tracking-tight text-card-foreground">
                                {project.name}
                            </h3>
                        </div>
                        <p className="text-base text-muted-foreground line-clamp-2 leading-relaxed">
                            {isEs ? project.descriptionEs : project.description}
                        </p>
                    </div>

                    <div className="p-6 pt-0 pb-4 flex flex-col items-start gap-4">
                        <div className="flex flex-wrap gap-2">
                            {project.isHyperobject && (
                                <span className="px-2.5 py-1 rounded border border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium tracking-wide uppercase">
                                    Hyperobject
                                </span>
                            )}
                            <span className="px-2 py-1 rounded bg-muted text-muted-foreground text-xs font-medium">
                                {project.category}
                            </span>
                        </div>

                        <div className="w-full border-t border-border/40 pt-4 flex flex-row items-center justify-between">
                            <p className="text-xs text-muted-foreground italic">Live 3D Rendering Active</p>
                            <a
                                href={`${STUDIO_URL}#/${project.slug}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium text-sm px-4 py-2 rounded-md transition-colors flex items-center justify-center gap-2 group"
                            >
                                Open Studio
                                <span className="transform group-hover:translate-x-1 transition-transform">→</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function ProjectCarousel3D({
    lang = 'es',
    t,
    projects,
    searchQuery,
    setSearchQuery,
    activeCategory,
    setActiveCategory,
    activeDomain,
    setActiveDomain
}: {
    lang?: string,
    t?: Translations,
    projects: any[],
    searchQuery: string,
    setSearchQuery: (val: string) => void,
    activeCategory: string,
    setActiveCategory: (val: string) => void,
    activeDomain: string,
    setActiveDomain: (val: string) => void
}) {
    const [activeIndex, setActiveIndex] = useState(0);

    const gap = 4;
    const isEs = lang === 'es';

    const carouselProjects = projects;

    useEffect(() => {
        if (activeIndex >= carouselProjects.length) {
            setActiveIndex(Math.max(0, carouselProjects.length - 1));
        }
        // Force scroll to active item immediately (handled by SceneCenterer)
    }, [carouselProjects.length, activeIndex]);

    const activeProject = carouselProjects[activeIndex];

    return (
        <div className="relative w-full h-[70vh] rounded-xl overflow-hidden bg-zinc-950 border border-zinc-800 shadow-xl flex flex-col hide-scrollcontrols-scrollbar">
            {/* Top glassmorphic filter bar overlay */}
            <div className="absolute top-4 left-4 right-4 z-20 pointer-events-none flex flex-col gap-3">
                <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center">

                    {/* Filter Pills */}
                    <div className="pointer-events-auto flex flex-wrap gap-2 items-center bg-black/40 backdrop-blur-md p-1.5 rounded-xl border border-white/10 shadow-lg">
                        <select
                            value={activeCategory}
                            onChange={e => setActiveCategory(e.target.value)}
                            className="bg-transparent text-white text-sm outline-none px-2 py-1 appearance-none cursor-pointer hover:text-blue-400 transition-colors"
                        >
                            <option value="all" className="bg-zinc-900">{isEs ? 'Todas las Categorías' : 'All Categories'}</option>
                            {CATEGORIES.filter(c => c !== 'all').map(cat => (
                                <option key={cat} value={cat} className="bg-zinc-900 capitalize">{cat}</option>
                            ))}
                        </select>
                        <div className="w-px h-4 bg-white/20"></div>
                        <select
                            value={activeDomain}
                            onChange={e => setActiveDomain(e.target.value)}
                            className="bg-transparent text-white text-sm outline-none px-2 py-1 appearance-none cursor-pointer hover:text-blue-400 transition-colors"
                        >
                            <option value="all" className="bg-zinc-900">{isEs ? 'Todos los Dominios' : 'All Domains'}</option>
                            {['household', 'industrial', 'medical', 'commercial', 'hybrid', 'culture'].map(dom => (
                                <option key={dom} value={dom} className="bg-zinc-900 capitalize">{dom}</option>
                            ))}
                        </select>
                    </div>

                    {/* Search Bar */}
                    <div className="pointer-events-auto relative w-full sm:w-64">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <SearchIcon className="h-4 w-4 text-zinc-400" />
                        </div>
                        <input
                            type="text"
                            placeholder={isEs ? "Buscar hyperobjetos..." : "Search hyperobjects..."}
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="block w-full pl-10 pr-3 py-2 border border-white/10 rounded-xl leading-5 bg-black/40 backdrop-blur-md text-zinc-300 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-all shadow-lg"
                        />
                    </div>

                </div>
            </div>

            <Canvas camera={{ position: [0, 0, 6], fov: 45 }} className="w-full h-full flex-grow">
                <color attach="background" args={['#0a0a0a']} />
                <ambientLight intensity={0.5} />
                <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />

                <Suspense fallback={null}>
                    {carouselProjects.length > 0 && (
                        <ScrollControls
                            pages={Math.max(1, carouselProjects.length * 0.5)}
                            damping={0.2}
                            horizontal
                            infinite
                            distance={1}
                        >
                            <CarouselTrack projects={carouselProjects} onActiveChange={setActiveIndex} />
                        </ScrollControls>
                    )}

                    <ambientLight intensity={0.5} />
                    <directionalLight position={[-5, 5, 5]} intensity={0.5} />
                    <pointLight position={[0, 5, -5]} intensity={0.5} />
                    <ContactShadows position={[0, -2, 0]} opacity={0.4} scale={20} blur={2} far={4.5} />
                </Suspense>
            </Canvas>

            {carouselProjects.length === 0 && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center pointer-events-none">
                    <p className="text-zinc-500 text-lg">{isEs ? 'No se encontraron hyperobjetos.' : 'No hyperobjects found.'}</p>
                </div>
            )}

            {carouselProjects.length > 0 && (
                <CarouselUIOverlay
                    project={activeProject}
                    lang={lang}
                    t={t}
                    index={activeIndex}
                    total={carouselProjects.length}
                />
            )}
            {/* Scroll Indicator */}
            {carouselProjects.length > 1 && (
                <div className="absolute bottom-6 right-6 z-20 pointer-events-none hidden sm:flex items-center gap-2 bg-black/50 backdrop-blur-md px-4 py-2 rounded-full border border-white/10 shadow-lg text-white/80 animate-pulse">
                    <MoveHorizontalIcon className="w-5 h-5" />
                    <span className="text-sm font-medium tracking-wide">
                        {isEs ? 'Desliza para explorar' : 'Drag to explore'}
                    </span>
                </div>
            )}

            <style>{`
                .hide-scrollcontrols-scrollbar div {
                    scrollbar-width: none !important;
                    -ms-overflow-style: none !important;
                }
                .hide-scrollcontrols-scrollbar div::-webkit-scrollbar { 
                    display: none !important;
                    width: 0 !important;
                    height: 0 !important;
                }
            `}</style>
        </div>
    );
}
