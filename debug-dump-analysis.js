
const fs = require('fs');
const html = fs.readFileSync('apps/studio/mock-dom-dump.html', 'utf8');

// Find the position of aria-labelledby="param-label-width"
const index = html.indexOf('aria-labelledby="param-label-width"');

if (index === -1) {
    console.log('Not found!');
    process.exit(1);
}

// Extract a chunk around it
const start = Math.max(0, index - 500);
const end = Math.min(html.length, index + 500);
const chunk = html.substring(start, end);

console.log('--- CONTEXT ---');
console.log(chunk);
console.log('--- END CONTEXT ---');
