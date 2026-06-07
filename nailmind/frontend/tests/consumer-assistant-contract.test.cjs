/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');

const root = join(__dirname, '..');
const mobileShell = readFileSync(join(root, 'src/components/mobile-shell.tsx'), 'utf8');
const designCandidates = readFileSync(join(root, 'src/lib/design-candidates.ts'), 'utf8');
const tryonPage = readFileSync(join(root, 'src/app/tryon/page.tsx'), 'utf8');
const apiClient = readFileSync(join(root, 'src/lib/api.ts'), 'utf8');
const assistantPage = readFileSync(join(root, 'src/app/assistant/page.tsx'), 'utf8');

assert.match(mobileShell, /href: '\/assistant'/);
assert.match(mobileShell, /label: '助手'/);

assert.match(designCandidates, /getCurrentUserId/);
assert.match(designCandidates, /design_candidates_user_/);

assert.match(tryonPage, /DesignComment/);
assert.match(tryonPage, /design_comments_user_/);
assert.match(tryonPage, /author_name/);

assert.match(apiClient, /chatWithConsumerAssistant/);
assert.match(apiClient, /getConsumerAssistantInsights/);

assert.match(assistantPage, /checking/);
assert.match(assistantPage, /user\.user_type !== 'consumer'/);
assert.match(assistantPage, /scrollToLatest/);
assert.match(assistantPage, /onLoad=\{scrollToLatest\}/);
assert.match(assistantPage, /requestAnimationFrame/);
assert.match(assistantPage, /window\.scrollTo/);

console.log('consumer assistant contract passed');
