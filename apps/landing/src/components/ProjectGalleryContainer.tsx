import React, { useState, useMemo } from 'react';
import ProjectCarousel3D from './ProjectCarousel3D';
import ProjectGalleryGrid from './ProjectGalleryGrid';
import { PROJECTS } from '../data/projects';
import type { Translations } from '../lib/i18n';

// Cap the number of hyperobjects rendered as live WebGL meshes in the 3D carousel.
// Each carousel item mounts its own GLB mesh, so passing 200+ melts the GPU. The
// overflow is routed into the 2D grid below so nothing disappears from the gallery.
const CAROUSEL_LIMIT = 24;

export default function ProjectGalleryContainer({ lang = 'es', t }: { lang?: string, t?: Translations }) {
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState<string>('all');
    const [activeDomain, setActiveDomain] = useState<string>('all');

    // Filter projects
    const filteredProjects = useMemo(() => {
        return PROJECTS.filter(p => {
            if (searchQuery.trim()) {
                const q = searchQuery.toLowerCase();
                const text = `${p.name} ${p.description} ${p.descriptionEs}`.toLowerCase();
                if (!text.includes(q)) return false;
            }

            if (activeCategory === 'commons') {
                if (!p.isHyperobject) return false;
            } else if (activeCategory !== 'all') {
                if (p.category !== activeCategory) return false;
            }

            if (activeDomain !== 'all') {
                if (p.domain !== activeDomain) return false;
            }

            return true;
        });
    }, [searchQuery, activeCategory, activeDomain]);

    // Split for 3D and 2D. Only hyperobjects are candidates for the 3D carousel, but
    // we cap how many go live to protect the GPU; the rest fall through to the grid.
    const { carouselProjects, gridProjects, carouselNote } = useMemo(() => {
        const hyperobjects = filteredProjects.filter(p => p.isHyperobject);
        const others = filteredProjects.filter(p => !p.isHyperobject);

        const carousel = hyperobjects.slice(0, CAROUSEL_LIMIT);
        const overflow = hyperobjects.slice(CAROUSEL_LIMIT);

        const note = overflow.length > 0
            ? (lang === 'es'
                ? `Mostrando ${carousel.length} de ${hyperobjects.length} en 3D — explora todos abajo`
                : `Showing ${carousel.length} of ${hyperobjects.length} in 3D — browse all below`)
            : undefined;

        return {
            carouselProjects: carousel,
            // Overflow hyperobjects join the grid so nothing disappears.
            gridProjects: [...overflow, ...others],
            carouselNote: note,
        };
    }, [filteredProjects, lang]);

    return (
        <div className="flex flex-col gap-16">
            <ProjectCarousel3D
                lang={lang}
                t={t}
                projects={carouselProjects}
                carouselNote={carouselNote}
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                activeCategory={activeCategory}
                setActiveCategory={setActiveCategory}
                activeDomain={activeDomain}
                setActiveDomain={setActiveDomain}
            />
            <ProjectGalleryGrid
                lang={lang}
                t={t}
                projects={gridProjects}
                activeCategory={activeCategory}
                setActiveCategory={setActiveCategory}
            />
        </div>
    );
}
