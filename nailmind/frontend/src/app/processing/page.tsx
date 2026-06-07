'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Sparkles, Loader2, Clock, CheckCircle, AlertCircle, X } from 'lucide-react';
import { api, type TryOnProgress } from '@/lib/api';
import { getCurrentTryOnId, getTryOnStartedAt, resetFailedTryOnForRetry } from '@/lib/tryon-session';
import { MobileShell } from '@/components/mobile-shell';

interface ProcessingState {
  status: 'pending' | 'processing' | 'completed' | 'fallback_completed' | 'failed';
  progress: number;
  message: string;
  resultUrl?: string;
  error?: string;
}

const isFinished = (status: ProcessingState['status']) =>
  status === 'completed';

const formatTryOnErrorMessage = (message?: string | null) => {
  if (!message) return undefined;
  if (message.includes('All connection attempts failed')) {
    return 'AI 生成服务暂时不可用，请稍后重试';
  }
  if (message.includes('RUNNINGHUB_API_KEY') || message.includes('RunningHub try-on generation')) {
    return 'AI 生成通道尚未完成配置，请联系现场工作人员检查 RunningHub 密钥';
  }
  return message;
};

const buildPresetProgress = (elapsedSeconds: number) => {
  if (elapsedSeconds < 2) return 4 + elapsedSeconds * 5;
  if (elapsedSeconds < 8) return 14 + (elapsedSeconds - 2) * 5.5;
  if (elapsedSeconds < 18) return 47 + (elapsedSeconds - 8) * 3.2;
  if (elapsedSeconds < 30) return 79 + (elapsedSeconds - 18) * 1.65;
  return 99;
};

const buildPresetMessage = (elapsedSeconds: number) => {
  if (elapsedSeconds < 8) return '正在读取手照和款式参考，准备提交 AI 生成';
  if (elapsedSeconds < 18) return 'AI 正在做款式迁移和指甲区域融合';
  if (elapsedSeconds < 30) return '正在优化细节，结果完成后会立即展示';
  if (elapsedSeconds < 90) return '正在等待 AI 生成通道返回高清试戴结果，完成后会自动展示';
  return '生成队列比平时更慢，任务仍在后台继续，请不要重复提交';
};

