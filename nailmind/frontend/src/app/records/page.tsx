'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, History, Eye, CheckCircle } from 'lucide-react';
import { api, type TryOnProgress, type TryOnRecord } from '@/lib/api';
import { useValidatedUser } from '@/lib/use-validated-user';
import { MobileShell } from '@/components/mobile-shell';

export default function RecordsPage() {
  const router = useRouter();
  const [records, setRecords] = useState<TryOnRecord[]>([]);
  const [progressById, setProgressById] = useState<Record<number, TryOnProgress>>({});
  const [completionNotice, setCompletionNotice] = useState<TryOnProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const { user, checking } = useValidatedUser('/records');
  const notifiedCompletionIds = useRef<Set<number>>(new Set());

  useEffect(() => {
    const processingRecords = records.filter((record) =>
      ['pending', 'processing'].includes(record.status)
    );

    if (processingRecords.length === 0) {
      return;
    }

    let cancelled = false;

    const refreshProgress = async () => {
      const progressList = await Promise.all(
        processingRecords.map((record) =>
          api.getTryOnProgress(record.id).catch(() => null)
        )
      );

      if (cancelled) {
        return;
      }

      const validProgress = progressList.filter(Boolean) as TryOnProgress[];
      const justCompleted = validProgress.find((progress) =>
        progress.status === 'completed' &&
        !notifiedCompletionIds.current.has(progress.try_on_id)
      );

      if (justCompleted) {
        notifiedCompletionIds.current.add(justCompleted.try_on_id);
        setCompletionNotice(justCompleted);
      }

      setProgressById((prev) => {
        const next = { ...prev };
        validProgress.forEach((progress) => {
          next[progress.try_on_id] = progress;
        });
        return next;
      });
    };

    refreshProgress();
    const timer = setInterval(refreshProgress, 5000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [records]);

  async function loadRecords() {
    await Promise.resolve();
    setLoading(true);
    try {
      const data = await api.getMyTryOns();
      setRecords(data);
    } catch (error) {
      console.error('Failed to load records:', error);
      setRecords([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!user) return;
    void Promise.resolve().then(loadRecords);
  }, [user]);

  const handleRecordClick = (record: TryOnRecord) => {
    if (record.status === 'failed' || record.status === 'fallback_completed') {
      router.push(`/tryon?design=${record.nail_design_id}`);
      return;
    }

    localStorage.setItem('current_try_on_id', record.id.toString());
    router.push(`/tryon?id=${record.id}`);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusLabel = (status: TryOnRecord['status']) => {
    if (status === 'completed') {
      return { text: '已完成', className: 'bg-green-50 text-green-700' };
    }
    if (status === 'fallback_completed') {
      return { text: '失败', className: 'bg-red-50 text-red-700' };
    }
    if (status === 'failed') {
      return { text: '失败', className: 'bg-red-50 text-red-700' };
    }
    return { text: '生成中', className: 'bg-blue-50 text-blue-700' };
  };

  return (
    <MobileShell>
      <header className="sticky top-0 z-50 border-b border-stone-200/70 bg-[#fbf7ef]/85 backdrop-blur-2xl">
        <div className="px-5 h-14 flex items-center">
          <Link href="/" className="flex items-center text-gray-600 hover:text-rose-600">
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回
          </Link>
          <h1 className="flex-1 text-center font-semibold text-gray-900">我的记录</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="px-5 py-4">
        <div className="mb-6 rounded-[2rem] bg-stone-950 p-5 text-amber-50">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/10">
              <History className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-lg font-bold">试戴记录</h2>
              <p className="mt-1 text-sm leading-6 text-amber-100/70">
                这里只保留生成历史。想对比或决策的款式统一放到“候选清单”。
              </p>
            </div>
          </div>
        </div>

        {loading || checking ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl p-4 border border-gray-100 animate-pulse">
                <div className="flex gap-4">
                  <div className="w-24 h-24 rounded-lg bg-gray-200 shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/2" />
                    <div className="h-3 bg-gray-200 rounded w-1/3" />
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : records.length === 0 ? (
          <div className="text-center py-20">
            <History className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">暂无试戴记录</p>
            <Link href="/designs" className="text-rose-600 text-sm mt-2 inline-block">
              去选择模板
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {records.map((record) => {
              const progress = progressById[record.id];
              const visibleStatus = progress?.status || record.status;
              const status = getStatusLabel(visibleStatus);
              const isProcessing = ['pending', 'processing'].includes(visibleStatus);
              const displayImage =
                visibleStatus === 'completed'
                  ? record.result_image_url || record.nail_design?.image_url || ''
                  : record.nail_design?.image_url || '';
              return (
                <div
                  key={record.id}
                  onClick={() => handleRecordClick(record)}
                  className="bg-white rounded-xl p-4 border border-gray-100 cursor-pointer hover:border-rose-200 transition-colors"
                >
                  <div className="flex gap-4">
                    <div className="w-24 h-24 rounded-lg bg-gray-100 overflow-hidden shrink-0">
                      <img
                        src={displayImage}
                        alt={record.nail_design?.name || '试戴记录'}
                        className="w-full h-full object-cover"
                      />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-semibold text-gray-900 truncate">
                            {record.nail_design?.name || '试戴记录'}
                          </h3>
                          <p className="text-xs text-gray-500 mt-1">
                            {formatDate(record.created_at)}
                          </p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${status.className}`}>
                          {status.text}
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-1 mt-2">
                        {record.nail_design?.style_tags?.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>

                      {isProcessing && progress && (
                        <div className="mt-3 rounded-xl bg-blue-50 p-3">
                          <div className="flex items-center justify-between text-xs text-blue-700">
                            <span>{progress.message}</span>
                            <span className="font-semibold">{progress.progress}%</span>
                          </div>
                          <div className="mt-2 h-2 rounded-full bg-blue-100 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-blue-500 transition-all duration-500"
                              style={{ width: `${progress.progress}%` }}
                            />
                          </div>
                        </div>
                      )}

                      <div className="flex gap-2 mt-3 items-center">
                        <span className="text-xs text-gray-400 flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          点击查看
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {completionNotice && (
        <div className="fixed left-4 right-4 bottom-5 z-[60] mx-auto max-w-lg">
          <button
            onClick={() => {
              localStorage.setItem('current_try_on_id', completionNotice.try_on_id.toString());
              router.push(`/tryon?id=${completionNotice.try_on_id}`);
            }}
            className="w-full rounded-3xl bg-gray-950 p-4 text-left text-white shadow-2xl"
          >
            <div className="flex items-center gap-3">
              <span className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center">
                <CheckCircle className="w-5 h-5" />
              </span>
              <span className="flex-1">
                <span className="block text-sm font-semibold">试戴结果已生成</span>
                <span className="block text-xs text-white/70 mt-0.5">点击查看本次 AI 试戴效果</span>
              </span>
              <span className="text-xs text-white/70">查看</span>
            </div>
          </button>
        </div>
      )}
    </MobileShell>
  );
}
