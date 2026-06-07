'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bot, Loader2, LockKeyhole, Phone, ShieldCheck } from 'lucide-react';
import { ApiError, api } from '@/lib/api';
import { saveAuthSession } from '@/lib/auth';

function authErrorMessage(error: unknown, fallback: string) {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 404) {
    return '当前后端未加载运营登录接口，请重启 8004 后端到最新代码后再试。';
  }
  if (error.message.includes('Phone is not allowed')) {
    return '该手机号未开通运营权限，请联系项目管理员加入运营白名单。';
  }
  if (error.message.includes('SMS provider') || error.message.includes('Unsupported SMS provider')) {
    return '短信服务未配置，请联系项目管理员配置短信服务后再登录。';
  }
  if (error.message.includes('Invalid or expired')) {
    return '验证码错误或已过期，请重新获取。';
  }
  return error.message;
}

export default function AdminLoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [nickname, setNickname] = useState('运营管理员');
  const [code, setCode] = useState('');
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestCode = async () => {
    if (!phone.trim()) {
      setError('请先输入运营手机号');
      return;
    }
    setSending(true);
    setError(null);
    try {
      const result = await api.requestLoginCode({
        phone: phone.trim(),
        nickname: nickname.trim() || undefined,
        user_type: 'admin',
      });
      setDebugCode(result.debug_code || null);
      if (result.debug_code) setCode(result.debug_code);
    } catch (err) {
      console.error(err);
      setError(authErrorMessage(err, '验证码发送失败，请确认后端服务已启动'));
    } finally {
      setSending(false);
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.login({
        phone: phone.trim(),
        nickname: nickname.trim() || undefined,
        code: code.trim(),
        user_type: 'admin',
      });
      saveAuthSession(result.access_token, result.user);
      router.replace('/admin/assistant');
    } catch (err) {
      console.error(err);
      setError(authErrorMessage(err, '登录失败，验证码可能已过期'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f7f1e7] px-6 py-10 text-stone-950">
      <main className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-5xl overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-2xl md:grid-cols-[1fr_420px]">
        <section className="hidden bg-stone-950 p-10 text-amber-50 md:block">
          <div className="flex h-full flex-col justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-amber-100/50">NailMind Ops</p>
              <h1 className="mt-6 text-4xl font-bold leading-tight">运营 Agent 是后台的第一入口</h1>
              <p className="mt-4 max-w-md text-sm leading-7 text-amber-100/70">
                登录后可以查看真实试戴、候选、预约和 Agent 建议。后续飞书/微信推送也会绑定到这个运营身份。
              </p>
            </div>
            <div className="rounded-[1.5rem] bg-white/10 p-5">
              <Bot className="mb-4 h-8 w-8 text-amber-200" />
              <p className="text-sm leading-6 text-amber-100/75">
                当前版本使用本地验证码方便验收，生产环境需要替换短信和企业成员校验。
              </p>
            </div>
          </div>
        </section>

        <form onSubmit={submit} className="flex flex-col justify-center p-6 md:p-8">
          <div className="mb-8">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-950 text-amber-50">
              <LockKeyhole className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-bold">运营端登录</h2>
            <p className="mt-2 text-sm text-stone-500">登录后进入 Chat 工作台，由 Agent 驱动今日运营动作。</p>
            <p className="mt-2 rounded-2xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
              运营账号需由项目管理员授权。开发验收环境会显示本地验证码，正式环境将通过短信和成员白名单校验。
            </p>
          </div>

          <label className="block text-sm font-semibold text-stone-700">
            运营昵称
            <input
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-stone-200 px-4 py-3 outline-none focus:border-stone-950"
              placeholder="运营管理员"
            />
          </label>

          <label className="mt-4 block text-sm font-semibold text-stone-700">
            手机号
            <div className="mt-2 flex items-center gap-2 rounded-2xl border border-stone-200 px-4 py-3 focus-within:border-stone-950">
              <Phone className="h-4 w-4 text-stone-400" />
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                className="min-w-0 flex-1 outline-none"
                placeholder="请输入运营手机号"
                inputMode="tel"
              />
            </div>
          </label>

          <div className="mt-4 grid grid-cols-[1fr_auto] gap-2">
            <input
              value={code}
              onChange={(event) => setCode(event.target.value)}
              className="rounded-2xl border border-stone-200 px-4 py-3 outline-none focus:border-stone-950"
              placeholder="验证码"
              inputMode="numeric"
            />
            <button
              type="button"
              onClick={requestCode}
              disabled={sending}
              className="rounded-2xl bg-stone-100 px-4 text-sm font-semibold text-stone-700 disabled:opacity-50"
            >
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : '获取'}
            </button>
          </div>

          {debugCode && <p className="mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">本地开发验证码：{debugCode}</p>}
          {error && <p className="mt-3 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={submitting || !phone.trim() || !code.trim()}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-stone-950 py-4 font-semibold text-amber-50 disabled:opacity-40"
          >
            {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <ShieldCheck className="h-5 w-5" />}
            进入运营 Agent
          </button>
        </form>
      </main>
    </div>
  );
}