export default function ProcessingPage() {
  const router = useRouter();
  const [tryOnId, setTryOnId] = useState<number | null>(null);
  const [completionNotice, setCompletionNotice] = useState<TryOnProgress | null>(null);
  const [noticeSecondsLeft, setNoticeSecondsLeft] = useState(6);
  const [state, setState] = useState<ProcessingState>({
    status: 'pending',
    progress: 0,
    message: '准备开始试戴...',
  });
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    void Promise.resolve().then(() => {
      const storedTryOnId = getCurrentTryOnId();
      if (cancelled) {
        return;
      }

      if (!storedTryOnId) {
        setState({
          status: 'failed',
          progress: 0,
          message: '没有找到正在进行的试戴任务',
          error: '请先选择款式并开始试戴',
        });
        return;
      }

      setTryOnId(storedTryOnId);
      setStartedAt(getTryOnStartedAt(storedTryOnId));
      const poll = async () => {
        try {
          const progress = await api.getTryOnProgress(storedTryOnId);
          if (cancelled) {
            return;
          }

          if (isFinished(progress.status) && progress.result_image_url) {
            setCompletionNotice(progress);
            setNoticeSecondsLeft(6);
            router.replace(`/tryon?id=${storedTryOnId}`);
            return;
          }

          if (progress.status === 'failed') {
            setElapsedTime(progress.elapsed_seconds);
            setState((current) => ({
              ...current,
              status: progress.status,
              progress: 100,
              message: progress.message,
              resultUrl: progress.result_image_url || undefined,
              error: formatTryOnErrorMessage(progress.error_message),
            }));
            return;
          }

          setTimeout(poll, 2000);
        } catch (error) {
          console.error('Polling error:', error);
          if (!cancelled) {
            setTimeout(poll, 2000);
          }
        }
      };

      void poll();
    });

    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (state.status !== 'pending' && state.status !== 'processing') {
        clearInterval(timer);
        return;
      }
      if (!startedAt) {
        return;
      }
      const elapsedSeconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
      setElapsedTime(elapsedSeconds);
      setState((current) => {
        if (current.status !== 'pending' && current.status !== 'processing') {
          return current;
        }
        return {
          ...current,
          status: 'processing',
          progress: Math.min(99, Math.floor(buildPresetProgress(elapsedSeconds))),
          message: buildPresetMessage(elapsedSeconds),
        };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [startedAt, state.status]);

  useEffect(() => {
    if (!completionNotice) {
      return;
    }

    const timer = setInterval(() => {
      setNoticeSecondsLeft((current) => {
        if (current <= 1) {
          clearInterval(timer);
          setCompletionNotice(null);
          return 0;
        }
        return current - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [completionNotice]);

  const handleRetry = async () => {
    if (!tryOnId) return;
    try {
      const failedTryOn = await api.getTryOn(tryOnId);
      resetFailedTryOnForRetry(failedTryOn);
      router.push(`/tryon?design=${failedTryOn.nail_design_id}`);
    } catch (error) {
      console.error('Failed to prepare retry:', error);
      router.push('/records');
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <MobileShell>
      <header className="sticky top-0 z-50 border-b border-stone-200/70 bg-[#fbf7ef]/85 backdrop-blur-2xl">
        <div className="px-5 h-14 flex items-center">
          <button
            onClick={() => router.push('/')}
            className="flex items-center text-gray-600 hover:text-rose-600"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回
          </button>
          <h1 className="flex-1 text-center font-semibold text-gray-900">试戴生成中</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="px-5 py-12">
        <div className="text-center space-y-8">
          <div className="relative">
            <div className="w-24 h-24 mx-auto bg-rose-100 rounded-full flex items-center justify-center">
              {state.status === 'processing' && (
                <Sparkles className="w-12 h-12 text-rose-500 animate-pulse" />
              )}
              {state.status === 'completed' && (
                <CheckCircle className="w-12 h-12 text-green-500" />
              )}
              {state.status === 'failed' && (
                <AlertCircle className="w-12 h-12 text-red-500" />
              )}
            </div>
            {state.status === 'processing' && (
              <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
                <Loader2 className="w-6 h-6 text-rose-400 animate-spin" />
              </div>
            )}
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-gray-900">
              {state.status === 'processing' && 'AI 正在生成试戴效果'}
              {state.status === 'completed' && '试戴效果已生成'}
              {state.status === 'failed' && '试戴生成失败'}
            </h2>
            <p className="text-gray-600">{state.message}</p>
          </div>

          {state.status === 'processing' && (
            <div className="space-y-3">
            <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-[linear-gradient(110deg,#fb7185,#f43f5e,#fbbf24,#fb7185)] bg-[length:220%_100%] transition-all duration-700 animate-pulse"
                  style={{ width: `${Math.max(1, state.progress)}%` }}
                />
              </div>
              <p className="text-sm text-gray-500">{state.progress}% 完成</p>
            </div>
          )}

          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <Clock className="w-4 h-4" />
            <span>已用时 {formatTime(elapsedTime)}</span>
          </div>

          {state.error && (
            <div className="bg-red-50 border border-red-100 rounded-xl p-4">
              <p className="text-red-600">{state.error}</p>
            </div>
          )}

          <div className="space-y-3 pt-4">
            {state.status === 'failed' && (
              <button
                onClick={handleRetry}
                className="w-full bg-rose-500 text-white py-3 rounded-xl font-medium hover:bg-rose-600 transition-colors"
              >
                重试
              </button>
            )}
            {state.status === 'processing' && (
              <>
                <button
                  onClick={() => router.push('/')}
                  className="w-full border border-gray-300 text-gray-700 py-3 rounded-xl font-medium hover:bg-gray-50 transition-colors"
                >
                  先继续浏览模板，稍后再回来
                </button>
                <p className="text-sm text-gray-500">
                  任务会继续生成，不会因为离开页面而中断。
                </p>
              </>
            )}
            {state.status === 'completed' && tryOnId && (
              <Link
                href={`/tryon?id=${tryOnId}`}
                className="w-full bg-rose-500 text-white py-3 rounded-xl font-medium hover:bg-rose-600 transition-colors flex items-center justify-center gap-2"
              >
                查看结果
                <ArrowLeft className="w-4 h-4 rotate-180" />
              </Link>
            )}
          </div>

          {state.status === 'processing' && (
            <div className="bg-white rounded-xl p-4 border border-rose-100 mt-8">
              <h3 className="font-medium text-gray-900 mb-2">试戴小贴士</h3>
              <ul className="text-sm text-gray-600 space-y-1 text-left">
                <li>• 生成时间通常约 1-2 分钟，取决于第三方队列状态</li>
                <li>• 你可以先去继续选款或查看记录</li>
                <li>• 结果会自动保存到“我的记录”</li>
                <li>• 如果主通道失败，会明确提示失败，不再用低质兜底图误导结果</li>
              </ul>
            </div>
          )}
        </div>
      </main>

      {completionNotice && tryOnId && (
        <div className="fixed inset-0 z-[60] bg-black/30 px-5 flex items-end sm:items-center justify-center">
          <div className="w-full max-w-sm overflow-hidden rounded-3xl bg-white shadow-2xl mb-6 sm:mb-0">
            <div
              className="h-1 bg-emerald-500 transition-all duration-1000"
              style={{ width: `${Math.max(0, noticeSecondsLeft / 6) * 100}%` }}
            />
            <div className="p-5">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div className="w-12 h-12 rounded-full bg-green-50 text-green-600 flex items-center justify-center">
                  <CheckCircle className="w-7 h-7" />
                </div>
                <button
                  type="button"
                  onClick={() => setCompletionNotice(null)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-stone-100 text-stone-500"
                  aria-label="关闭通知"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <h2 className="text-lg font-semibold text-gray-950">试戴结果已生成</h2>
              <p className="text-sm text-gray-600 mt-2">{completionNotice.message}</p>
              <p className="mt-2 text-xs text-stone-400">{noticeSecondsLeft} 秒后自动收起</p>
              <div className="grid grid-cols-2 gap-3 mt-5">
                <button
                  onClick={() => setCompletionNotice(null)}
                  className="rounded-2xl border border-gray-200 py-3 text-sm font-medium text-gray-700"
                >
                  先不看
                </button>
                <button
                  onClick={() => router.push(`/tryon?id=${tryOnId}`)}
                  className="rounded-2xl bg-gray-950 py-3 text-sm font-medium text-white"
                >
                  查看结果
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </MobileShell>
  );
}
