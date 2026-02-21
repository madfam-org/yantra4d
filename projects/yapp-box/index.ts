import type { YantraCartridge } from '@yantra4d/sdk';
import manifestData from './project.json';

const cartridge: YantraCartridge = {
    manifest: manifestData as any,

    getScadContent: async (filename: string) => {
        if (typeof window === 'undefined') {
            const fs = require('fs');
            const path = require('path');
            return fs.promises.readFile(path.join(__dirname, '..', filename), 'utf-8');
        } else {
            throw new Error("fetching SCAD content in browser is not implemented in this demo cartridge");
        }
    }
};

export default cartridge;
