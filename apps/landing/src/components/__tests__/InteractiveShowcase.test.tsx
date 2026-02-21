import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import InteractiveShowcase from '../InteractiveShowcase';
import React from 'react';

// Mock dependencies
vi.mock('../../lib/env', () => ({
  STUDIO_URL: 'http://localhost:5173',
}));

describe('InteractiveShowcase', () => {
  it('renders the showcase tabs and default iframe', () => {
    render(<InteractiveShowcase />);
    
    // Check if the tabs rendered
    expect(screen.getByRole('tab', { name: 'Gridfinity' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Voronoi' })).toBeInTheDocument();
    
    // Check if the iframe points to the default slug
    const iframe = screen.getByTitle('Gridfinity interactive demo');
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute('src', 'http://localhost:5173?embed=true#/gridfinity');
  });

  it('changes the iframe and active tab on click', () => {
    render(<InteractiveShowcase />);
    
    // Click on Voronoi tab
    const voronoiTab = screen.getByRole('tab', { name: 'Voronoi' });
    fireEvent.click(voronoiTab);
    
    // The iframe should now point to Voronoi
    const iframe = screen.getByTitle('Voronoi interactive demo');
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute('src', 'http://localhost:5173?embed=true#/voronoi');
    
    // Voronoi tab should be selected
    expect(voronoiTab).toHaveAttribute('aria-selected', 'true');
  });
});
