/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const apiSource = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'lib', 'api.ts'),
  'utf8'
);
const merchantPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'merchant', 'page.tsx'),
  'utf8'
);

assert(
  apiSource.includes('failed_try_ons: number'),
  'merchant overview API type should expose failed try-on diagnostics'
);

assert(
  merchantPage.includes("label: '失败试戴'") &&
    merchantPage.includes('overview?.failed_try_ons') &&
    merchantPage.includes('AlertCircle'),
  'merchant page should surface failed try-on count for operational troubleshooting'
);

console.log('merchant failure diagnostics contract passed');
