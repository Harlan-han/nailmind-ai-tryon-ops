'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  TrendingUp,
  Heart,
  Eye,
  ChevronRight,
  Sparkles,
  Package,
  Calendar,
  DollarSign,
  Users,
  ArrowRight,
  Star,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { OpsShell } from '@/components/ops-shell';
import { api, type MerchantOverview } from '@/lib/api';

export default function MerchantPage() {
  const [overview, setOverview] = useState<MerchantOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [merchantName, setMerchantName] = useState('美甲工作室');

  useEffect(() => {
    let cancelled = false;

    void Promise.resolve().then(async () => {
      setMerchantName(localStorage.getItem('merchant_name') || '美甲工作室');
      setLoading(true);
      setError(null);
      try {
        const data = await api.getMerchantOverview();
        if (!cancelled) {
          setOverview(data);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('店铺数据加载失败，请确认后端服务已启动并使用运营账号登录。');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const stats = [
    {
      label: '总款式',
      value: overview?.total_designs || 0,
      icon: Package,
      color: 'text-blue-500',
      bgColor: 'bg-blue-50',
    },
    {
      label: '总浏览',
      value: overview?.total_views || 0,
      icon: Eye,
      color: 'text-rose-500',
      bgColor: 'bg-rose-50',
    },
    {
      label: '试戴次数',
      value: overview?.total_try_ons || 0,
      icon: TrendingUp,
      color: 'text-purple-500',
      bgColor: 'bg-purple-50',
    },
    {
      label: '失败试戴',
      value: overview?.failed_try_ons || 0,
      icon: AlertCircle,
      color: 'text-red-500',
      bgColor: 'bg-red-50',
    },
    {
      label: '收藏数',
      value: overview?.total_favorites || 0,
      icon: Heart,
      color: 'text-pink-500',
      bgColor: 'bg-pink-50',
    },
  ];

  return (
    <OpsShell
      title={merchantName}
      subtitle="商家视角查看试戴、收藏、预约和款式表现。"
      eyebrow="Merchant Ops"
      action={
        <Link href="/admin" className="rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50">
          切换到平台运营
        </Link>
      }
    >
      <div className="space-y-6">
        {error && (
          <div className="flex items-center gap-2 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {/* Welcome */}
        <div className="rounded-[2rem] bg-stone-950 p-6 text-amber-50">
          <h2 className="text-xl font-semibold mb-2">欢迎回来，{merchantName}</h2>
          <p className="text-amber-100/70">查看店铺的最新数据和趋势，把试戴意向转成预约跟进。</p>
          <div className="flex gap-4 mt-4">
            <div className="bg-white/20 rounded-lg px-4 py-2">
              <p className="text-2xl font-bold">{overview?.conversion_rate || 0}%</p>
              <p className="text-sm text-rose-100">试戴转化率</p>
            </div>
            <div className="bg-white/20 rounded-lg px-4 py-2">
              <p className="text-2xl font-bold">{overview?.recent_bookings || 0}</p>
              <p className="text-sm text-rose-100">今日预约</p>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-5">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-3xl border border-stone-200 bg-[#fffaf0] p-4 shadow-sm">
              <div className={`w-10 h-10 ${stat.bgColor} rounded-2xl flex items-center justify-center mb-3`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <p className="text-2xl font-bold text-stone-950">{stat.value}</p>
              <p className="text-sm text-stone-500">{stat.label}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Hot Designs */}
          <div className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-orange-500" />
              店铺热门款
            </h2>
            <div className="space-y-3">
              {loading ? (
                <div className="flex items-center gap-2 rounded-2xl border border-dashed border-stone-200 p-4 text-sm text-stone-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在读取店铺款式表现
                </div>
              ) : overview?.hot_designs.length ? (
                overview.hot_designs.map((design, index) => (
                  <div key={design.id} className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-rose-100 text-rose-600 text-xs flex items-center justify-center font-medium">
                      {index + 1}
                    </span>
                    <div className="w-10 h-10 rounded-lg bg-gray-100 overflow-hidden">
                      <img src={design.image_url} alt={design.name} className="w-full h-full object-cover" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{design.name}</p>
                      <p className="text-xs text-gray-500">{design.try_on_count}次试戴</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-stone-200 p-4 text-sm text-stone-500">
                  暂无真实试戴数据。用户完成试戴后，这里会自动按热度排序。
                </div>
              )}
            </div>
            <Link
              href="/admin/designs"
              className="mt-4 flex items-center justify-center gap-1 text-sm text-rose-600 hover:underline"
            >
              查看全部款式
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Quick Actions */}
          <div className="rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-5 shadow-sm">
            <h2 className="font-semibold text-gray-900 mb-4">快捷操作</h2>
            <div className="space-y-2">
              <Link
                href="/admin/designs"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Package className="w-5 h-5 text-blue-500" />
                  <span className="text-sm text-gray-700">管理款式</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </Link>
              <Link
                href="/admin/trends"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-rose-500" />
                  <span className="text-sm text-gray-700">趋势分析</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </Link>
              <Link
                href="/admin/report"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-orange-500" />
                  <span className="text-sm text-gray-700">运营日报</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </Link>
              <Link
                href="/merchant/bookings"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <DollarSign className="w-5 h-5 text-green-500" />
                  <span className="text-sm text-gray-700">预约管理</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </Link>
            </div>
          </div>

          {/* Tips */}
          <div className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-500" />
              经营建议
            </h2>
            <div className="space-y-3 text-sm text-gray-600">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="font-medium text-blue-900 mb-1">上新建议</p>
                <p className="text-blue-700">
                  当前有 {overview?.active_designs || 0} 个在线款式，可结合热门款补齐同风格素材。
                </p>
              </div>
              <div className="p-3 bg-green-50 rounded-lg">
                <p className="font-medium text-green-900 mb-1">转化优化</p>
                <p className="text-green-700">
                  试戴到收藏转化率为 {overview?.conversion_rate || 0}%，优先复盘收藏高但预约少的款式。
                </p>
              </div>
              <div className="p-3 bg-purple-50 rounded-lg">
                <p className="font-medium text-purple-900 mb-1">预约提醒</p>
                <p className="text-purple-700">
                  今日有 {overview?.recent_bookings || 0} 条新预约意向，建议先进入预约管理完成跟进。
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl p-4 border border-gray-100">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-500" />
            最近活动
          </h2>
          <div className="divide-y divide-gray-100">
            {loading ? (
              <div className="flex items-center gap-2 py-4 text-sm text-stone-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                正在读取真实用户行为
              </div>
            ) : overview?.recent_activity.length ? (
              overview.recent_activity.map((activity) => (
                <div key={activity.event_key} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-rose-400 rounded-full" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                      <p className="text-xs text-gray-500">{activity.detail}</p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400">{activity.time}</span>
                </div>
              ))
            ) : (
              <div className="py-4 text-sm text-stone-500">
                暂无真实活动。用户试戴、收藏或提交预约后会出现在这里。
              </div>
            )}
          </div>
        </div>
      </div>
    </OpsShell>
  );
}
