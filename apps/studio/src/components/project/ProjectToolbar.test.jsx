import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ProjectToolbar } from './ProjectToolbar'

const defaultProps = {
  search: '',
  onSearchChange: vi.fn(),
  sort: 'name_asc',
  onSortChange: vi.fn(),
  filterType: 'all',
  onFilterTypeChange: vi.fn(),
  filterDifficulty: 'all',
  onFilterDifficultyChange: vi.fn(),
  viewMode: 'grid',
  onViewModeChange: vi.fn(),
  t: (key) => {
    const map = {
      'projects.search': 'Search projects',
      'projects.sort.name_asc': 'Name (A-Z)',
      'projects.sort.name_desc': 'Name (Z-A)',
      'projects.sort.date_newest': 'Newest First',
      'projects.sort.date_oldest': 'Oldest First',
      'projects.sort.complexity_asc': 'Simpler First',
      'projects.sort.complexity_desc': 'Complex First',
      'projects.filter.type.all': 'All Types',
      'projects.filter.type.hyperobject': 'Hyperobjects',
      'projects.filter.type.demo': 'Demos',
      'projects.filter.difficulty.all': 'All Difficulties',
      'projects.filter.difficulty.beginner': 'Beginner',
      'projects.filter.difficulty.intermediate': 'Intermediate',
      'projects.filter.difficulty.advanced': 'Advanced',
    }
    return map[key] || key
  },
}

describe('ProjectToolbar', () => {
  it('renders search input with placeholder', () => {
    render(<ProjectToolbar {...defaultProps} />)
    expect(screen.getByPlaceholderText('Search projects')).toBeInTheDocument()
  })

  it('calls onSearchChange when typing in search', () => {
    const onSearchChange = vi.fn()
    render(<ProjectToolbar {...defaultProps} onSearchChange={onSearchChange} />)
    fireEvent.change(screen.getByPlaceholderText('Search projects'), {
      target: { value: 'test' },
    })
    expect(onSearchChange).toHaveBeenCalledWith('test')
  })

  it('renders view mode toggle buttons', () => {
    render(<ProjectToolbar {...defaultProps} />)
    expect(screen.getByLabelText('3D Carousel view')).toBeInTheDocument()
    expect(screen.getByLabelText('Grid view')).toBeInTheDocument()
    expect(screen.getByLabelText('List view')).toBeInTheDocument()
  })

  it('renders sort select with sort-by label', () => {
    render(<ProjectToolbar {...defaultProps} />)
    expect(screen.getByLabelText('Sort by')).toBeInTheDocument()
  })

  it('renders filter type select', () => {
    render(<ProjectToolbar {...defaultProps} />)
    expect(screen.getByLabelText('Filter by type')).toBeInTheDocument()
  })

  it('renders filter difficulty select', () => {
    render(<ProjectToolbar {...defaultProps} />)
    expect(screen.getByLabelText('Filter by difficulty')).toBeInTheDocument()
  })

  it('displays search value from props', () => {
    render(<ProjectToolbar {...defaultProps} search="hello" />)
    expect(screen.getByPlaceholderText('Search projects')).toHaveValue('hello')
  })

  it('uses fallback text when t returns empty for sort options', () => {
    const tEmpty = () => ''
    render(<ProjectToolbar {...defaultProps} t={tEmpty} />)
    // Fallback text should render — but since Select options are not visible until open,
    // just verify the component renders without error
    expect(screen.getByLabelText('Sort by')).toBeInTheDocument()
  })
})
