/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const uploadPage = fs.readFileSync(path.join(__dirname, '../src/app/upload/page.tsx'), 'utf8');
const nextConfig = fs.readFileSync(path.join(__dirname, '../next.config.ts'), 'utf8');

assert.equal(uploadPage.includes('http://localhost:8003'), false);
assert.ok(uploadPage.includes('/ai/analyze/hand'));

assert.ok(nextConfig.includes('NEXT_PUBLIC_AI_SERVICE_ORIGIN'));
assert.ok(nextConfig.includes("source: '/ai/:path*'"));
assert.ok(nextConfig.includes('destination: `${aiServiceOrigin}/:path*`'));

console.log('ai service rewrite contract passed');
