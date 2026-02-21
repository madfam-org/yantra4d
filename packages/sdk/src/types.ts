/**
 * Core types for the Yantra4D SDK.
 * Defines the structure of hyperobject manifests and parameters.
 */

export interface YantraParameter {
    id: string;
    type: 'slider' | 'select' | 'boolean' | 'number' | 'string' | 'part_mode';
    label?: string | Record<string, string>;
    default?: any;
    min?: number;
    max?: number;
    step?: number;
    options?: Array<{ id: string; label?: string | Record<string, string> }>;
    visible_in_modes?: string[];
    group?: string;
    category?: string;
}

export interface YantraPart {
    id: string;
    name?: string | Record<string, string>;
    render_mode?: number;
    default_color?: string;
    static_stl?: string;
}

export interface YantraMode {
    id: string;
    name?: string | Record<string, string>;
    scad_file: string;
    parts: string[];
    estimate?: {
        base_units: number;
        formula_vars?: string[];
    };
}

export interface YantraProjectMetadata {
    name: string;
    slug: string;
    version: string;
    description?: string;
    engine?: string;
}

export interface YantraManifest {
    project: YantraProjectMetadata;
    parameters: YantraParameter[];
    parts: YantraPart[];
    modes: YantraMode[];
    estimate_constants?: Record<string, number>;
    camera_views?: any[];
    viewer?: any;
}

export interface RenderOptions {
    mode: string;
    params?: Record<string, any>;
    parts?: string[];
    colors?: Record<string, string>;
}

export interface RenderResult {
    url: string;
    logs: string;
}

/**
 * A Cartridge acts as the portable definition of a Hyperobject.
 */
export interface YantraCartridge {
    manifest: YantraManifest;
    // A function to fetch the raw SCAD content for a given mode's scad_file.
    // When packaged as an NPM module, this can be bundled or an asset loader.
    getScadContent?: (filename: string) => Promise<string>;
    // For pre-rendered static assets if needed.
    getStaticAsset?: (filename: string) => Promise<Blob>;
}
