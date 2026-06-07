/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function loadAuthModule() {
  const sourcePath = path.join(__dirname, '../src/lib/auth.ts');
  const source = fs.readFileSync(sourcePath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
  }).outputText;

  const testModule = { exports: {} };
  const storage = new Map();
  const localStorage = {
    getItem: (key) => (storage.has(key) ? storage.get(key) : null),
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: (key) => storage.delete(key),
  };
  const cookieWrites = [];
  const document = {};
  Object.defineProperty(document, 'cookie', {
    get: () => cookieWrites.join('; '),
    set: (value) => cookieWrites.push(value),
  });
  const window = {
    localStorage,
    location: { pathname: '/', search: '' },
  };

  const context = {
    module: testModule,
    exports: testModule.exports,
    require: (request) => {
      if (request === './config') return { API_BASE_URL: 'http://localhost:8004/api' };
      if (request === './route-guards.js') {
        return require('../src/lib/route-guards.js');
      }
      return require(request);
    },
    window,
    document,
    localStorage,
    fetch: async () => ({ ok: true, json: async () => ({}) }),
  };

  vm.runInNewContext(compiled, context, { filename: sourcePath });
  return { auth: testModule.exports, storage, cookieWrites, window };
}

const { auth, storage, cookieWrites, window } = loadAuthModule();
const consumerUser = { id: 7, phone: '13910009999', nickname: '用户', user_type: 'consumer' };
const operatorUser = { id: 7, phone: '13910009999', nickname: '运营', user_type: 'admin' };

auth.saveAuthSession('consumer-token', consumerUser);
window.location.pathname = '/admin/login';
auth.saveAuthSession('operator-token', operatorUser);

assert.equal(storage.get('nailmind_consumer_auth_token'), 'consumer-token');
assert.equal(JSON.parse(storage.get('nailmind_consumer_auth_user')).user_type, 'consumer');
assert.equal(storage.get('nailmind_auth_token'), 'consumer-token');
assert.equal(JSON.parse(storage.get('nailmind_auth_user')).user_type, 'consumer');
assert.equal(storage.get('user_id'), String(consumerUser.id));
assert.equal(storage.get('nailmind_operator_auth_token'), 'operator-token');
assert.ok(cookieWrites.some((value) => value.startsWith('nailmind_consumer_auth_token=consumer-token')));
assert.ok(cookieWrites.some((value) => value.startsWith('nailmind_operator_auth_token=operator-token')));

window.location.pathname = '/';
storage.delete('nailmind_consumer_auth_token');
storage.delete('nailmind_auth_token');
assert.equal(auth.getAuthToken(), 'consumer-token');

assert.equal(auth.safeConsumerNextPath('/records'), '/records');
assert.equal(auth.safeConsumerNextPath('/tryon?design=12'), '/tryon?design=12');
assert.equal(auth.safeConsumerNextPath('/login'), '/');
assert.equal(auth.safeConsumerNextPath('/login?next=%2Frecords'), '/');
assert.equal(auth.safeConsumerNextPath('https://evil.example/phish'), '/');
assert.equal(auth.safeConsumerNextPath('//evil.example/phish'), '/');
assert.equal(auth.safeConsumerNextPath('/admin/assistant'), '/');
assert.equal(auth.safeConsumerNextPath('/merchant/bookings'), '/');

const legacyScope = loadAuthModule();
legacyScope.window.location.pathname = '/admin';
legacyScope.storage.set('nailmind_auth_user', JSON.stringify(consumerUser));
legacyScope.storage.set('user_id', String(consumerUser.id));

assert.equal(legacyScope.auth.getCurrentUser(), null);
assert.equal(legacyScope.auth.getCurrentUserId(), null);

console.log('auth session storage contract passed');
