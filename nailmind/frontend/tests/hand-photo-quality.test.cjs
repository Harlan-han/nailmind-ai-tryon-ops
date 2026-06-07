/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function loadQualityModule() {
  const sourcePath = path.join(__dirname, '../src/lib/hand-photo-quality.ts');
  const source = fs.readFileSync(sourcePath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
  }).outputText;

  const testModule = { exports: {} };
  vm.runInNewContext(compiled, {
    module: testModule,
    exports: testModule.exports,
    require,
  }, { filename: sourcePath });
  return testModule.exports;
}

const { assessHandPhotoQuality } = loadQualityModule();

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

assert.deepEqual(plain(assessHandPhotoQuality({
  hand_detected: false,
  quality_score: 0.92,
  recommendations: ['未检测到手部，请上传包含手部的照片'],
})), {
  ok: false,
  message: '未检测到手部，请上传包含手部的照片',
});

assert.deepEqual(plain(assessHandPhotoQuality({
  hand_detected: true,
  quality_score: 0.44,
  recommendations: ['照片过暗，建议在自然光下重新拍摄'],
})), {
  ok: false,
  message: '照片质量偏低，请重新拍摄一张更清晰的手部照片。',
});

assert.deepEqual(plain(assessHandPhotoQuality({
  hand_detected: true,
  quality_score: 0.62,
  recommendations: ['建议保持手部平放'],
})), {
  ok: true,
  message: null,
});

console.log('hand photo quality gate contract passed');
