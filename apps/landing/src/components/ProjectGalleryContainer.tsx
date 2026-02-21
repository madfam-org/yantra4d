import React, { useState, useMemo } from 'react';
import ProjectCarousel3D from './ProjectCarousel3D';
import ProjectGalleryGrid from './ProjectGalleryGrid';
import { PROJECTS } from '../data/projects';
import type { Translations } from '../lib/i18n';

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

    // Split for 3D and 2D
    const carouselProjects = filteredProjects.filter(p => p.isHyperobject);
    const gridProjects = filteredProjects.filter(p => !p.isHyperobject);

    return (
        <div className="flex flex-col gap-16">
            <ProjectCarousel3D
                lang={lang}
                t={t}
                projects={carouselProjects}
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
