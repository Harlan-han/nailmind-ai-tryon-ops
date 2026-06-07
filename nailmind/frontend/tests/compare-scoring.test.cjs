/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const comparePage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'compare', 'page.tsx'),
  'utf8'
);

assert(
  !comparePage.includes('Math.random'),
  'compare page must not use random scores for user-facing AI recommendations'
);

assert(
  comparePage.includes('api.getMyCandidateTryOns()'),
  'compare page should load dedicated candidate try-ons instead of filtering recent records'
);

assert(
  !comparePage.includes('api.getMyTryOns()'),
  'compare page must not filter candidates from the recent try-on record window'
);

const { scoreCandidateDesign } = require('../src/lib/compare-scoring.js');

const warmProfile = {
  skin_tone: 'medium',
  skin_undertone: 'warm',
  preferred_styles: [{ name: '法式', count: 3, score: 1 }],
  preferred_colors: [{ name: '金色', count: 2, score: 1 }],
  preferred_scenes: [{ name: '通勤', count: 4, score: 1 }],
};

const warmDesign = {
  id: 1,
  style_tags: ['法式', '极简'],
  color_tags: ['金色', '裸色'],
  scene_tags: ['通勤'],
  try_on_count: 18,
  favorite_count: 6,
};

const coolDesign = {
  id: 2,
  style_tags: ['猫眼'],
  color_tags: ['蓝色'],
  scene_tags: ['派对'],
  try_on_count: 2,
  favorite_count: 0,
};

const first = scoreCandidateDesign(warmDesign, warmProfile);
const second = scoreCandidateDesign(warmDesign, warmProfile);
const cooler = scoreCandidateDesign(coolDesign, warmProfile);

assert.deepEqual(first, second, 'candidate scoring must be stable for identical inputs');
assert(first.skin_tone_match > cooler.skin_tone_match, 'warm undertone should prefer warm/neutral colors');
assert(first.style_fit > cooler.style_fit, 'matching user style signals should improve style fit');
assert(first.occasion_fit > cooler.occasion_fit, 'matching scene signals should improve occasion fit');
assert(first.overall > cooler.overall, 'overall score should reflect user profile and engagement signals');

for (const [key, value] of Object.entries(first)) {
  assert(value >= 0 && value <= 1, `${key} must stay in 0..1`);
  assert.equal(Number(value.toFixed(2)), value, `${key} should be rounded for stable display`);
}

console.log('compare scoring contract passed');
