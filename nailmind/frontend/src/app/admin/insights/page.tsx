'use client';

import { useEffect, useState } from 'react';
import {
  Brain,
  TrendingUp,
  AlertTriangle,
  Sparkles,
  Package,
  Target,
  ChevronRight,
  Loader2,
  LineChart,
  Zap
} from 'lucide-react';
import { api } from '@/lib/api';
import { OpsImage } from '@/components/ops-image';
import { OpsShell } from '@/components/ops-shell';

interface PredictionData {
  trend_direction: string;
  slope: number;
  predictions: number[];
  confidence: number;
  average_last_7_days: number;
  prediction_next_7_days: number;
}

interface EmergingStyle {
  style: string;
  try_ons: number;
  favorites: number;
  unique_users: number;
  growth_rate: number;
  favorite_rate: number;
  is_emerging: boolean;
}

interface InventoryItem {
  design_id: number;
  design_name: string;
  image_url: string;
  status: string;
  action: string;
  reason: string;
  metrics: {
    try_ons: number;
    favorites: number;
    bookings: number;
    favorite_rate: number;
    booking_rate: number;
  };
}

interface Anomaly {
  date: string;
  value: number;
  expected: number;
  z_score: number;
  type: string;
  severity: string;
}

interface ActionItem {
  action: string;
  reason: string;
  priority: string;
}

interface ActionPlan {
  generated_at: string;
  summary: string;
  immediate_actions: ActionItem[];
  short_term: ActionItem[];
  long_term: ActionItem[];
}

interface AIInsightsData {
  predictions: PredictionData;
  emerging_styles: EmergingStyle[];
  inventory_recommendations: InventoryItem[];
  anomalies: Anomaly[];
  action_plan: ActionPlan;
}

