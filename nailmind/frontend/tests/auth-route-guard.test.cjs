/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');

const {
  resolveRouteAuth,
  AUTH_COOKIE_NAMES,
} = require('../src/lib/route-guards.js');

function tokenFor(userType, expiresInSeconds = 3600) {
  const payload = {
    sub: '1',
    user_type: userType,
    exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
  };
  const encoded = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `header.${encoded}.signature`;
}

function tokenWithoutExpiry(userType) {
  const payload = {
    sub: '1',
    user_type: userType,
  };
  const encoded = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `header.${encoded}.signature`;
}

function tokenWithPayload(payload) {
  const encoded = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `header.${encoded}.signature`;
}

function resolve(pathname, search = '', cookies = {}) {
  return resolveRouteAuth({ pathname, search, cookies, nowSeconds: Math.floor(Date.now() / 1000) });
}

const consumerToken = tokenFor('consumer');
const operatorToken = tokenFor('admin');
const expiredConsumerToken = tokenFor('consumer', -60);
const consumerTokenWithoutExpiry = tokenWithoutExpiry('consumer');
const operatorTokenWithoutExpiry = tokenWithoutExpiry('admin');
const tokenWithoutSubject = tokenWithPayload({
  user_type: 'consumer',
  exp: Math.floor(Date.now() / 1000) + 3600,
});
const tokenWithUnknownRole = tokenWithPayload({
  sub: '1',
  user_type: 'guest',
  exp: Math.floor(Date.now() / 1000) + 3600,
});
const tokenWithNonNumericSubject = tokenWithPayload({
  sub: 'abc',
  user_type: 'consumer',
  exp: Math.floor(Date.now() / 1000) + 3600,
});

assert.deepEqual(resolve('/admin/assistant'), {
  action: 'redirect',
  destination: '/admin/login',
});

assert.deepEqual(resolve('/admin/login', '', { [AUTH_COOKIE_NAMES.operator]: operatorToken }), {
  action: 'redirect',
  destination: '/admin/assistant',
});

assert.deepEqual(resolve('/admin', '', { [AUTH_COOKIE_NAMES.consumer]: consumerToken }), {
  action: 'redirect',
  destination: '/admin/login',
});

assert.deepEqual(resolve('/upload'), {
  action: 'redirect',
  destination: '/login?next=%2Fupload',
});

assert.deepEqual(resolve('/assistant'), {
  action: 'redirect',
  destination: '/login?next=%2Fassistant',
});

assert.deepEqual(resolve('/tryon', '?design=12'), {
  action: 'redirect',
  destination: '/login?next=%2Ftryon%3Fdesign%3D12',
});

assert.deepEqual(resolve('/profile', '', { [AUTH_COOKIE_NAMES.operator]: operatorToken }), {
  action: 'redirect',
  destination: '/login?next=%2Fprofile',
});

assert.deepEqual(resolve('/admin/login', '', { [AUTH_COOKIE_NAMES.consumer]: consumerToken }), {
  action: 'next',
});

assert.deepEqual(resolve('/login', '', { [AUTH_COOKIE_NAMES.operator]: operatorToken }), {
  action: 'next',
});

assert.deepEqual(resolve('/login', '?next=%2Frecords', { [AUTH_COOKIE_NAMES.consumer]: consumerToken }), {
  action: 'redirect',
  destination: '/records',
});

assert.deepEqual(resolve('/login', '?next=https%3A%2F%2Fevil.example%2Fphish', { [AUTH_COOKIE_NAMES.consumer]: consumerToken }), {
  action: 'redirect',
  destination: '/',
});

assert.deepEqual(resolve('/login', '?next=%2Fadmin%2Fassistant', { [AUTH_COOKIE_NAMES.consumer]: consumerToken }), {
  action: 'redirect',
  destination: '/',
});

assert.deepEqual(resolve('/records', '', { [AUTH_COOKIE_NAMES.consumer]: expiredConsumerToken }), {
  action: 'redirect',
  destination: '/login?next=%2Frecords',
});

assert.deepEqual(resolve('/records', '', { [AUTH_COOKIE_NAMES.consumer]: consumerTokenWithoutExpiry }), {
  action: 'redirect',
  destination: '/login?next=%2Frecords',
});

assert.deepEqual(resolve('/admin/assistant', '', { [AUTH_COOKIE_NAMES.operator]: operatorTokenWithoutExpiry }), {
  action: 'redirect',
  destination: '/admin/login',
});

assert.deepEqual(resolve('/records', '', { [AUTH_COOKIE_NAMES.consumer]: tokenWithoutSubject }), {
  action: 'redirect',
  destination: '/login?next=%2Frecords',
});

assert.deepEqual(resolve('/records', '', { [AUTH_COOKIE_NAMES.consumer]: tokenWithUnknownRole }), {
  action: 'redirect',
  destination: '/login?next=%2Frecords',
});

assert.deepEqual(resolve('/records', '', { [AUTH_COOKIE_NAMES.consumer]: tokenWithNonNumericSubject }), {
  action: 'redirect',
  destination: '/login?next=%2Frecords',
});

assert.deepEqual(resolve('/admin/assistant', '', { [AUTH_COOKIE_NAMES.operator]: tokenWithUnknownRole }), {
  action: 'redirect',
  destination: '/admin/login',
});

assert.deepEqual(resolve('/designs'), { action: 'next' });

console.log('auth route guard contract passed');
