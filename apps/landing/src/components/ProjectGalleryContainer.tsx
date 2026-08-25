import React, { useState, useMemo } from 'react';
import ProjectCarousel3D from './ProjectCarousel3D';
import ProjectGalleryGrid from './ProjectGalleryGrid';
import { PROJECTS } from '../data/projects';
import modelManifest from '../../public/models/manifest.json';
import type { Translations } from '../lib/i18n';

// Slugs with a pre-rendered GLB. The carousel used to take the first 24
// hyperobjects in list order — none of which had a model — so every item fell
// through to the gray wireframe placeholder and the page's best asset showed
// 24 identical cubes. Real geometry goes first now.
const MODELLED_SLUGS = new Set(modelManifest.models.map((m) => m.slug));

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

        // The carousel exists to show live geometry, so anything with a
        // pre-rendered GLB goes first — hyperobjects ahead of the rest, since
        // they are what the section is about. Unmodelled hyperobjects fill any
        // remaining slots, so a filtered view still populates instead of
        // emptying. Stable partition throughout: original order within groups.
        const modelled = (p: { slug: string }) => MODELLED_SLUGS.has(p.slug);
        const ranked = [
            ...hyperobjects.filter(modelled),
            ...others.filter(modelled),
            ...hyperobjects.filter(p => !modelled(p)),
        ];

        const carousel = ranked.slice(0, CAROUSEL_LIMIT);
        const inCarousel = new Set(carousel.map(p => p.slug));

        // The grid is everything the carousel did not take, in the original
        // filtered order. Derived from the carousel rather than assembled
        // separately, so a project can never appear in both.
        const grid = filteredProjects.filter(p => !inCarousel.has(p.slug));

        const note = grid.length > 0
            ? (lang === 'es'
                ? `Mostrando ${carousel.length} de ${filteredProjects.length} en 3D — explora todos abajo`
                : `Showing ${carousel.length} of ${filteredProjects.length} in 3D — browse all below`)
            : undefined;

        return {
            carouselProjects: carousel,
            gridProjects: grid,
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