export default function InsightsPage() {
  const [insights, setInsights] = useState<AIInsightsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadInsights();
  }, []);

  async function loadInsights() {
    try {
      setLoading(true);
      const data = await api.getAIInsights();
      setInsights(data);
    } catch (err) {
      setError('加载 AI 洞察失败，请稍后重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'up':
        return <TrendingUp className="w-5 h-5 text-green-500" />;
      case 'down':
        return <TrendingUp className="w-5 h-5 text-red-500 rotate-180" />;
      default:
        return <LineChart className="w-5 h-5 text-gray-500" />;
    }
  };

  const getTrendColor = (direction: string) => {
    switch (direction) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-50 border-red-200 text-red-700';
      case 'medium':
        return 'bg-yellow-50 border-yellow-200 text-yellow-700';
      default:
        return 'bg-blue-50 border-blue-200 text-blue-700';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-700';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700';
      default:
        return 'bg-green-100 text-green-700';
    }
  };

  if (loading) {
    return (
      <OpsShell title="AI 智能洞察" subtitle="预测趋势、异常、库存建议和行动计划。">
        <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-stone-200 bg-white">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-8 h-8 text-stone-950 animate-spin" />
            <p className="text-gray-600">AI 正在分析数据...</p>
          </div>
        </div>
      </OpsShell>
    );
  }

  if (error) {
    return (
      <OpsShell title="AI 智能洞察" subtitle="预测趋势、异常、库存建议和行动计划。">
        <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-stone-200 bg-white">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={loadInsights}
              className="px-4 py-2 bg-stone-950 text-amber-50 rounded-lg hover:bg-stone-800 transition-colors"
            >
              重新加载
            </button>
          </div>
        </div>
      </OpsShell>
    );
  }

  return (
    <OpsShell
      title="AI 智能洞察"
      subtitle="预测趋势、异常、库存建议和行动计划。"
      eyebrow="NailMind Intelligence"
      action={
        <button
          type="button"
          onClick={loadInsights}
          className="rounded-2xl bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-sm"
        >
          刷新洞察
        </button>
      }
    >
      <div className="space-y-6">
        {/* Summary Card */}
        {insights?.action_plan?.summary && (
          <div className="bg-gradient-to-r from-purple-500 to-rose-500 rounded-xl p-6 text-white">
            <div className="flex items-center gap-3 mb-2">
              <Sparkles className="w-5 h-5" />
              <h2 className="font-semibold">AI 运营总结</h2>
            </div>
            <p className="text-lg">{insights.action_plan.summary}</p>
            <p className="text-sm text-white/70 mt-2">
              生成时间: {new Date(insights.action_plan.generated_at).toLocaleString('zh-CN')}
            </p>
          </div>
        )}

        {/* Top Stats Grid */}
        <div className="grid grid-cols-4 gap-4">
          {/* Trend Prediction */}
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">趋势预测</p>
                <p className={`font-semibold ${getTrendColor(insights?.predictions?.trend_direction || '')}`}>
                  {insights?.predictions?.trend_direction === 'up' && '上升'}
                  {insights?.predictions?.trend_direction === 'down' && '下降'}
                  {insights?.predictions?.trend_direction === 'stable' && '稳定'}
                  {insights?.predictions?.trend_direction === 'insufficient_data' && '数据不足'}
                </p>
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-gray-600">
                未来7天预测: <span className="font-medium">{insights?.predictions?.prediction_next_7_days?.toFixed(0)} 次/天</span>
              </p>
              <p className="text-sm text-gray-600">
                置信度: <span className="font-medium">{((insights?.predictions?.confidence || 0) * 100).toFixed(0)}%</span>
              </p>
            </div>
          </div>

          {/* Emerging Styles Count */}
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">新兴风格</p>
                <p className="font-semibold text-gray-900">
                  {insights?.emerging_styles?.filter(s => s.is_emerging).length || 0} 个
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              近14天增长趋势明显且收藏转化良好的风格
            </p>
          </div>

          {/* Inventory Alerts */}
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-10 h-10 bg-orange-50 rounded-lg flex items-center justify-center">
                <Package className="w-5 h-5 text-orange-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">库存建议</p>
                <p className="font-semibold text-gray-900">
                  {insights?.inventory_recommendations?.filter(i => i.status === 'high_demand').length || 0} 款需关注
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              高需求款式建议确保库存充足
            </p>
          </div>

          {/* Anomalies */}
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">异常检测</p>
                <p className="font-semibold text-gray-900">
                  {insights?.anomalies?.length || 0} 个异常
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              数据波动超过2个标准差的异常点
            </p>
          </div>
        </div>

        {/* Predictions Chart */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <LineChart className="w-5 h-5 text-blue-500" />
              未来7天试戴量预测
            </h2>
            <span className="text-sm text-gray-500">
              基于过去30天数据
            </span>
          </div>
          {insights?.predictions?.predictions ? (
            <div className="space-y-3">
              <div className="flex items-end gap-2 h-32">
                {insights.predictions.predictions.map((value, index) => (
                  <div key={index} className="flex-1 flex flex-col items-center gap-2">
                    <div
                      className="w-full bg-gradient-to-t from-blue-500 to-blue-300 rounded-t-lg transition-all hover:from-blue-600 hover:to-blue-400"
                      style={{
                        height: `${Math.max(20, (value / Math.max(...insights.predictions.predictions)) * 100)}%`,
                        minHeight: '20px'
                      }}
                    />
                    <span className="text-xs text-gray-500">D{index + 1}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-between text-sm text-gray-600 pt-2 border-t border-gray-100">
                <span>平均预测: {insights.predictions.prediction_next_7_days.toFixed(1)} 次/天</span>
                <span className={getTrendColor(insights.predictions.trend_direction)}>
                  趋势: {insights.predictions.trend_direction === 'up' ? '↗ 上升' :
                    insights.predictions.trend_direction === 'down' ? '↘ 下降' : '→ 平稳'}
                </span>
              </div>
            </div>
          ) : (
            <div className="h-32 bg-gray-50 rounded-lg flex items-center justify-center">
              <p className="text-gray-400">数据不足，无法生成预测</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Emerging Styles */}
          <div className="bg-white rounded-xl border border-gray-100">
            <div className="p-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-green-500" />
                新兴风格识别
              </h2>
            </div>
            <div className="divide-y divide-gray-100">
              {insights?.emerging_styles?.slice(0, 5).map((style, index) => (
                <div key={style.style} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center font-medium text-sm">
                        {index + 1}
                      </span>
                      <div>
                        <p className="font-medium text-gray-900">{style.style}</p>
                        <p className="text-xs text-gray-500">
                          试戴 {style.try_ons} · 收藏 {style.favorites}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-green-600">
                        +{(style.growth_rate * 100).toFixed(0)}%
                      </p>
                      <p className="text-xs text-gray-500">
                        收藏率 {(style.favorite_rate * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>
                </div>
              ))}
              {!insights?.emerging_styles?.length && (
                <div className="p-8 text-center text-gray-400">
                  暂无新兴风格数据
                </div>
              )}
            </div>
          </div>

          {/* Anomalies */}
          <div className="bg-white rounded-xl border border-gray-100">
            <div className="p-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                异常检测提醒
              </h2>
            </div>
            <div className="divide-y divide-gray-100">
              {insights?.anomalies?.map((anomaly, index) => (
                <div key={index} className={`p-4 ${getSeverityColor(anomaly.severity)}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">
                          {anomaly.type === 'spike' ? '📈 数据突增' : '📉 数据下降'}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${anomaly.severity === 'high' ? 'bg-red-200 text-red-800' : 'bg-yellow-200 text-yellow-800'}`}>
                          {anomaly.severity === 'high' ? '严重' : '中等'}
                        </span>
                      </div>
                      <p className="text-sm opacity-90">
                        {anomaly.date}: {anomaly.value} 次 (预期 {anomaly.expected} 次)
                      </p>
                      <p className="text-xs opacity-70 mt-1">
                        偏离 {anomaly.z_score > 0 ? '+' : ''}{anomaly.z_score.toFixed(1)}σ
                      </p>
                    </div>
                  </div>
                </div>
              ))}
              {!insights?.anomalies?.length && (
                <div className="p-8 text-center text-gray-400">
                  近7天数据正常，无异常波动
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Inventory Recommendations */}
        <div className="bg-white rounded-xl border border-gray-100">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Package className="w-5 h-5 text-orange-500" />
              库存管理建议
            </h2>
          </div>
          <div className="divide-y divide-gray-100">
            {insights?.inventory_recommendations?.slice(0, 5).map((item) => (
              <div key={item.design_id} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-4">
                  <OpsImage
                    src={item.image_url}
                    alt={item.design_name}
                    className="w-16 h-16 rounded-lg object-cover"
                    fallbackLabel="库存款图缺失"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium text-gray-900">{item.design_name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        item.status === 'high_demand'
                          ? 'bg-red-100 text-red-700'
                          : item.status === 'potential'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {item.action === 'ensure_stock' ? '确保库存' :
                         item.action === 'promote' ? '加推' : 'Review'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{item.reason}</p>
                    <div className="flex gap-4 mt-2 text-xs text-gray-500">
                      <span>试戴 {item.metrics.try_ons}</span>
                      <span>收藏率 {(item.metrics.favorite_rate * 100).toFixed(0)}%</span>
                      <span>预约率 {(item.metrics.booking_rate * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {!insights?.inventory_recommendations?.length && (
              <div className="p-8 text-center text-gray-400">
                暂无库存建议
              </div>
            )}
          </div>
        </div>

        {/* Action Plan */}
        <div className="bg-white rounded-xl border border-gray-100">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-500" />
              智能行动计划
            </h2>
          </div>
          <div className="p-4 space-y-4">
            {/* Immediate Actions */}
            {insights?.action_plan?.immediate_actions && insights.action_plan.immediate_actions.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-red-500" />
                  立即行动
                </h3>
                <div className="space-y-2">
                  {insights.action_plan.immediate_actions.map((action, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
                      <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${getPriorityColor(action.priority)}`}>
                        {action.priority === 'high' ? '高' : '中'}
                      </span>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{action.action}</p>
                        <p className="text-sm text-gray-600 mt-1">{action.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Short Term */}
            {insights?.action_plan?.short_term && insights.action_plan.short_term.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-3">短期计划 (本周)</h3>
                <div className="space-y-2">
                  {insights.action_plan.short_term.map((action, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg">
                      <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${getPriorityColor(action.priority)}`}>
                        {action.priority === 'high' ? '高' : '中'}
                      </span>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{action.action}</p>
                        <p className="text-sm text-gray-600 mt-1">{action.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {((!insights?.action_plan?.immediate_actions || insights.action_plan.immediate_actions.length === 0) &&
             (!insights?.action_plan?.short_term || insights.action_plan.short_term.length === 0)) && (
              <div className="text-center text-gray-400 py-8">
                暂无行动计划
              </div>
            )}
          </div>
        </div>
      </div>
    </OpsShell>
  );
}
