(async () => {
  const assert = await import('node:assert/strict');
  const fs = await import('node:fs');
  const path = await import('node:path');

  const pageSource = fs.readFileSync(
    path.join(__dirname, '..', 'src', 'app', 'admin', 'designs', 'page.tsx'),
    'utf8',
  );

  assert.default(
    pageSource.includes("only_servable: 'true'") && pageSource.includes("dedupe_images: 'true'"),
    'admin design management should request the curated asset view instead of rendering broken or duplicated covers',
  );

  assert.default(
    pageSource.includes('function DesignCover') && pageSource.includes('封面异常'),
    'admin design cards should render a clear cover-error placeholder when an image still fails in the browser',
  );

  console.log('admin design asset contract passed');
})();
