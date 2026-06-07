/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const pageSource = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'merchant', 'bookings', 'page.tsx'),
  'utf8'
);

assert.ok(
  pageSource.includes("const canComplete = booking.status !== 'completed' && booking.status !== 'cancelled'"),
  'booking follow-up page should allow completion for active statuses and block terminal statuses'
);

assert.ok(
  pageSource.includes("const canCancel = booking.status !== 'completed' && booking.status !== 'cancelled'"),
  'booking follow-up page should not allow cancellation after a terminal status'
);

assert.ok(
  pageSource.includes('advanceToCompleted') &&
    pageSource.includes('handleCompleteClick') &&
    pageSource.includes("['contacted', 'confirmed', 'completed']"),
  'booking completion should advance active bookings through the required linear status flow'
);

assert.ok(
  pageSource.includes("disabled={updatingId === booking.id || !canCancel}"),
  'booking cancellation button should be disabled after terminal statuses'
);

console.log('booking follow-up status contract passed');
