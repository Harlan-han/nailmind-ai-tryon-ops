'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  Bot,
  Calendar,
  ChevronRight,
  ClipboardCheck,
  Heart,
  LayoutGrid,
  Phone,
  Settings,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { api, TodayWorkbench, type ConsumerAssistantInsights } from '@/lib/api';
import { OpsShell } from '@/components/ops-shell';

const cardStyle = {
  booking_followup: {
    icon: Phone,
    label: '预约跟进',
    tone: 'bg-blue-50 text-blue-700 border-blue-100',
  },
  conversion_gap: {
    icon: AlertTriangle,
    label: '转化修复',
    tone: 'bg-amber-50 text-amber-800 border-amber-100',
  },
  suggestion_review: {
    icon: ClipboardCheck,
    label: '建议审核',
    tone: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  },
};

const priorityLabel: Record<string, string> = {
  high: '高优先级',
  medium: '中优先级',
  low: '低优先级',
};

export default function AdminPage() {
  const [workbench, setWorkbench] = useState<TodayWorkbench | null>(null);
  const [assistantInsights, setAssistantInsights] = useState<ConsumerAssistantInsights | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTodayWorkbench().then(setWorkbench).catch((err) => {
      console.error(err);
      setError('今日工作台暂时不可用，请检查后端服务是否已重启。');
    });
    api.getConsumerAssistantInsights().then(setAssistantInsights).catch((err) => {
      console.error(err);
    });
  }, []);

  const summary = workbench?.summary;
  const stats = [
    { label: '今日试戴', value: summary?.today_try_ons || 0, icon: TrendingUp, tone: 'bg-rose-50 text-rose-600' },
    { label: '今日收藏', value: summary?.today_favorites || 0, icon: Heart, tone: 'bg-pink-50 text-pink-600' },
    { label: '预约意向', value: summary?.today_booking_intents || 0, icon: Phone, tone: 'bg-blue-50 text-blue-600' },
    { label: '待处理建议', value: summary?.pending_suggestion_count || 0, icon: ClipboardCheck, tone: 'bg-emerald-50 text-emerald-600' },
  ];

  const quickLinks = [
    { href: '/admin/assistant', label: '运营 Agent', icon: Bot },
    { href: '/merchant/bookings', label: '预约跟进', icon: Calendar },
    { href: '/admin/suggestions', label: '建议中心', icon: ClipboardCheck },
    { href: '/admin/designs', label: '款式管理', icon: LayoutGrid },
    { href: '/admin/trends', label: '趋势分析', icon: TrendingUp },
    { href: '/admin/settings', label: '配置中心', icon: Settings },
  ];

  return (
    <OpsShell
      title="今日运营工作台"
      subtitle="把试戴、收藏、预约和 Agent 建议压缩成今天要做的行动。"
      action={
        <Link
          href="/admin/assistant"
          className="rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50 transition hover:bg-stone-800"
        >
          打开运营 Agent
        </Link>
      }
    >
        <section className="mb-6 overflow-hidden rounded-[2rem] bg-stone-950 text-amber-50 shadow-sm">
          <div className="grid gap-6 p-6 lg:grid-cols-[1.3fr_0.7fr]">
            <div>
              <p className="mb-3 text-sm text-amber-100/70">今天先做什么</p>
              <h2 className="max-w-2xl text-3xl font-bold leading-tight">
                先跟进预约，再修复试戴到预约的断层，最后审核 Agent 建议。
              </h2>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-amber-100/70">
                这里把用户试戴、收藏、预约意向和运营建议压成可执行待办，帮助商家看清 AI 试戴如何带来真实转化。
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-3xl bg-white/10 p-4">
                <p className="text-3xl font-bold">{summary?.pending_booking_count || 0}</p>
                <p className="mt-1 text-sm text-amber-100/70">待跟进预约</p>
              </div>
              <div className="rounded-3xl bg-white/10 p-4">
                <p className="text-3xl font-bold">{summary?.conversion_gap_count || 0}</p>
                <p className="mt-1 text-sm text-amber-100/70">转化断层款</p>
              </div>
            </div>
          </div>
        </section>

        {error && <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

        <section className="mb-6 grid gap-4 md:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-3xl border border-stone-200 bg-[#fffaf0] p-4 shadow-sm">
              <div className={`mb-4 flex h-11 w-11 items-center justify-center rounded-2xl ${stat.tone}`}>
                <stat.icon className="h-5 w-5" />
              </div>
              <p className="text-2xl font-bold">{stat.value}</p>
              <p className="text-sm text-stone-500">{stat.label}</p>
            </div>
          ))}
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.45fr_0.75fr]">
          <section className="rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-5 shadow-sm">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">今日行动卡</h2>
                <p className="mt-1 text-sm text-stone-500">从预约、转化断层和建议中心自动汇总</p>
              </div>
              <Link href="/admin/assistant" className="text-sm font-medium text-stone-700 hover:text-stone-950">
                让 Agent 继续分析
              </Link>
            </div>

            <div className="space-y-3">
              {workbench?.action_cards?.length ? (
                workbench.action_cards.map((card) => {
                  const meta = cardStyle[card.type];
                  const Icon = meta.icon;
                  return (
                    <Link
                      key={card.id}
                      href={card.target_url}
                      className="block rounded-3xl border border-stone-200 bg-white p-4 transition hover:-translate-y-0.5 hover:shadow-md"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex gap-3">
                          <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border ${meta.tone}`}>
                            <Icon className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="mb-2 flex flex-wrap items-center gap-2">
                              <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${meta.tone}`}>
                                {meta.label}
                              </span>
                              <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-600">
                                {priorityLabel[card.priority] || card.priority}
                              </span>
                            </div>
                            <h3 className="font-semibold text-stone-950">{card.title}</h3>
                            <p className="mt-1 text-sm leading-6 text-stone-600">{card.description}</p>
                            <p className="mt-2 text-sm font-medium text-stone-900">{card.metric}</p>
                          </div>
                        </div>
                        <ChevronRight className="mt-2 h-5 w-5 shrink-0 text-stone-400" />
                      </div>
                    </Link>
                  );
                })
              ) : (
                <div className="rounded-3xl border border-dashed border-stone-300 p-8 text-center text-stone-500">
                  暂无待办。完成新的试戴、收藏或预约后，这里会自动生成行动卡。
                </div>
              )}
            </div>
          </section>

          <aside className="space-y-6">
            <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold">用户助手洞察</h2>
                  <p className="mt-1 text-sm text-stone-500">小甲灵对话沉淀的选款信号</p>
                </div>
                <Bot className="h-5 w-5 text-stone-400" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-stone-50 p-3">
                  <p className="text-2xl font-bold">{assistantInsights?.total_messages || 0}</p>
                  <p className="text-xs text-stone-500">咨询数</p>
                </div>
                <div className="rounded-2xl bg-stone-50 p-3">
                  <p className="text-2xl font-bold">{assistantInsights?.active_users || 0}</p>
                  <p className="text-xs text-stone-500">活跃用户</p>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {(assistantInsights?.top_intents || []).slice(0, 3).map((item) => (
                  <div key={item.name} className="flex items-center justify-between rounded-2xl bg-[#fffaf0] px-3 py-2 text-sm">
                    <span className="text-stone-700">{item.name}</span>
                    <span className="font-bold text-stone-950">{item.count}</span>
                  </div>
                ))}
                {!assistantInsights?.top_intents?.length && (
                  <p className="rounded-2xl bg-stone-50 px-3 py-3 text-sm text-stone-500">用户和小甲灵对话后，这里会显示显白、通勤、约会等偏好信号。</p>
                )}
              </div>
              {assistantInsights?.recent_messages?.[0] && (
                <div className="mt-4 rounded-2xl border border-stone-100 p-3 text-sm text-stone-600">
                  <p className="font-semibold text-stone-950">{assistantInsights.recent_messages[0].user_name}</p>
                  <p className="mt-1 line-clamp-2">{assistantInsights.recent_messages[0].message}</p>
                </div>
              )}
            </section>

            <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 font-bold">热门风格趋势</h2>
              <div className="space-y-3">
                {workbench?.trending_styles?.slice(0, 5).map((style, index) => (
                  <div key={style.style} className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-rose-100 text-xs font-bold text-rose-600">
                      {index + 1}
                    </span>
                    <span className="flex-1 text-sm text-stone-700">{style.style}</span>
                    <span className="text-sm text-stone-500">{style.count}次</span>
                  </div>
                )) || <p className="text-sm text-stone-400">暂无数据</p>}
              </div>
            </section>

            <section className="rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-5 shadow-sm">
              <h2 className="mb-4 font-bold">快捷入口</h2>
              <div className="space-y-2">
                {quickLinks.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="flex items-center justify-between rounded-2xl px-3 py-3 text-sm transition hover:bg-white"
                  >
                    <span className="flex items-center gap-3 text-stone-700">
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </span>
                    <ChevronRight className="h-4 w-4 text-stone-400" />
                  </Link>
                ))}
              </div>
            </section>

            <section className="rounded-[2rem] border border-amber-200 bg-amber-50 p-5">
              <div className="mb-3 flex items-center gap-2 font-bold text-amber-900">
                <Sparkles className="h-5 w-5" />
                商业化闭环雏形
              </div>
              <p className="text-sm leading-6 text-amber-800">
                暂不做支付，先追踪“试戴 → 收藏 → 预约意向 → 商家跟进”。当预约跟进和推荐贡献稳定后，再接交易闭环更稳。
              </p>
            </section>
          </aside>
        </div>
    </OpsShell>
  );
}
