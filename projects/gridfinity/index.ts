import type { YantraCartridge } from '@yantra4d/sdk';
import manifestData from './project.json';

// In a real build step, the SCAD files could be embedded or copied.
// For now, we define the structure of the Gridfinity cartridge.
const cartridge: YantraCartridge = {
    manifest: manifestData as any,

    getScadContent: async (filename: string) => {
        if (typeof window === 'undefined') {
            // Node.js environment: we can read from the local file system.
            const fs = require('fs');
            const path = require('path');
            return fs.promises.readFile(path.join(__dirname, '..', filename), 'utf-8');
        } else {
            // Browser environment: SCAD contents should be fetched via URL or embedded at build step.
            throw new Error("fetching SCAD content in browser is not implemented in this demo cartridge");
        }
    }
};

export default cartridge;
