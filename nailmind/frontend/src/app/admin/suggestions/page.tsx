'use client';

import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Filter,
  Lightbulb,
  Loader2,
  Sparkles,
  Star,
  TrendingUp,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';
import { OpsShell } from '@/components/ops-shell';

interface Suggestion {
  id: string;
  type: 'hot' | 'cold' | 'new' | 'promo' | 'agent';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  target: string;
  reason: string;
  expected_impact: string;
  risk?: string | null;
  source?: string;
  status: 'pending' | 'accepted' | 'rejected' | 'completed';
  created_at: string;
}

type SuggestionApiItem = Suggestion & {
  created_at?: string | null;
};

type SuggestionFilter = 'all' | 'pending' | 'accepted' | 'completed' | 'agent';

const typeMeta = {
  hot: { label: '爆款推广', icon: TrendingUp, tone: 'bg-rose-50 text-rose-700 border-rose-100' },
  cold: { label: '冷门调整', icon: AlertTriangle, tone: 'bg-amber-50 text-amber-800 border-amber-100' },
  new: { label: '上新建议', icon: Star, tone: 'bg-blue-50 text-blue-700 border-blue-100' },
  promo: { label: '活动建议', icon: Sparkles, tone: 'bg-purple-50 text-purple-700 border-purple-100' },
  agent: { label: '运营 Agent', icon: Lightbulb, tone: 'bg-emerald-50 text-emerald-700 border-emerald-100' },
};

const priorityLabel = {
  high: '高优先级',
  medium: '中优先级',
  low: '低优先级',
};

