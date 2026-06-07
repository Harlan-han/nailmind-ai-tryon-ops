/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert');

const assistantPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'admin', 'assistant', 'page.tsx'),
  'utf8'
);
const merchantPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'merchant', 'page.tsx'),
  'utf8'
);

assert(
  !assistantPage.includes("const webhookBaseUrl = typeof window === 'undefined'"),
  'admin assistant page must not derive webhookBaseUrl from window during render'
);

assert(
  assistantPage.includes('useEffect(() =>') && assistantPage.includes('setWebhookBaseUrl'),
  'admin assistant page should set webhookBaseUrl after client mount'
);

assert(
  !merchantPage.includes("useState(() =>") || !merchantPage.includes("localStorage.getItem('merchant_name')"),
  'merchant page must not read merchant_name from localStorage during render'
);

console.log('no render-time window contract passed');
