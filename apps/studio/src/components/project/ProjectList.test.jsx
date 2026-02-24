import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProjectList } from './ProjectList'

const t = (key) => {
  const map = {
    'projects.list.thumbnail': 'Image',
    'projects.list.name': 'Name',
    'projects.list.type': 'Type',
    'projects.list.stats': 'Stats',
    'projects.list.updated': 'Updated',
    'projects.open': 'Open Project',
  }
  return map[key] || key
}

const sampleProjects = [
  {
    slug: 'gridfinity',
    name: 'Gridfinity',
    thumbnail: '/thumb/gridfinity.png',
    is_hyperobject: false,
    is_demo: true,
    difficulty: 'beginner',
    mode_count: 3,
    parameter_count: 12,
    modified_at: 1700000000,
  },
  {
    slug: 'slide-holder',
    name: 'Microscope Slide Holder',
    thumbnail: null,
    is_hyperobject: true,
    is_demo: false,
    difficulty: null,
    mode_count: 2,
    parameter_count: 8,
    modified_at: null,
  },
]

function renderList(projects = sampleProjects) {
  return render(
    <MemoryRouter>
      <ProjectList projects={projects} t={t} />
    </MemoryRouter>
  )
}

describe('ProjectList', () => {
  it('returns null for empty array', () => {
    const { container } = render(<MemoryRouter><ProjectList projects={[]} t={t} /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })

  it('returns null for null projects', () => {
    const { container } = render(<MemoryRouter><ProjectList projects={null} t={t} /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })

  it('returns null for undefined projects', () => {
    const { container } = render(<MemoryRouter><ProjectList projects={undefined} t={t} /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })

  it('renders table with column headers', () => {
    renderList()
    expect(screen.getByText('Image')).toBeInTheDocument()
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Type')).toBeInTheDocument()
    expect(screen.getByText('Stats')).toBeInTheDocument()
    expect(screen.getByText('Updated')).toBeInTheDocument()
  })

  it('renders correct number of project rows', () => {
    renderList()
    const rows = screen.getAllByTestId('project-row')
    expect(rows).toHaveLength(2)
  })

  it('renders project name and slug', () => {
    renderList()
    expect(screen.getByText('Gridfinity')).toBeInTheDocument()
    expect(screen.getByText('gridfinity')).toBeInTheDocument()
    expect(screen.getByText('Microscope Slide Holder')).toBeInTheDocument()
    expect(screen.getByText('slide-holder')).toBeInTheDocument()
  })

  it('renders thumbnail image when available', () => {
    renderList()
    const img = screen.getByAltText('Gridfinity')
    expect(img).toHaveAttribute('src', '/thumb/gridfinity.png')
  })

  it('renders No Img placeholder when thumbnail is null', () => {
    renderList()
    expect(screen.getByText('No Img')).toBeInTheDocument()
  })

  it('renders Hyperobject badge for hyperobject projects', () => {
    renderList()
    expect(screen.getByText('Hyperobject')).toBeInTheDocument()
  })

  it('renders Demo badge for demo projects', () => {
    renderList()
    expect(screen.getByText('Demo')).toBeInTheDocument()
  })

  it('renders difficulty badge when present', () => {
    renderList()
    expect(screen.getByText('beginner')).toBeInTheDocument()
  })

  it('does not render difficulty badge when null', () => {
    renderList([{ ...sampleProjects[1] }])
    // No difficulty badge for slide-holder
    expect(screen.queryByText('beginner')).not.toBeInTheDocument()
  })

  it('renders mode and param counts', () => {
    renderList()
    expect(screen.getByText('3 modes')).toBeInTheDocument()
    expect(screen.getByText('12 params')).toBeInTheDocument()
  })

  it('renders formatted date when modified_at is present', () => {
    renderList()
    const date = new Date(1700000000 * 1000).toLocaleDateString()
    expect(screen.getByText(date)).toBeInTheDocument()
  })

  it('renders dash when modified_at is null', () => {
    renderList([sampleProjects[1]])
    expect(screen.getByText('-')).toBeInTheDocument()
  })

  it('renders open project links with correct hrefs', () => {
    renderList()
    const links = screen.getAllByTitle('Open Project')
    expect(links[0].closest('a')).toHaveAttribute('href', '/project/gridfinity')
    expect(links[1].closest('a')).toHaveAttribute('href', '/project/slide-holder')
  })

  it('uses fallback text when t returns empty strings', () => {
    const tEmpty = () => ''
    render(<MemoryRouter><ProjectList projects={sampleProjects} t={tEmpty} /></MemoryRouter>)
    // Fallback values from || operator
    expect(screen.getByText('Image')).toBeInTheDocument()
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Type')).toBeInTheDocument()
    expect(screen.getByText('Stats')).toBeInTheDocument()
    expect(screen.getByText('Updated')).toBeInTheDocument()
    expect(screen.getAllByTitle('Open Project')).toHaveLength(2)
  })
})
