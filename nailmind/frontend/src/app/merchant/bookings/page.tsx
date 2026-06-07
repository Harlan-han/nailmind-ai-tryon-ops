'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowUpRight,
  Calendar,
  CheckCircle,
  Clock,
  Filter,
  ImageIcon,
  Loader2,
  MessageCircle,
  Phone,
  Search,
  User,
  UserCheck,
  XCircle,
} from 'lucide-react';
import { OpsShell, OpsStatCard } from '@/components/ops-shell';
import { api, type BookingIntent } from '@/lib/api';

type BookingStatus = BookingIntent['status'];

const statusMeta: Record<BookingStatus, { label: string; helper: string; tone: string; dot: string }> = {
  pending: {
    label: '待确认',
    helper: '需要首次联系',
    tone: 'bg-amber-50 text-amber-800 border-amber-100',
    dot: 'bg-amber-500',
  },
  contacted: {
    label: '已联系',
    helper: '等待确认到店',
    tone: 'bg-sky-50 text-sky-700 border-sky-100',
    dot: 'bg-sky-500',
  },
  confirmed: {
    label: '已确认',
    helper: '准备服务承接',
    tone: 'bg-blue-50 text-blue-700 border-blue-100',
    dot: 'bg-blue-500',
  },
  completed: {
    label: '已完成',
    helper: '形成转化贡献',
    tone: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    dot: 'bg-emerald-500',
  },
  cancelled: {
    label: '已取消',
    helper: '保留复盘线索',
    tone: 'bg-stone-100 text-stone-600 border-stone-200',
    dot: 'bg-stone-400',
  },
};

const statusFilters: Array<'all' | BookingStatus> = ['pending', 'contacted', 'confirmed', 'completed', 'cancelled', 'all'];
const statusPriority: Record<BookingStatus, number> = {
  pending: 0,
  contacted: 1,
  confirmed: 2,
  completed: 3,
  cancelled: 4,
};

