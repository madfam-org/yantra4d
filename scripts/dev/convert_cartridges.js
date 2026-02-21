const fs = require('fs');
const path = require('path');

const projects = [
    'ultimate-box',
    'keyv2',
    'multiboard',
    'yapp-box',
    'stemfie',
    'polydice',
    'custom-msh',
    'slide-holder',
    'rugged-box',
    'tablaco',
    'microscope-slide-holder'
];

// Let's also check if 'extrusion-hyperobject' is in projects/ or root.
if (fs.existsSync(path.join(__dirname, '../projects/extrusion-hyperobject'))) {
    projects.push('extrusion-hyperobject');
}

projects.forEach(project => {
    const dir = path.join(__dirname, '../projects', project);
    if (!fs.existsSync(dir)) {
        console.log(`Skipping ${project}, directory not found.`);
        return;
    }

    // 1. package.json
    const packageJson = {
        name: `@yantra4d/${project}`,
        version: "1.0.0",
        description: `${project} Yantra4D Hyperobject Cartridge`,
        main: "./dist/index.js",
        module: "./dist/index.mjs",
        types: "./dist/index.d.ts",
        exports: {
            ".": {
                require: "./dist/index.js",
                import: "./dist/index.mjs",
                types: "./dist/index.d.ts"
            }
        },
        scripts: {
            build: "tsup index.ts --format cjs,esm --dts"
        },
        dependencies: {
            "@yantra4d/sdk": "file:../../packages/sdk"
        },
        devDependencies: {
            "@types/node": "^20.0.0",
            "tsup": "^8.0.0",
            "typescript": "^5.0.0"
        }
    };

    fs.writeFileSync(path.join(dir, 'package.json'), JSON.stringify(packageJson, null, 2));

    // 2. tsconfig.json
    const tsconfigJson = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "CommonJS",
            "moduleResolution": "node",
            "esModuleInterop": true,
            "forceConsistentCasingInFileNames": true,
            "strict": true,
            "skipLibCheck": true,
            "resolveJsonModule": true,
            "declaration": true
        },
        "include": ["index.ts"]
    };
    fs.writeFileSync(path.join(dir, 'tsconfig.json'), JSON.stringify(tsconfigJson, null, 2));

    // 3. index.ts
    const indexTs = `import type { YantraCartridge } from '@yantra4d/sdk';
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
`;
    fs.writeFileSync(path.join(dir, 'index.ts'), indexTs);
    console.log(`Converted ${project}`);
});
