'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, Calendar, Loader2, Filter } from 'lucide-react';
import { api } from '@/lib/api';
import { OpsShell } from '@/components/ops-shell';

interface DailyStat {
  date: string;
  try_ons: number;
  unique_users: number;
}

interface TrendsData {
  period: string;
  daily_stats: DailyStat[];
  style_distribution: Record<string, number>;
  color_distribution: Record<string, number>;
}

interface FunnelStage {
  name: string;
  count: number;
  conversion_rate: number;
}

interface FunnelData {
  period_days: number;
  stages: FunnelStage[];
  overall_conversion: number;
}

export default function TrendsPage() {
  const [period, setPeriod] = useState(7);
  const [data, setData] = useState<TrendsData | null>(null);
  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    await Promise.resolve();
    setLoading(true);
    try {
      const [trendsResult, funnelResult] = await Promise.all([
        api.getTrends(period),
        api.getFunnel(period).catch(() => null),
      ]);
      setData(trendsResult);
      setFunnel(funnelResult);
    } catch (error) {
      console.error('Failed to load trends:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadData);
  }, [period]);

  const maxTryOns = data?.daily_stats?.length
    ? Math.max(...data.daily_stats.map((d) => d.try_ons), 1)
    : 1;

  const sortedStyles = data?.style_distribution
    ? Object.entries(data.style_distribution)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
    : [];

  const maxStyleCount = sortedStyles.length ? sortedStyles[0][1] : 1;

  const funnelColors = ['bg-blue-500', 'bg-indigo-500', 'bg-purple-500', 'bg-rose-500'];

  return (
    <OpsShell
      title="趋势分析"
      subtitle="查看试戴、风格和转化漏斗趋势，辅助推荐位和上新判断。"
    >
      <div className="space-y-6">
        {/* Period Selector */}
        <div className="flex items-center gap-4">
          <Calendar className="w-5 h-5 text-gray-500" />
          <div className="flex gap-2">
            {[7, 14, 30].map((days) => (
              <button
                key={days}
                onClick={() => setPeriod(days)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  period === days
                    ? 'bg-rose-500 text-white'
                    : 'bg-white text-gray-600 border border-gray-200 hover:border-rose-300'
                }`}
              >
                近{days}天
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20">
            <Loader2 className="w-8 h-8 text-rose-400 mx-auto animate-spin" />
            <p className="mt-4 text-gray-500">加载趋势数据...</p>
          </div>
        ) : (
          <>
            {/* Conversion Funnel */}
            {funnel && funnel.stages.length > 0 && (
              <div className="bg-white rounded-xl p-6 border border-gray-100">
                <div className="flex items-center gap-2 mb-4">
                  <Filter className="w-5 h-5 text-rose-500" />
                  <h2 className="font-semibold text-gray-900">转化漏斗</h2>
                  <span className="text-sm text-gray-500 ml-2">
                    近{period}天整体转化率 {funnel.overall_conversion}%
                  </span>
                </div>
                <div className="flex items-center gap-0">
                  {funnel.stages.map((stage, index) => (
                    <div key={stage.name} className="flex-1 flex flex-col items-center">
                      <div
                        className={`w-full ${funnelColors[index]} text-white rounded-lg p-4 text-center transition-all`}
                        style={{
                          opacity: 1 - index * 0.15,
                        }}
                      >
                        <p className="text-2xl font-bold">{stage.count}</p>
                        <p className="text-sm opacity-90">{stage.name}</p>
                      </div>
                      {index < funnel.stages.length - 1 && (
                        <div className="flex items-center justify-center w-full py-2">
                          <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                            转化 {stage.conversion_rate}%
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Daily Stats Bar Chart */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <h2 className="font-semibold text-gray-900 mb-4">试戴量趋势</h2>
              {data?.daily_stats && data.daily_stats.length > 0 ? (
                <div className="space-y-3">
                  <div className="flex items-end gap-2 h-48">
                    {data.daily_stats.map((stat) => (
                      <div key={stat.date} className="flex-1 flex flex-col items-center gap-1">
                        <span className="text-xs text-gray-500">{stat.try_ons}</span>
                        <div
                          className="w-full bg-rose-400 rounded-t-md min-h-[4px] transition-all"
                          style={{
                            height: `${(stat.try_ons / maxTryOns) * 160}px`,
                          }}
                        />
                        <span className="text-xs text-gray-400">
                          {stat.date.slice(5)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-400">近{period}天暂无试戴数据</p>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-6">
              {/* Style Distribution */}
              <div className="bg-white rounded-xl p-6 border border-gray-100">
                <h2 className="font-semibold text-gray-900 mb-4">风格分布</h2>
                {sortedStyles.length > 0 ? (
                  <div className="space-y-3">
                    {sortedStyles.map(([style, count]) => (
                      <div key={style} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-700">{style}</span>
                          <span className="text-gray-500">{count}次</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2">
                          <div
                            className="bg-rose-500 h-2 rounded-full transition-all"
                            style={{ width: `${(count / maxStyleCount) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
                    <p className="text-gray-400">暂无风格数据</p>
                  </div>
                )}
              </div>

              {/* Color Distribution */}
              <div className="bg-white rounded-xl p-6 border border-gray-100">
                <h2 className="font-semibold text-gray-900 mb-4">颜色分布</h2>
                {data?.color_distribution && Object.keys(data.color_distribution).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(data.color_distribution)
                      .sort((a, b) => b[1] - a[1])
                      .slice(0, 10)
                      .map(([color, count]) => (
                        <div key={color} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-700">{color}</span>
                            <span className="text-gray-500">{count}次</span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-2">
                            <div
                              className="bg-pink-500 h-2 rounded-full transition-all"
                              style={{
                                width: `${(count / Math.max(...Object.values(data.color_distribution))) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                  </div>
                ) : (
                  <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
                    <p className="text-gray-400">暂无颜色数据</p>
                  </div>
                )}
              </div>
            </div>

            {/* Style Trend Table */}
            <div className="bg-white rounded-xl border border-gray-100">
              <div className="p-4 border-b border-gray-100">
                <h2 className="font-semibold text-gray-900">风格趋势排行</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {sortedStyles.length > 0 ? (
                  sortedStyles.map(([style, count], index) => (
                    <div key={style} className="flex items-center gap-4 p-4">
                      <span className="w-8 h-8 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center font-medium text-sm">
                        {index + 1}
                      </span>
                      <span className="flex-1 font-medium text-gray-900">{style}</span>
                      <TrendingUp className="w-4 h-4 text-green-500" />
                      <span className="text-sm text-gray-600">{count}次试戴</span>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-400">
                    近{period}天暂无风格趋势数据
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </OpsShell>
  );
}
