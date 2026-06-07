'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { CheckCircle, X } from 'lucide-react';
import { api, type TryOnProgress } from '@/lib/api';
import { getCurrentTryOnId } from '@/lib/tryon-session';

export function TryOnProgressListener() {
  const router = useRouter();
  const pathname = usePathname();
  const [notice, setNotice] = useState<TryOnProgress | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(6);
  const notifiedIds = useRef<Set<number>>(new Set());
  const isConsumerRoute =
    pathname === '/' ||
    pathname.startsWith('/upload') ||
    pathname.startsWith('/tryon') ||
    pathname.startsWith('/designs') ||
    pathname.startsWith('/records') ||
    pathname.startsWith('/candidates') ||
    pathname.startsWith('/compare') ||
    pathname.startsWith('/profile') ||
    pathname.startsWith('/scenes') ||
    pathname.startsWith('/seasonal') ||
    pathname.startsWith('/processing');
  const mutedOnCurrentPage = !isConsumerRoute || pathname === '/processing' || pathname === '/records';

  useEffect(() => {
    try {
      notifiedIds.current = new Set(
        JSON.parse(localStorage.getItem('tryon_notified_ids') || '[]')
          .map((id: string | number) => Number(id))
          .filter(Boolean)
      );
    } catch {
      notifiedIds.current = new Set();
    }
  }, []);

  const markNotified = (tryOnId: number) => {
    notifiedIds.current.add(tryOnId);
    localStorage.setItem('tryon_notified_ids', JSON.stringify(Array.from(notifiedIds.current).slice(-20)));
  };

  useEffect(() => {
    if (mutedOnCurrentPage) {
      return;
    }

    let cancelled = false;

    const pollCurrentTask = async () => {
      const tryOnId = getCurrentTryOnId();

      if (!tryOnId || notifiedIds.current.has(tryOnId)) {
        return;
      }

      try {
        const progress = await api.getTryOnProgress(tryOnId);
        if (cancelled) {
          return;
        }

        if (progress.status === 'completed' && progress.result_image_url) {
          markNotified(tryOnId);
          setNotice(progress);
          setSecondsLeft(6);
        }
      } catch (error) {
        console.error('Failed to poll try-on progress:', error);
      }
    };

    pollCurrentTask();
    const timer = setInterval(pollCurrentTask, 5000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [mutedOnCurrentPage]);

  useEffect(() => {
    if (!notice || mutedOnCurrentPage) {
      return;
    }

    const timer = setInterval(() => {
      setSecondsLeft((current) => {
        if (current <= 1) {
          clearInterval(timer);
          setNotice(null);
          return 0;
        }
        return current - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [notice, mutedOnCurrentPage]);

  if (!notice || mutedOnCurrentPage) {
    return null;
  }

  return (
    <div className="fixed left-4 right-4 bottom-5 z-[70] mx-auto max-w-lg">
      <div className="overflow-hidden rounded-3xl bg-gray-950 text-white shadow-2xl">
        <div
          className="h-1 bg-emerald-400 transition-all duration-1000"
          style={{ width: `${Math.max(0, secondsLeft / 6) * 100}%` }}
        />
        <div className="flex items-center gap-3 p-4">
          <button
            type="button"
            onClick={() => {
              localStorage.setItem('current_try_on_id', notice.try_on_id.toString());
              router.push(`/tryon?id=${notice.try_on_id}`);
              setNotice(null);
            }}
            className="flex flex-1 items-center gap-3 text-left"
          >
            <span className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center">
            <CheckCircle className="w-5 h-5" />
            </span>
            <span className="flex-1">
              <span className="block text-sm font-semibold">试戴结果已生成</span>
              <span className="block text-xs text-white/70 mt-0.5">点击查看本次 AI 试戴效果 · {secondsLeft}s</span>
            </span>
            <span className="text-xs text-white/70">查看</span>
          </button>
          <button
            type="button"
            onClick={() => setNotice(null)}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white/70"
            aria-label="关闭通知"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
