/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');

const root = join(__dirname, '..');
const apiSource = readFileSync(join(root, 'src/lib/api.ts'), 'utf8');
const uploadPage = readFileSync(join(root, 'src/app/upload/page.tsx'), 'utf8');

assert.match(apiSource, /getHandPhotoPresets:\s*\(\)\s*=>\s*fetchAPI\('\/users\/me\/hand-photo-presets'\)/);
assert.match(apiSource, /useHandPhotoPreset:\s*\(presetId:\s*string\)\s*=>/);
assert.match(apiSource, /`\/users\/me\/hand-photo-presets\/\$\{presetId\}\/use`/);

assert.match(uploadPage, /interface HandPhotoPreset/);
assert.match(uploadPage, /官方预设手模/);
assert.match(uploadPage, /不想上传也可以直接体验/);
assert.match(uploadPage, /api\.getHandPhotoPresets/);
assert.match(uploadPage, /api\.useHandPhotoPreset/);
assert.match(uploadPage, /setCurrentPhoto\(photo\)/);
assert.match(uploadPage, /setPhotos\(\(current\) =>/);
assert.match(uploadPage, /一键使用/);
assert.ok(
  uploadPage.indexOf('新增手部档案') < uploadPage.indexOf('Official Samples'),
  'official hand presets should render after the upload section'
);
assert.match(uploadPage, /snap-x snap-mandatory/);
assert.match(uploadPage, /\[scrollbar-width:none\]/);
assert.match(uploadPage, /\[\&::-webkit-scrollbar\]:hidden/);

console.log('hand photo presets contract passed');
