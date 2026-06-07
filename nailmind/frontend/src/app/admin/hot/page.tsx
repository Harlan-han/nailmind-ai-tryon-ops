'use client';

import { useEffect, useState } from 'react';
import { Award, Eye, Flame, Loader2, Rocket, Star, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import { OpsShell, OpsStatCard } from '@/components/ops-shell';

interface HotCandidate {
  design: {
    id: number;
    name: string;
    image_url: string;
    try_on_count: number;
    favorite_count: number;
  };
  recent_try_ons: number;
  previous_try_ons: number;
  growth_rate: number;
  reason: string;
}

type TabType = 'candidates' | 'rising' | 'stable';

export default function HotCandidatesPage() {
  const [candidates, setCandidates] = useState<HotCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('candidates');

  async function loadCandidates() {
    await Promise.resolve();
    setLoading(true);
    try {
      const data = await api.getHotCandidates();
      setCandidates(data);
    } catch (error) {
      console.error('Failed to load hot candidates:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadCandidates);
  }, []);

  const filtered = candidates
    .filter((candidate) => {
      if (activeTab === 'rising') {
        return candidate.growth_rate > 0.5 && candidate.recent_try_ons >= 5;
      }
      if (activeTab === 'stable') {
        return candidate.design.try_on_count >= 20;
      }
      return true;
    })
    .sort((a, b) => b.growth_rate - a.growth_rate);

  const tabs = [
    { id: 'candidates' as TabType, label: '潜力爆款', icon: Flame },
    { id: 'rising' as TabType, label: '增速榜', icon: Rocket },
    { id: 'stable' as TabType, label: '稳定热门', icon: Award },
  ];

  const topGrowth = candidates[0]?.growth_rate ? `${(candidates[0].growth_rate * 100).toFixed(0)}%` : '0%';

  return (
    <OpsShell
      title="爆款候选"
      subtitle="优先识别值得加推的款式，减少运营靠感觉选品。"
    >
      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <OpsStatCard label="候选款式" value={candidates.length} helper="按增长和试戴热度排序" tone="bg-[#fffaf0]" />
        <OpsStatCard label="最高增速" value={topGrowth} helper="近周期试戴增长" tone="bg-white" />
        <OpsStatCard label="稳定热门" value={candidates.filter((item) => item.design.try_on_count >= 20).length} helper="总试戴已验证" tone="bg-white" />
        <OpsStatCard label="推荐动作" value="加推 / 复核" helper="先做推荐位验证" tone="bg-amber-50" />
      </section>

      <section className="rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-5 shadow-sm">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl font-bold">款式行动列表</h2>
            <p className="mt-1 text-sm text-stone-500">从“为什么热”到“是否加推”放在同一张卡里判断。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={
                  activeTab === tab.id
                    ? 'flex items-center gap-2 rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50'
                    : 'flex items-center gap-2 rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-600'
                }
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-stone-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            加载爆款候选
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-stone-300 p-10 text-center text-stone-500">
            <Star className="mx-auto mb-4 h-12 w-12 text-stone-300" />
            暂无符合该分类的款式
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((candidate, index) => (
              <article key={candidate.design.id} className="overflow-hidden rounded-3xl border border-stone-200 bg-white shadow-sm">
                <div className="relative aspect-[4/3] bg-stone-100">
                  <img src={candidate.design.image_url} alt={candidate.design.name} className="h-full w-full object-cover" />
                  <span className="absolute left-3 top-3 rounded-full bg-stone-950 px-3 py-1 text-xs font-bold text-amber-50">
                    #{index + 1}
                  </span>
                </div>
                <div className="p-4">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-stone-950">{candidate.design.name}</h3>
                      <p className="mt-1 text-sm text-stone-500">近周期 {candidate.recent_try_ons} 次试戴</p>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
                      +{(candidate.growth_rate * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="mb-3 grid grid-cols-2 gap-2 text-sm">
                    <div className="rounded-2xl bg-stone-50 p-3">
                      <Eye className="mb-1 h-4 w-4 text-stone-400" />
                      <p className="font-semibold text-stone-950">{candidate.design.try_on_count}</p>
                      <p className="text-xs text-stone-500">总试戴</p>
                    </div>
                    <div className="rounded-2xl bg-stone-50 p-3">
                      <Star className="mb-1 h-4 w-4 text-amber-500" />
                      <p className="font-semibold text-stone-950">{candidate.design.favorite_count}</p>
                      <p className="text-xs text-stone-500">收藏</p>
                    </div>
                  </div>

                  <p className="rounded-2xl bg-amber-50 p-3 text-sm leading-6 text-amber-900">{candidate.reason}</p>
                  <button className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50">
                    <TrendingUp className="h-4 w-4" />
                    加入推荐位观察
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </OpsShell>
  );
}