export default function SuggestionsPage() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<SuggestionFilter>('pending');
  const [lastAppliedAction, setLastAppliedAction] = useState<string | null>(null);

  async function loadSuggestions() {
    await Promise.resolve();
    setLoading(true);
    try {
      const data = await api.getSuggestions();
      setSuggestions(
        (data as SuggestionApiItem[]).map((item) => ({
          ...item,
          created_at: item.created_at?.split('T')[0] || '',
        }))
      );
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadSuggestions);
  }, []);

  const handleAccept = async (id: string) => {
    const result = await api.acceptSuggestion(id);
    setSuggestions((current) =>
      current.map((item) => (item.id === id ? { ...item, status: 'accepted' } : item))
    );
    const actionMessage = {
      promote_hot_design: '已应用：该款式已进入用户端热门推荐',
      demote_hot_design: '已应用：该款式已移出用户端热门推荐',
      status_only: '已采纳：该建议已进入人工执行记录',
    }[result.applied_action];
    setLastAppliedAction(actionMessage);
  };

  const handleReject = async (id: string) => {
    await api.rejectSuggestion(id);
    setSuggestions((current) =>
      current.map((item) => (item.id === id ? { ...item, status: 'rejected' } : item))
    );
  };

  const filteredSuggestions = suggestions.filter((item) => {
    if (filter === 'all') return true;
    if (filter === 'pending') return item.status === 'pending';
    if (filter === 'accepted') return item.status === 'accepted';
    if (filter === 'completed') return item.status === 'completed';
    return item.type === 'agent';
  });

  const counts = {
    pending: suggestions.filter((item) => item.status === 'pending').length,
    accepted: suggestions.filter((item) => item.status === 'accepted').length,
    completed: suggestions.filter((item) => item.status === 'completed').length,
    agent: suggestions.filter((item) => item.type === 'agent').length,
  };

  return (
    <OpsShell
      title="建议中心"
      subtitle="承接 Agent 和规则系统输出，形成可审核、可追踪的运营决策队列。"
    >
      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <StatFilterCard label="待处理建议" value={counts.pending} helper="今天优先清空" active={filter === 'pending'} onClick={() => setFilter('pending')} />
        <StatFilterCard label="已采纳" value={counts.accepted} helper="进入执行跟踪" active={filter === 'accepted'} onClick={() => setFilter('accepted')} />
        <StatFilterCard label="已完成" value={counts.completed} helper="形成运营复盘" active={filter === 'completed'} onClick={() => setFilter('completed')} />
        <StatFilterCard label="Agent 生成" value={counts.agent} helper="来自对话助手" active={filter === 'agent'} onClick={() => setFilter('agent')} tone="bg-emerald-50" />
      </section>

      {lastAppliedAction && (
        <div className="mb-4 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
          {lastAppliedAction}
        </div>
      )}

      <section className="rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-5 shadow-sm">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl font-bold">决策队列</h2>
            <p className="mt-1 text-sm text-stone-500">每条建议都包含原因、预期影响和风险，避免只看一句结论。</p>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-stone-500" />
            {(['all', 'pending', 'accepted', 'completed', 'agent'] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                className={
                  filter === item
                    ? 'rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50'
                    : 'rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-600'
                }
              >
                {item === 'all' ? '全部' : item === 'pending' ? '待处理' : item === 'accepted' ? '已采纳' : item === 'completed' ? '已完成' : 'Agent 生成'}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-stone-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            正在加载建议
          </div>
        ) : filteredSuggestions.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-stone-300 p-10 text-center text-stone-500">
            <Lightbulb className="mx-auto mb-4 h-12 w-12 text-stone-300" />
            当前筛选下暂无建议
          </div>
        ) : (
          <div className="space-y-3">
            {filteredSuggestions.map((suggestion) => {
              const meta = typeMeta[suggestion.type] || typeMeta.agent;
              const Icon = meta.icon;

              return (
                <article key={suggestion.id} className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex gap-4">
                      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border ${meta.tone}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <span className={`rounded-full border px-3 py-1 text-xs font-medium ${meta.tone}`}>
                            {meta.label}
                          </span>
                          <span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-600">
                            {priorityLabel[suggestion.priority]}
                          </span>
                          <span className="flex items-center gap-1 text-xs text-stone-400">
                            <Clock className="h-3.5 w-3.5" />
                            {suggestion.created_at}
                          </span>
                        </div>
                        <h3 className="text-lg font-bold text-stone-950">{suggestion.title}</h3>
                        <p className="mt-2 text-sm leading-6 text-stone-600">{suggestion.description}</p>
                      </div>
                    </div>

                    {suggestion.status === 'pending' ? (
                      <div className="flex shrink-0 gap-2">
                        <button
                          type="button"
                          onClick={() => handleReject(suggestion.id)}
                          className="flex items-center gap-2 rounded-full border border-stone-200 px-4 py-2 text-sm text-stone-600"
                        >
                          <X className="h-4 w-4" />
                          忽略
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAccept(suggestion.id)}
                          className="flex items-center gap-2 rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50"
                        >
                          <CheckCircle className="h-4 w-4" />
                          采纳
                        </button>
                      </div>
                    ) : (
                      <span className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
                        {suggestion.status === 'accepted' ? '已采纳' : suggestion.status === 'completed' ? '已完成' : '已忽略'}
                      </span>
                    )}
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div className="rounded-2xl bg-stone-50 p-4">
                      <p className="text-xs font-semibold text-stone-400">为什么推荐</p>
                      <p className="mt-1 text-sm leading-6 text-stone-700">{suggestion.reason}</p>
                    </div>
                    <div className="rounded-2xl bg-emerald-50 p-4">
                      <p className="text-xs font-semibold text-emerald-600">预期影响</p>
                      <p className="mt-1 text-sm leading-6 text-emerald-800">{suggestion.expected_impact}</p>
                    </div>
                    <div className="rounded-2xl bg-amber-50 p-4">
                      <p className="text-xs font-semibold text-amber-600">风险提醒</p>
                      <p className="mt-1 text-sm leading-6 text-amber-900">{suggestion.risk || '风险较低，建议小流量验证。'}</p>
                    </div>
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

function StatFilterCard({
  label,
  value,
  helper,
  active,
  onClick,
  tone = 'bg-white',
}: {
  label: string;
  value: string | number;
  helper: string;
  active: boolean;
  onClick: () => void;
  tone?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-3xl border p-4 text-left shadow-sm transition ${
        active
          ? 'border-stone-950 bg-stone-950 text-amber-50'
          : `border-stone-200 ${tone} text-stone-950 hover:-translate-y-0.5 hover:border-stone-400`
      }`}
    >
      <p className={active ? 'text-2xl font-bold text-amber-50' : 'text-2xl font-bold text-stone-950'}>{value}</p>
      <p className={active ? 'mt-1 text-sm text-amber-100/80' : 'mt-1 text-sm text-stone-500'}>{label}</p>
      <p className={active ? 'mt-3 text-xs text-amber-100/60' : 'mt-3 text-xs text-stone-400'}>{helper}</p>
    </button>
  );
}
