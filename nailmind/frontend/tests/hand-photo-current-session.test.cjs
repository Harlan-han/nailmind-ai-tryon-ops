/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const sessionSource = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'lib', 'tryon-session.ts'),
  'utf8'
);
const uploadPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'upload', 'page.tsx'),
  'utf8'
);
const tryonPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'tryon', 'page.tsx'),
  'utf8'
);

assert(
  sessionSource.includes('saveCurrentHandPhoto') &&
    sessionSource.includes('clearCurrentHandPhoto'),
  'try-on session should expose a single source of truth for the current hand photo'
);

assert(
  uploadPage.includes('saveCurrentHandPhoto(photo)') &&
    uploadPage.includes('clearCurrentHandPhoto()') &&
    !uploadPage.includes("localStorage.setItem('current_hand_photo_id'") &&
    !uploadPage.includes("localStorage.setItem('current_hand_photo_url'"),
  'upload page should update the current hand profile through shared session helpers'
);

assert(
  tryonPage.includes('saveCurrentHandPhoto(photo)') &&
    tryonPage.includes('resolveHandPhotoForTryOn') &&
    tryonPage.includes('tryOnRecord.hand_photo_id') &&
    tryonPage.includes('api.getMyHandPhotos()') &&
    tryonPage.includes('if (tryOnId) return;') &&
    !tryonPage.includes("localStorage.setItem('current_hand_photo_id'") &&
    !tryonPage.includes("localStorage.setItem('current_hand_photo_url'"),
  'try-on page should sync the selected hand profile from backend records instead of stale localStorage'
);

console.log('hand photo current session contract passed');
