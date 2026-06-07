/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const sessionSource = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'lib', 'tryon-session.ts'),
  'utf8'
);
const processingPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'processing', 'page.tsx'),
  'utf8'
);
const tryonPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'tryon', 'page.tsx'),
  'utf8'
);
const recordsPage = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'app', 'records', 'page.tsx'),
  'utf8'
);

assert(
  sessionSource.includes('resetFailedTryOnForRetry'),
  'try-on session utilities should expose a dedicated failed-task retry reset'
);

assert(
  sessionSource.includes('localStorage.removeItem(CURRENT_TRY_ON_ID_KEY)'),
  'failed retry reset should remove the failed current_try_on_id'
);

assert(
  sessionSource.includes('clearPendingTryOn(tryOn.nail_design_id, tryOn.hand_photo_id)'),
  'failed retry reset should clear the failed design/photo pending cache'
);

assert(
  processingPage.includes('resetFailedTryOnForRetry') &&
    processingPage.includes('api.getTryOn(tryOnId)') &&
    processingPage.includes('router.push(`/tryon?design=${failedTryOn.nail_design_id}`)'),
  'processing retry should load the failed record, clear retry state, and return to the design page'
);

assert(
  processingPage.includes('formatTryOnErrorMessage') &&
    processingPage.includes('All connection attempts failed') &&
    processingPage.includes('AI 生成服务暂时不可用，请稍后重试'),
  'processing failure should translate backend connection errors into user-facing copy'
);

assert(
  processingPage.includes('RUNNINGHUB_API_KEY') &&
    processingPage.includes('AI 生成通道尚未完成配置，请联系现场工作人员检查 RunningHub 密钥'),
  'processing failure should translate missing RunningHub configuration into user-facing copy'
);

assert(
  processingPage.includes('setElapsedTime(progress.elapsed_seconds)') &&
    processingPage.includes("if (state.status !== 'pending' && state.status !== 'processing')") &&
    processingPage.includes('return () => clearInterval(timer);'),
  'processing failure should freeze elapsed time once the task reaches a terminal state'
);

assert(
  processingPage.includes("status === 'completed';") &&
    !processingPage.includes("status === 'completed' || status === 'fallback_completed'") &&
    !processingPage.includes('已生成备用效果图') &&
    !processingPage.includes('备用效果图，仅供参考'),
  'processing page should not treat local fallback results as displayable completion'
);

assert(
  tryonPage.includes("data.status === 'failed'") &&
    tryonPage.includes('resetFailedTryOnForRetry(data') &&
    tryonPage.includes('router.replace(`/tryon?design=${data.nail_design_id}`)'),
  'opening a failed try-on record should redirect to the design page instead of rendering an empty result'
);

assert(
  tryonPage.includes("data.status === 'fallback_completed'") &&
    tryonPage.includes('resetFailedTryOnForRetry(data') &&
    !tryonPage.includes("existing.status === 'completed' || existing.status === 'fallback_completed'"),
  'tryon page should not reuse historical fallback results as successful AI results'
);

assert(
  recordsPage.includes("progress.status === 'completed'") &&
    recordsPage.includes("visibleStatus === 'completed'") &&
    recordsPage.includes('const displayImage =') &&
    recordsPage.includes("record.status === 'fallback_completed'") &&
    !recordsPage.includes("src={record.result_image_url || record.nail_design?.image_url || ''}") &&
    !recordsPage.includes("'fallback_completed'].includes(progress.status)") &&
    !recordsPage.includes('备用结果'),
  'records page should not show fallback result images as completed try-on history'
);

console.log('try-on retry recovery contract passed');
