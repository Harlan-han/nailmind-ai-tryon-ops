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
  apiSource.includes('event_key: string') &&
    apiSource.includes('recent_activity: Array<{'),
  'merchant overview activity API type should expose a stable event_key'
);

assert(
  merchantPage.includes('key={activity.event_key}') &&
    !merchantPage.includes('key={`${activity.action}-${activity.detail}-${activity.created_at || index}-${index}`}'),
  'merchant recent activity list should use backend event_key instead of index-based fallback keys'
);

console.log('merchant activity key contract passed');
