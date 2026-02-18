import { Search, LayoutGrid, List as ListIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

export function ProjectToolbar({
    search,
    onSearchChange,
    sort,
    onSortChange,
    filterType,
    onFilterTypeChange,
    filterDifficulty,
    onFilterDifficultyChange,
    viewMode,
    onViewModeChange,
    t
}) {
    return (
        <div className="flex flex-col gap-4 mb-6">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">

                {/* Search */}
                <div className="relative w-full sm:w-72">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                        type="search"
                        placeholder={t('projects.search')}
                        className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        value={search}
                        onChange={(e) => onSearchChange(e.target.value)}
                    />
                </div>

                <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
                    {/* View Mode Toggle */}
                    <ToggleGroup type="single" value={viewMode} onValueChange={(val) => val && onViewModeChange(val)}>
                        <ToggleGroupItem value="grid" aria-label="Grid view" className="h-9 w-9 p-0">
                            <LayoutGrid className="h-4 w-4" />
                        </ToggleGroupItem>
                        <ToggleGroupItem value="list" aria-label="List view" className="h-9 w-9 p-0">
                            <ListIcon className="h-4 w-4" />
                        </ToggleGroupItem>
                    </ToggleGroup>

                    {/* Sort */}
                    <Select value={sort} onValueChange={onSortChange}>
                        <SelectTrigger className="w-[140px] h-9" aria-label="Sort by">
                            <SelectValue placeholder="Sort by" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="name_asc">{t('projects.sort.name_asc') || 'Name (A-Z)'}</SelectItem>
                            <SelectItem value="name_desc">{t('projects.sort.name_desc') || 'Name (Z-A)'}</SelectItem>
                            <SelectItem value="date_newest">{t('projects.sort.date_newest') || 'Newest First'}</SelectItem>
                            <SelectItem value="date_oldest">{t('projects.sort.date_oldest') || 'Oldest First'}</SelectItem>
                            <SelectItem value="complexity_asc">{t('projects.sort.complexity_asc') || 'Simpler First'}</SelectItem>
                            <SelectItem value="complexity_desc">{t('projects.sort.complexity_desc') || 'Complex First'}</SelectItem>
                        </SelectContent>
                    </Select>

                    {/* Filter Type */}
                    <Select value={filterType} onValueChange={onFilterTypeChange}>
                        <SelectTrigger className="w-[130px] h-9" aria-label="Filter by type">
                            <SelectValue placeholder="Type" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">{t('projects.filter.type.all') || 'All Types'}</SelectItem>
                            <SelectItem value="hyperobject">{t('projects.filter.type.hyperobject') || 'Hyperobjects'}</SelectItem>
                            <SelectItem value="demo">{t('projects.filter.type.demo') || 'Demos'}</SelectItem>
                        </SelectContent>
                    </Select>

                    {/* Filter Difficulty */}
                    <Select value={filterDifficulty} onValueChange={onFilterDifficultyChange}>
                        <SelectTrigger className="w-[130px] h-9" aria-label="Filter by difficulty">
                            <SelectValue placeholder="Difficulty" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">{t('projects.filter.difficulty.all') || 'All Difficulties'}</SelectItem>
                            <SelectItem value="beginner">{t('projects.filter.difficulty.beginner') || 'Beginner'}</SelectItem>
                            <SelectItem value="intermediate">{t('projects.filter.difficulty.intermediate') || 'Intermediate'}</SelectItem>
                            <SelectItem value="advanced">{t('projects.filter.difficulty.advanced') || 'Advanced'}</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>
        </div>
    )
}
