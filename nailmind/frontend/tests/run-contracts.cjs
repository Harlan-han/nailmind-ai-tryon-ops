(async () => {
  const { readdirSync } = await import("node:fs");
  const { join } = await import("node:path");
  const { spawnSync } = await import("node:child_process");

  const testsDir = __dirname;
  const testFiles = readdirSync(testsDir)
    .filter((name) => name.endsWith(".test.cjs"))
    .sort();

  for (const fileName of testFiles) {
    const result = spawnSync(process.execPath, [join(testsDir, fileName)], {
      stdio: "inherit",
    });

    if (result.status !== 0) {
      process.exit(result.status ?? 1);
    }
  }
})();
