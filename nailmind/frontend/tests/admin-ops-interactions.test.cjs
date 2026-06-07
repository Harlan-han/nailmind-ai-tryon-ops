/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const read = (...segments) =>
  fs.readFileSync(path.join(__dirname, '..', ...segments), 'utf8');

const insightsPage = read('src', 'app', 'admin', 'insights', 'page.tsx');
const coldPage = read('src', 'app', 'admin', 'cold', 'page.tsx');
const suggestionsPage = read('src', 'app', 'admin', 'suggestions', 'page.tsx');
const bookingsPage = read('src', 'app', 'merchant', 'bookings', 'page.tsx');
const assistantPage = read('src', 'app', 'admin', 'assistant', 'page.tsx');

assert.ok(
  insightsPage.includes('OpsImage') && insightsPage.includes('库存管理建议'),
  'AI insights inventory cards should use the shared operations image component'
);

assert.ok(
  coldPage.includes('handleAdjustPlacement') &&
    coldPage.includes('handleOpenTagEditor') &&
    coldPage.includes('handleArchiveDesign') &&
    coldPage.includes('api.toggleDesignHot') &&
    coldPage.includes('api.updateDesignStatus') &&
    coldPage.includes('api.updateDesign'),
  'cold repair page should wire placement, tag editing, and archive actions to real APIs'
);

assert.ok(
  suggestionsPage.includes("setFilter('pending')") &&
    suggestionsPage.includes("setFilter('accepted')") &&
    suggestionsPage.includes("setFilter('completed')") &&
    suggestionsPage.includes("setFilter('agent')"),
  'suggestion stats should be clickable filter controls'
);

assert.ok(
  bookingsPage.includes('advanceToCompleted') &&
    bookingsPage.includes('handleCompleteClick') &&
    bookingsPage.includes('completionHint'),
  'booking follow-up page should explain and handle completion progression'
);

assert.ok(
  assistantPage.includes('activePanel') &&
    assistantPage.includes('chat-page-shell') &&
    assistantPage.includes('chat-main-column') &&
    assistantPage.includes('chat-message-stream') &&
    assistantPage.includes('agent-side-rail') &&
    assistantPage.includes('chat-input-dock') &&
    assistantPage.includes('quickQuestions') &&
    assistantPage.includes('showQuickPrompts') &&
    assistantPage.includes('quick-prompt-overlay') &&
    assistantPage.includes('预设问题') &&
    assistantPage.includes('sticky bottom-0') &&
    assistantPage.includes('messageEndRef') &&
    assistantPage.includes('scrollIntoView') &&
    assistantPage.includes('sidePanelTabs') &&
    assistantPage.includes('DeepSeek 未连接') &&
    assistantPage.includes('nailmind\\\\scripts\\\\set-local-secrets.ps1 -DeepSeekOnly'),
  'assistant page should be a left chat surface with right vertical tool rail, fixed composer, auto-follow, and actionable key guidance'
);

assert.ok(
  !assistantPage.includes('chat-shell-main') &&
    !assistantPage.includes('xl:grid-cols-[minmax(0,1fr)_380px]') &&
    !assistantPage.includes('agent-inline-tools') &&
    !assistantPage.includes('overflow-x-auto pb-1') &&
    !assistantPage.includes('rounded-[2rem] border border-stone-200 bg-[#fffaf0] shadow-sm'),
  'assistant page should not render top tool tabs, a quick-prompt horizontal scroller, or the old bordered chat window'
);

assert.ok(
  !assistantPage.includes('Chat first') &&
    !assistantPage.includes('Tool calling') &&
    !assistantPage.includes('External gateway') &&
    !assistantPage.includes('Scheduled task'),
  'assistant page should remove the top explanatory stat cards so the chat can fit in one viewport'
);

console.log('admin ops interactions contract passed');
