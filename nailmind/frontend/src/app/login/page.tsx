'use client';

import { FormEvent, Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Loader2, Phone, ShieldCheck, Sparkles } from 'lucide-react';
import { ApiError, api } from '@/lib/api';
import { safeConsumerNextPath, saveAuthSession, validateAuthSession } from '@/lib/auth';

function authErrorMessage(error: unknown, fallback: string) {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 404) {
    return '当前后端未加载登录接口，请重启 8004 后端到最新代码后再试。';
  }
  if (error.message.includes('SMS provider') || error.message.includes('Unsupported SMS provider')) {
    return '短信服务未配置，请联系项目管理员配置短信服务后再登录。';
  }
  if (error.message.includes('Invalid or expired')) {
    return '验证码错误或已过期，请重新获取。';
  }
  return error.message;
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeConsumerNextPath(searchParams.get('next'));
  const [phone, setPhone] = useState('');
  const [nickname, setNickname] = useState('');
  const [code, setCode] = useState('');
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    validateAuthSession().then((user) => {
      if (!active || !user) return;
      setSuccess(next === '/' ? '登录成功，正在进入首页' : '登录成功，正在回到刚才页面');
      window.setTimeout(() => router.replace(next), 600);
    });

    return () => {
      active = false;
    };
  }, [next, router]);

  const requestCode = async () => {
    if (!phone.trim()) {
      setError('请先输入手机号');
      return;
    }
    setSending(true);
    setError(null);
    try {
      const result = await api.requestLoginCode({
        phone: phone.trim(),
        nickname: nickname.trim() || undefined,
        user_type: 'consumer',
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
    setSuccess(null);
    try {
      const result = await api.login({
        phone: phone.trim(),
        code: code.trim(),
        nickname: nickname.trim() || undefined,
        user_type: 'consumer',
      });
      saveAuthSession(result.access_token, result.user);
      setSuccess(next === '/' ? '登录成功，正在进入首页' : '登录成功，正在回到刚才页面');
      window.setTimeout(() => router.replace(next), 600);
    } catch (err) {
      console.error(err);
      setError(authErrorMessage(err, '登录失败，验证码可能已过期'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f7f2eb] text-stone-950">
      <main className="mx-auto min-h-screen max-w-[430px] bg-[#fbf7ef] px-5 py-5 shadow-2xl shadow-stone-200/80">
        <header className="flex items-center justify-between">
          <Link href="/" className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-stone-700 shadow-sm">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">NailMind</p>
          <div className="h-10 w-10" />
        </header>

        <section className="mt-8 overflow-hidden rounded-[2rem] bg-stone-950 p-6 text-amber-50">
          <Sparkles className="mb-5 h-9 w-9 text-amber-200" />
          <h1 className="text-3xl font-bold leading-tight">登录后继续你的 AI 试戴</h1>
          <p className="mt-3 text-sm leading-6 text-amber-100/70">
            手部档案、试戴记录、候选清单和偏好画像都会跟随当前账号保存。
          </p>
        </section>

        <form onSubmit={submit} className="mt-5 rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
          <label className="mb-4 block text-sm font-semibold text-stone-700">
            用户名
            <div className="mt-2 rounded-2xl border border-stone-200 px-4 py-3 focus-within:border-stone-950">
              <input
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                className="w-full outline-none"
                placeholder="请输入用户名"
              />
            </div>
          </label>

          <label className="block text-sm font-semibold text-stone-700">
            手机号
            <div className="mt-2 flex items-center gap-2 rounded-2xl border border-stone-200 px-4 py-3 focus-within:border-stone-950">
              <Phone className="h-4 w-4 text-stone-400" />
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                className="min-w-0 flex-1 outline-none"
                placeholder="请输入手机号"
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

          {debugCode && (
            <p className="mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
              本地开发验证码：{debugCode}
            </p>
          )}
          {error && <p className="mt-3 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          {success && (
            <div className="mt-3 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || Boolean(success) || !phone.trim() || !code.trim()}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-stone-950 py-4 font-semibold text-amber-50 disabled:opacity-40"
          >
            {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <ShieldCheck className="h-5 w-5" />}
            登录并继续
          </button>
        </form>
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#fbf7ef]" />}>
      <LoginContent />
    </Suspense>
  );
}
