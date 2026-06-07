'use client';

import { useEffect, useState } from 'react';
import { Calendar, Sparkles, Plus, Edit2, Trash2, Check, X, Gift, Clock } from 'lucide-react';
import { api } from '@/lib/api';
import { OpsShell, OpsStatCard } from '@/components/ops-shell';

interface SeasonalTheme {
  id: string;
  name: string;
  description: string;
  icon: string;
  keywords: string[];
  colors: string[];
  start_date: string;
  end_date: string;
  is_active: boolean;
  designs_count: number;
}

interface FestivalTheme {
  id: string;
  name: string;
  description: string;
  icon: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  match_rules: {
    style_tags: string[];
    color_tags: string[];
    scene_tags: string[];
  };
  designs_count: number;
}

type ThemeItem = SeasonalTheme | FestivalTheme;

export default function SeasonalAdminPage() {
  const [seasons, setSeasons] = useState<SeasonalTheme[]>([]);
  const [festivals, setFestivals] = useState<FestivalTheme[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'seasons' | 'festivals'>('seasons');
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<ThemeItem | null>(null);

  async function loadData() {
    await Promise.resolve();
    setLoading(true);
    try {
      const themes = await api.getAllThemes();
      setSeasons(themes.seasons || []);
      setFestivals(themes.festivals || []);
    } catch (error) {
      console.error('Failed to load themes:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadData);
  }, []);

  const handleCreate = () => {
    setEditingItem(null);
    setShowModal(true);
  };

  const handleEdit = (item: ThemeItem) => {
    setEditingItem(item);
    setShowModal(true);
  };

  const toggleActive = async (item: ThemeItem, type: 'season' | 'festival') => {
    try {
      // In real implementation, this would call API
      if (type === 'season') {
        setSeasons(prev => prev.map(s =>
          s.id === item.id ? { ...s, is_active: !s.is_active } : s
        ));
      } else {
        setFestivals(prev => prev.map(f =>
          f.id === item.id ? { ...f, is_active: !f.is_active } : f
        ));
      }
    } catch (error) {
      console.error('Failed to toggle status:', error);
    }
  };

  const getDaysUntil = (dateStr: string) => {
    const target = new Date(dateStr);
    const today = new Date();
    const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    return diff;
  };

  return (
    <OpsShell
      title="节日专题管理"
      subtitle="管理季节、节日活动和推荐规则，统一影响 C 端专题展示与款式分发。"
      action={
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 rounded-2xl bg-stone-950 px-4 py-2 text-sm font-semibold text-amber-50"
        >
          <Plus className="w-4 h-4" />
          新建专题
        </button>
      }
    >
      <div className="space-y-6">
        {/* Current Status */}
        <div className="grid grid-cols-3 gap-4">
          <OpsStatCard
            label="当前季节"
            value={seasons.find(s => s.is_active)?.name || '未配置'}
            helper={`${seasons.find(s => s.is_active)?.designs_count || 0} 款推荐`}
            tone="bg-stone-950 text-amber-50"
          />
          <OpsStatCard
            label="进行中的活动"
            value={festivals.filter(f => f.is_active).length}
            helper="个限时活动"
            tone="bg-white"
          />
          <OpsStatCard
            label="即将开始"
            value={festivals.filter(f => getDaysUntil(f.start_date) > 0 && getDaysUntil(f.start_date) <= 30).length}
            helper="30 天内开始"
            tone="bg-[#fffaf0]"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          {(['seasons', 'festivals'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-rose-500 text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-rose-300'
              }`}
            >
              {tab === 'seasons' ? '季节配置' : '节日活动'}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-4 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl p-4 border border-gray-100 h-32" />
            ))}
          </div>
        ) : activeTab === 'seasons' ? (
          <div className="space-y-4">
            {seasons.length === 0 ? (
              <div className="text-center py-20 bg-white rounded-xl border border-gray-100">
                <p className="text-gray-400">暂无季节配置</p>
                <button
                  onClick={handleCreate}
                  className="mt-4 text-rose-500 hover:underline"
                >
                  创建第一个季节
                </button>
              </div>
            ) : (
              seasons.map((season) => (
                <div
                  key={season.id}
                  className={`bg-white rounded-xl p-4 border ${season.is_active ? 'border-rose-200' : 'border-gray-100'}`}
                >
                  <div className="flex items-start gap-4">
                    <div className="text-4xl">{season.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                            {season.name}
                            {season.is_active && (
                              <span className="px-2 py-0.5 bg-rose-100 text-rose-600 text-xs rounded-full">
                                进行中
                              </span>
                            )}
                          </h3>
                          <p className="text-sm text-gray-500 mt-1">{season.description}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEdit(season)}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => toggleActive(season, 'season')}
                            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                              season.is_active
                                ? 'bg-rose-100 text-rose-600'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {season.is_active ? '停用' : '启用'}
                          </button>
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {season.colors.map((color) => (
                          <span key={color} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                            {color}
                          </span>
                        ))}
                      </div>

                      <div className="mt-3 text-sm text-gray-500">
                        <span>关键词: {season.keywords.join(', ')}</span>
                      </div>

                      <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
                        <span>{season.designs_count} 款匹配款式</span>
                        <span>活动期: {new Date(season.start_date).toLocaleDateString('zh-CN')} - {new Date(season.end_date).toLocaleDateString('zh-CN')}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {festivals.length === 0 ? (
              <div className="text-center py-20 bg-white rounded-xl border border-gray-100">
                <p className="text-gray-400">暂无节日活动</p>
                <button
                  onClick={handleCreate}
                  className="mt-4 text-rose-500 hover:underline"
                >
                  创建第一个活动
                </button>
              </div>
            ) : (
              festivals.map((festival) => (
                <div
                  key={festival.id}
                  className={`bg-white rounded-xl p-4 border ${festival.is_active ? 'border-orange-200' : 'border-gray-100'}`}
                >
                  <div className="flex items-start gap-4">
                    <div className="text-4xl">{festival.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                            {festival.name}
                            {festival.is_active && (
                              <span className="px-2 py-0.5 bg-orange-100 text-orange-600 text-xs rounded-full">
                                进行中
                              </span>
                            )}
                            {getDaysUntil(festival.start_date) > 0 && getDaysUntil(festival.start_date) <= 7 && (
                              <span className="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full">
                                {getDaysUntil(festival.start_date)}天后开始
                              </span>
                            )}
                          </h3>
                          <p className="text-sm text-gray-500 mt-1">{festival.description}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEdit(festival)}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => toggleActive(festival, 'festival')}
                            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                              festival.is_active
                                ? 'bg-orange-100 text-orange-600'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {festival.is_active ? '停用' : '启用'}
                          </button>
                        </div>
                      </div>

                      <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500 mb-2">匹配规则:</p>
                        <div className="flex flex-wrap gap-2">
                          {festival.match_rules.style_tags.map((tag) => (
                            <span key={tag} className="px-2 py-0.5 bg-rose-100 text-rose-600 text-xs rounded">
                              风格:{tag}
                            </span>
                          ))}
                          {festival.match_rules.color_tags.map((tag) => (
                            <span key={tag} className="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded">
                              颜色:{tag}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
                        <span>{festival.designs_count} 款匹配款式</span>
                        <span>活动期: {new Date(festival.start_date).toLocaleDateString('zh-CN')} - {new Date(festival.end_date).toLocaleDateString('zh-CN')}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Modal - Simplified for now */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-lg m-4 p-6">
            <h2 className="font-semibold text-gray-900 mb-4">
              {editingItem ? '编辑' : '新建'}{activeTab === 'seasons' ? '季节' : '活动'}
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              专题规则将用于后续 C 端分发和运营推荐，保存前请确认名称、时间范围和匹配标签。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </OpsShell>
  );
}
