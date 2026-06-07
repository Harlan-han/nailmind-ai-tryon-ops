(async () => {
  const assert = await import('node:assert/strict');
  const fs = await import('node:fs');
  const path = await import('node:path');

  const apiSource = fs.readFileSync(
    path.join(__dirname, '..', 'src', 'lib', 'api.ts'),
    'utf8',
  );

  assert.default(
    apiSource.includes("return fetchAPI(query ? `/designs/?${query}` : '/designs/');"),
    'listDesigns should keep the FastAPI trailing slash before query params to avoid auth-losing redirects',
  );

  console.log('design list trailing slash contract passed');
})();
