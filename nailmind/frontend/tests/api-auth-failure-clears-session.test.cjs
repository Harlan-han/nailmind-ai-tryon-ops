/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function loadApiModule(fetchResponse, pathname = '/records') {
  const sourcePath = path.join(__dirname, '../src/lib/api.ts');
  const source = fs.readFileSync(sourcePath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
  }).outputText;

  const testModule = { exports: {} };
  const authEvents = [];
  const window = {
    location: {
      pathname,
      search: '',
      href: pathname,
    },
  };

  const context = {
    module: testModule,
    exports: testModule.exports,
    require: (request) => {
      if (request === './auth') {
        return {
          getAuthToken: () => 'stale-token',
          clearAuthSession: () => authEvents.push('clear'),
        };
      }
      if (request === './config') {
        return { API_BASE_URL: 'http://localhost:8004/api' };
      }
      return require(request);
    },
    fetch: async () => fetchResponse,
    window,
    URLSearchParams,
  };

  vm.runInNewContext(compiled, context, { filename: sourcePath });
  return { api: testModule.exports.api, authEvents, window };
}

(async () => {
  const { api, authEvents, window } = loadApiModule({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Invalid token' }),
  });

  await assert.rejects(() => api.getMyTryOns(), {
    name: 'ApiError',
    status: 401,
  });

  assert.deepEqual(authEvents, ['clear']);
  assert.equal(window.location.href, '/login?next=%2Frecords');

  const authFlow = loadApiModule({
    ok: false,
    status: 403,
    json: async () => ({ detail: 'Phone not allowed for operator login' }),
  }, '/admin/login');

  await assert.rejects(() => authFlow.api.requestLoginCode({
    phone: '13800000000',
    user_type: 'merchant',
  }), {
    name: 'ApiError',
    status: 403,
    message: 'Phone not allowed for operator login',
  });

  assert.deepEqual(authFlow.authEvents, []);
  assert.equal(authFlow.window.location.href, '/admin/login');

  const validationFlow = loadApiModule({
    ok: false,
    status: 422,
    json: async () => ({
      detail: [
        {
          loc: ['body', 'code'],
          msg: 'String should have at most 8 characters',
        },
      ],
    }),
  }, '/login');

  await assert.rejects(() => validationFlow.api.login({
    phone: '15287403872',
    code: '12345678901',
    user_type: 'consumer',
  }), {
    name: 'ApiError',
    status: 422,
    message: 'code: String should have at most 8 characters',
  });

  console.log('api auth failure clears session contract passed');
})();
