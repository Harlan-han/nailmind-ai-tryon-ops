/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const { AUTH_COOKIE_NAMES } = require('../src/lib/route-guards.js');

const proxyPath = path.join(__dirname, '../src/proxy.ts');

function loadProxyModule() {
  const source = fs.readFileSync(proxyPath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
  }).outputText;

  const testModule = { exports: {} };
  const context = {
    module: testModule,
    exports: testModule.exports,
    require: (moduleName) => {
      if (moduleName === 'next/server') {
        return {
          NextResponse: {
            next: () => ({ action: 'next' }),
            redirect: (url) => ({ action: 'redirect', destination: url.toString() }),
          },
        };
      }
      if (moduleName === './lib/route-guards.js') {
        return require('../src/lib/route-guards.js');
      }
      return require(moduleName);
    },
    URL,
  };

  vm.runInNewContext(compiled, context, { filename: proxyPath });
  return testModule.exports;
}

function tokenFor(userType, expiresInSeconds = 3600) {
  const payload = {
    sub: '1',
    user_type: userType,
    exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
  };
  const encoded = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `header.${encoded}.signature`;
}

function requestFor(pathnameAndSearch, cookieValues = {}) {
  const url = new URL(`http://localhost:3000${pathnameAndSearch}`);
  return {
    url: url.toString(),
    nextUrl: {
      pathname: url.pathname,
      search: url.search,
    },
    cookies: {
      get: (name) => {
        const value = cookieValues[name];
        return value ? { name, value } : undefined;
      },
    },
  };
}

const { proxy, config } = loadProxyModule();
const consumerToken = tokenFor('consumer');
const operatorToken = tokenFor('admin');

assert.equal(typeof proxy, 'function');

assert.deepEqual(proxy(requestFor('/admin/assistant')), {
  action: 'redirect',
  destination: 'http://localhost:3000/admin/login',
});

assert.deepEqual(proxy(requestFor('/upload')), {
  action: 'redirect',
  destination: 'http://localhost:3000/login?next=%2Fupload',
});

assert.deepEqual(proxy(requestFor('/records?page=1')), {
  action: 'redirect',
  destination: 'http://localhost:3000/login?next=%2Frecords%3Fpage%3D1',
});

assert.deepEqual(proxy(requestFor('/admin/assistant', {
  [AUTH_COOKIE_NAMES.operator]: operatorToken,
})), {
  action: 'next',
});

assert.deepEqual(proxy(requestFor('/upload', {
  [AUTH_COOKIE_NAMES.consumer]: consumerToken,
})), {
  action: 'next',
});

assert.deepEqual(proxy(requestFor('/login?next=%2Frecords', {
  [AUTH_COOKIE_NAMES.consumer]: consumerToken,
})), {
  action: 'redirect',
  destination: 'http://localhost:3000/records',
});

assert.deepEqual(proxy(requestFor('/admin/login', {
  [AUTH_COOKIE_NAMES.operator]: operatorToken,
})), {
  action: 'redirect',
  destination: 'http://localhost:3000/admin/assistant',
});

[
  '/login',
  '/admin/login',
  '/admin/:path*',
  '/merchant/:path*',
  '/upload/:path*',
  '/tryon/:path*',
  '/processing/:path*',
  '/records/:path*',
  '/candidates/:path*',
  '/compare/:path*',
  '/profile/:path*',
].forEach((matcher) => {
  assert.ok(config.matcher.includes(matcher), `missing matcher: ${matcher}`);
});

console.log('auth proxy runtime contract passed');
