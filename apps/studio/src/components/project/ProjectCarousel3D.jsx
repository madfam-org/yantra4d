import { useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { ScrollControls, Scroll, useScroll, Environment, ContactShadows } from '@react-three/drei'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import CarouselItem from './CarouselItem'
import CarouselUIOverlay from './CarouselUIOverlay'

// The infinite scrolling track logic
function CarouselTrack({ projects, onActiveChange }) {
    const scroll = useScroll()
    const numItems = projects.length
    const gap = 4 // Distance between items in 3D units

    useFrame(() => {
        // Calculate the current active index based on scroll offset (0 to 1)
        // We multiply by numItems - 1 because offset goes up to exactly 1.0 at the end
        const rawIndex = scroll.offset * (Math.max(1, numItems - 1))
        const activeIdx = Math.round(rawIndex)
        onActiveChange(activeIdx)
    })

    return (
        <group>
            {projects.map((project, i) => {
                // Determine layout on X axis based on index and gap
                const posX = i * gap
                return (
                    <CarouselItem
                        key={project.slug}
                        project={project}
                        index={i}
                        position={[posX, 0, 0]}
                        gap={gap}
                    />
                )
            })}
        </group>
    )
}

function SceneCenterer({ children, activeIndex, gap }) {
    const groupRef = useRef()

    useFrame((state, delta) => {
        // Smoothly pan the entire group along X so the 'activeIndex' item
        // moves towards X = 0 (the center of the screen)
        const targetX = -activeIndex * gap
        if (groupRef.current) {
            // Lerp for smooth camera panning effect
            groupRef.current.position.x += (targetX - groupRef.current.position.x) * 5 * delta
        }
    })

    return <group ref={groupRef}>{children}</group>
}

export default function ProjectCarousel3D({ projects = [] }) {
    const { t, language } = useLanguage()
    const loc = (val) => (typeof val === 'object' && val !== null) ? (val[language] || val.en || '') : (val || '')
    const [activeIndex, setActiveIndex] = useState(0)
    const gap = 4

    if (!projects.length) return null

    const activeProject = projects[activeIndex]

    return (
        <div className="relative w-full h-[70vh] rounded-xl overflow-hidden bg-background border border-border shadow-sm">
            <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
                <color attach="background" args={['#0a0a0a']} />

                <ambientLight intensity={0.5} />
                <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />

                {/* We need ScrollControls to just capture the wheel/touch events. 
                    We set pages based on the number of items so the scrollbar feels right. */}
                <ScrollControls pages={Math.max(1, projects.length * 0.5)} damping={0.2} horizontal>

                    <SceneCenterer activeIndex={activeIndex} itemsCount={projects.length} gap={gap}>
                        <CarouselTrack projects={projects} onActiveChange={setActiveIndex} />
                    </SceneCenterer>

                    {/* HTML overlay layer directly tied to scroll state */}
                    <Scroll html style={{ width: '100%', height: '100%' }}>
                        <CarouselUIOverlay
                            project={activeProject}
                            loc={loc}
                            t={t}
                            index={activeIndex}
                            total={projects.length}
                        />
                    </Scroll>
                </ScrollControls>

                <Environment preset="city" />
                <ContactShadows position={[0, -2, 0]} opacity={0.4} scale={20} blur={2} far={4.5} />
            </Canvas>
        </div>
    )
}
