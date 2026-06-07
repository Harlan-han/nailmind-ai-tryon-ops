/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');

const root = join(__dirname, '..');
const loginPage = readFileSync(join(root, 'src/app/login/page.tsx'), 'utf8');
const homePage = readFileSync(join(root, 'src/app/page.tsx'), 'utf8');
const profilePage = readFileSync(join(root, 'src/app/profile/page.tsx'), 'utf8');

assert.match(loginPage, /const \[nickname/);
assert.match(loginPage, /placeholder="请输入用户名"/);
assert.match(loginPage, /nickname: nickname\.trim\(\) \|\| undefined/);
assert.match(loginPage, /登录成功/);
assert.match(loginPage, /正在回到刚才页面/);
assert.match(loginPage, /window\.setTimeout\(\(\) => router\.replace\(next\)/);

assert.equal(homePage.includes('getCurrentUser'), false);
assert.match(homePage, /href="\/profile"/);
assert.equal(homePage.includes('profileHref'), false);

assert.match(profilePage, /clearAuthSession/);
assert.match(profilePage, /退出账号/);
assert.match(profilePage, /账号管理/);
assert.match(profilePage, /router\.replace\('\/login'\)/);

console.log('consumer auth ux contract passed');
