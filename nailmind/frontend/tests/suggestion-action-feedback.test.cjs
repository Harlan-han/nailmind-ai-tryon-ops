/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const apiSource = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'lib', 'api.ts'),
  'utf8'
);
const suggestionsPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'admin', 'suggestions', 'page.tsx'),
  'utf8'
);

assert(
  apiSource.includes('OperationsSuggestionActionResult') &&
    apiSource.includes("applied_action: 'promote_hot_design' | 'demote_hot_design' | 'status_only'"),
  'operations API should type the applied suggestion action returned by accept'
);

assert(
  suggestionsPage.includes('lastAppliedAction') &&
    suggestionsPage.includes('api.acceptSuggestion(id)') &&
    suggestionsPage.includes('promote_hot_design') &&
    suggestionsPage.includes('demote_hot_design'),
  'suggestions page should show whether an accepted suggestion actually changed user-facing distribution'
);

console.log('suggestion action feedback contract passed');