export default function MerchantBookingsPage() {
  const [bookings, setBookings] = useState<BookingIntent[]>([]);
  const [filter, setFilter] = useState<'all' | BookingStatus>('pending');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completionHint, setCompletionHint] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  async function loadBookings() {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const data = await api.getBookingIntents();
      setBookings(data);
    } catch (err) {
      console.error(err);
      setError('预约数据加载失败，请确认后端服务已启动。');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadBookings);
  }, []);

  const filteredBookings = bookings.filter((booking) => {
    const keyword = searchQuery.trim();
    const matchesFilter = filter === 'all' || booking.status === filter;
    const matchesSearch =
      !keyword ||
      booking.user_name.includes(keyword) ||
      booking.design_name.includes(keyword) ||
      booking.phone.includes(keyword);
    return matchesFilter && matchesSearch;
  });

  const priorityBookings = [...filteredBookings].sort((a, b) => {
    const priorityDiff = statusPriority[a.status] - statusPriority[b.status];
    if (priorityDiff !== 0) return priorityDiff;
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
  });

  const statusCounts = bookings.reduce<Record<BookingStatus, number>>(
    (acc, booking) => {
      acc[booking.status] += 1;
      return acc;
    },
    { pending: 0, contacted: 0, confirmed: 0, completed: 0, cancelled: 0 }
  );

  const activeCount = statusCounts.pending + statusCounts.contacted + statusCounts.confirmed;
  const completionRate = bookings.length > 0 ? Math.round((statusCounts.completed / bookings.length) * 100) : 0;

  const handleStatusChange = async (bookingId: number, newStatus: BookingStatus) => {
    setError(null);
    setCompletionHint(null);
    setUpdatingId(bookingId);
    try {
      const updated = await api.updateBookingIntentStatus(bookingId, newStatus);
      setBookings((current) =>
        current.map((booking) => (booking.id === bookingId ? updated : booking))
      );
    } catch (err) {
      console.error(err);
      setError('状态更新失败，请稍后重试。');
    } finally {
      setUpdatingId(null);
    }
  };

  const advanceToCompleted = async (booking: BookingIntent) => {
    const steps: BookingStatus[] =
      booking.status === 'pending'
        ? ['contacted', 'confirmed', 'completed']
        : booking.status === 'contacted'
          ? ['confirmed', 'completed']
          : booking.status === 'confirmed'
            ? ['completed']
            : [];

    if (!steps.length) return;

    setError(null);
    setCompletionHint(null);
    setUpdatingId(booking.id);
    try {
      let updated = booking;
      for (const status of steps) {
        updated = await api.updateBookingIntentStatus(booking.id, status);
      }
      setBookings((current) => current.map((item) => (item.id === booking.id ? updated : item)));
      setCompletionHint(`${booking.user_name} 的预约已按联系、确认、完成流程归档。`);
    } catch (err) {
      console.error(err);
      setError('完成预约失败，请确认当前状态仍在可跟进流程内。');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleCompleteClick = (booking: BookingIntent) => {
    if (booking.status === 'completed') {
      setCompletionHint('这条预约已经完成，无需重复操作。');
      return;
    }
    if (booking.status === 'cancelled') {
      setCompletionHint('已取消的预约不能标记完成，请重新创建预约意向。');
      return;
    }
    if (booking.status !== 'confirmed') {
      setCompletionHint('系统会先补齐“已联系”和“已确认”，再标记完成，保证运营记录不跳步。');
    }
    void advanceToCompleted(booking);
  };

  const getNextStep = (status: BookingStatus): { label: string; status: BookingStatus; icon: typeof MessageCircle } | null => {
    if (status === 'pending') return { label: '标记已联系', status: 'contacted', icon: MessageCircle };
    if (status === 'contacted') return { label: '确认到店', status: 'confirmed', icon: UserCheck };
    if (status === 'confirmed') return { label: '标记完成', status: 'completed', icon: CheckCircle };
    return null;
  };

  const formatDate = (value: string | null) => {
    if (!value) return '待沟通时间';
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <OpsShell
      title="预约跟进"
      subtitle="把 AI 试戴带来的预约意向转成可跟进、可复盘的商家动作。"
      action={
        <Link
          href="/admin/assistant"
          className="inline-flex items-center gap-2 rounded-full bg-stone-950 px-4 py-2 text-sm font-semibold text-amber-50 shadow-sm"
        >
          问 Agent
          <ArrowUpRight className="h-4 w-4" />
        </Link>
      }
    >
      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <OpsStatCard label="全部预约" value={bookings.length} helper="来自试戴结果页" tone="bg-[#fffaf0]" />
        <OpsStatCard label="待处理" value={activeCount} helper="需要门店动作" tone="bg-amber-50" />
        <OpsStatCard label="已确认" value={statusCounts.confirmed} helper="进入到店准备" tone="bg-blue-50" />
        <OpsStatCard label="完成率" value={`${completionRate}%`} helper={`${statusCounts.completed} 条已完成`} tone="bg-emerald-50" />
      </section>

      <section className="mb-6 rounded-[2rem] border border-stone-200 bg-stone-950 p-5 text-amber-50 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-100/50">Agent-readable signals</p>
            <h2 className="mt-2 text-xl font-bold">今天优先处理 {activeCount} 条预约线索</h2>
            <p className="mt-1 text-sm text-amber-100/70">
              这些数据会被运营 Agent 读取，用于回答“哪些客户要先跟进”“哪些试戴图带来了预约转化”。
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 rounded-3xl bg-white/10 p-2 text-center text-xs text-amber-100/70 sm:min-w-80">
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-lg font-bold text-amber-50">{statusCounts.pending}</p>
              <p>待确认</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-lg font-bold text-amber-50">{statusCounts.contacted}</p>
              <p>已联系</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-lg font-bold text-amber-50">{statusCounts.completed}</p>
              <p>已完成</p>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-5 shadow-sm">
        <div className="mb-5 flex flex-col gap-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-xl font-bold">跟进队列</h2>
              <p className="mt-1 text-sm text-stone-500">按紧急程度排序，从待确认、已联系、已确认到完成复盘。</p>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索姓名、手机号或款式"
                className="w-full rounded-2xl border border-stone-200 bg-white py-3 pl-9 pr-4 text-sm outline-none focus:border-stone-950 sm:w-72"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {statusFilters.map((item) => {
              const active = filter === item;
              const label = item === 'all' ? '全部' : statusMeta[item].label;
              const count = item === 'all' ? bookings.length : statusCounts[item];
              return (
                <button
                  key={item}
                  type="button"
                  onClick={() => setFilter(item)}
                  className={
                    active
                      ? 'shrink-0 rounded-full bg-stone-950 px-4 py-2 text-sm font-semibold text-amber-50'
                      : 'shrink-0 rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-600'
                  }
                >
                  {label} {count}
                </button>
              );
            })}
            <div className="ml-auto hidden items-center gap-2 text-xs text-stone-400 md:flex">
              <Filter className="h-4 w-4 text-stone-500" />
              当前筛选 {filter === 'all' ? '全部状态' : statusMeta[filter].label}
            </div>
          </div>
        </div>

        {error && <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {completionHint && <p className="mb-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{completionHint}</p>}

        {loading ? (
          <div className="flex items-center justify-center rounded-3xl border border-dashed border-stone-300 p-10 text-stone-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            正在加载预约队列
          </div>
        ) : priorityBookings.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-stone-300 p-10 text-center text-stone-500">
            <Calendar className="mx-auto mb-4 h-12 w-12 text-stone-300" />
            当前筛选下暂无预约。用户在试戴结果页提交后会出现在这里。
          </div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {priorityBookings.map((booking) => {
              const meta = statusMeta[booking.status];
              const nextStep = getNextStep(booking.status);
              const NextIcon = nextStep?.icon;
              const canComplete = booking.status !== 'completed' && booking.status !== 'cancelled';
              const canCancel = booking.status !== 'completed' && booking.status !== 'cancelled';
              return (
                <article key={booking.id} className="rounded-3xl border border-stone-200 bg-white p-4 shadow-sm">
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <div className="flex gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-950 text-amber-50">
                        <User className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-bold text-stone-950">{booking.user_name}</h3>
                        <p className="mt-1 flex items-center gap-1 text-sm text-stone-500">
                          <Phone className="h-4 w-4" />
                          {booking.phone}
                        </p>
                      </div>
                    </div>
                    <span className={`rounded-full border px-3 py-1 text-xs font-medium ${meta.tone}`}>
                      {meta.label}
                    </span>
                  </div>

                  <div className="grid gap-3 rounded-2xl bg-stone-50 p-3 sm:grid-cols-[160px_1fr]">
                    <div className="grid grid-cols-2 gap-2">
                      <PreviewImage src={booking.try_on_result_image_url} label="试戴图" />
                      <PreviewImage src={booking.design_image_url} label="原款式" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                        <p className="text-xs font-semibold text-stone-400">{meta.helper}</p>
                      </div>
                      <p className="mt-2 text-lg font-bold text-stone-950">{booking.design_name}</p>
                      <p className="mt-2 flex items-center gap-2 text-sm text-stone-500">
                        <Clock className="h-4 w-4" />
                        期望时间：{formatDate(booking.preferred_date)}
                      </p>
                      <p className="mt-1 text-xs text-stone-400">
                        线索来源：试戴记录 #{booking.try_on_record_id} · 预约 #{booking.id}
                      </p>
                      {booking.notes && <p className="mt-2 rounded-2xl bg-white px-3 py-2 text-sm text-stone-600">备注：{booking.notes}</p>}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_1fr_1fr]">
                    {nextStep && NextIcon ? (
                      <button
                        type="button"
                        disabled={updatingId === booking.id}
                        onClick={() => handleStatusChange(booking.id, nextStep.status)}
                        className="flex items-center justify-center gap-2 rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50 disabled:opacity-60"
                      >
                        <NextIcon className="h-4 w-4" />
                        {updatingId === booking.id ? '更新中' : nextStep.label}
                      </button>
                    ) : (
                      <a
                        href={`tel:${booking.phone}`}
                        className="flex items-center justify-center gap-2 rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50"
                      >
                        <Phone className="h-4 w-4" />
                        联系客户
                      </a>
                    )}
                    <button
                      type="button"
                      disabled={updatingId === booking.id || !canComplete}
                      onClick={() => handleCompleteClick(booking)}
                      className="flex items-center justify-center gap-2 rounded-2xl bg-emerald-50 py-3 text-sm font-medium text-emerald-700 disabled:opacity-40"
                    >
                      <CheckCircle className="h-4 w-4" />
                      完成
                    </button>
                    <button
                      type="button"
                      disabled={updatingId === booking.id || !canCancel}
                      onClick={() => handleStatusChange(booking.id, 'cancelled')}
                      className="flex items-center justify-center gap-2 rounded-2xl bg-stone-100 py-3 text-sm font-medium text-stone-600 disabled:opacity-40"
                    >
                      <XCircle className="h-4 w-4" />
                      取消
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </OpsShell>
  );
}

function PreviewImage({ src, label }: { src: string | null; label: string }) {
  return (
    <div className="relative aspect-[3/4] overflow-hidden rounded-2xl bg-white">
      {src ? (
        <img src={src} alt={label} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-stone-300">
          <ImageIcon className="h-6 w-6" />
        </div>
      )}
      <span className="absolute bottom-1.5 left-1.5 rounded-full bg-stone-950/75 px-2 py-1 text-[10px] font-semibold text-amber-50 backdrop-blur">
        {label}
      </span>
    </div>
  );
}
