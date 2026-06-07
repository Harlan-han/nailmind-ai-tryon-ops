'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, TrendingDown, Eye, MousePointer, Heart, Loader2, X } from 'lucide-react';
import { api } from '@/lib/api';
import { OpsImage } from '@/components/ops-image';
import { OpsShell } from '@/components/ops-shell';

interface ColdDesign {
  design: {
    id: number;
    name: string;
    image_url: string;
    view_count: number;
    try_on_count: number;
    favorite_count: number;
    booking_count: number;
  };
  alert_type: string;
  metrics: {
    impressions: number;
    try_on_rate: number;
    favorite_rate: number;
    booking_rate: number;
  };
  reason: string;
  suggestion: string;
}

interface DesignDetail {
  name: string;
  description?: string | null;
  image_url: string;
  style_tags?: string[] | null;
  color_tags?: string[] | null;
  scene_tags?: string[] | null;
  length?: string | null;
  shape?: string | null;
}

export default function ColdAlertPage() {
  const [coldDesigns, setColdDesigns] = useState<ColdDesign[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [editingItem, setEditingItem] = useState<ColdDesign | null>(null);
  const [tagDraft, setTagDraft] = useState('');

  async function loadColdDesigns() {
    await Promise.resolve();
    try {
      setLoading(true);
      const data = await api.getColdDesigns();
      setColdDesigns(data);
    } catch (error) {
      console.error('Failed to load cold designs:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadColdDesigns);
  }, []);

  const getAlertColor = (type: string) => {
    switch (type) {
      case "高曝光低试戴": return "text-orange-500 bg-orange-50";
      case "高试戴低收藏": return "text-yellow-500 bg-yellow-50";
      case "连续下滑": return "text-red-500 bg-red-50";
      default: return "text-gray-500 bg-gray-50";
    }
  };

  const runDesignAction = async (designId: number, action: () => Promise<unknown>, successMessage: string) => {
    setActionMessage(null);
    setActionError(null);
    setUpdatingId(designId);
    try {
      await action();
      setActionMessage(successMessage);
      await loadColdDesigns();
    } catch (error) {
      console.error(error);
      setActionError('操作失败，请稍后重试或到款式管理页检查该款状态。');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleAdjustPlacement = (item: ColdDesign) => {
    runDesignAction(
      item.design.id,
      () => api.toggleDesignHot(item.design.id, false),
      `${item.design.name} 已移出热门推荐位，可继续观察转化。`
    );
  };

  const handleOpenTagEditor = (item: ColdDesign) => {
    setEditingItem(item);
    setTagDraft('');
    setActionMessage(null);
    setActionError(null);
  };

  const handleSaveTags = async () => {
    if (!editingItem) return;
    const tags = tagDraft.split(',').map((tag) => tag.trim()).filter(Boolean);
    if (!tags.length) {
      setActionError('请至少输入一个标签，用逗号分隔。');
      return;
    }

    await runDesignAction(
      editingItem.design.id,
      async () => {
        const currentDesign = await api.getDesign(editingItem.design.id) as DesignDetail;
        return api.updateDesign(editingItem.design.id, {
          name: currentDesign.name || editingItem.design.name,
          description: currentDesign.description || editingItem.suggestion,
          image_url: currentDesign.image_url || editingItem.design.image_url,
          style_tags: tags,
          color_tags: currentDesign.color_tags || [],
          scene_tags: currentDesign.scene_tags || [],
          length: currentDesign.length || undefined,
          shape: currentDesign.shape || undefined,
        });
      },
      `${editingItem.design.name} 的标签已更新。`
    );
    setEditingItem(null);
  };

  const handleArchiveDesign = (item: ColdDesign) => {
    runDesignAction(
      item.design.id,
      () => api.updateDesignStatus(item.design.id, 'inactive'),
      `${item.design.name} 已下架，历史试戴与预约记录仍会保留。`
    );
  };

  return (
    <OpsShell
      title="冷门修复"
      subtitle="识别高曝光低试戴、高试戴低收藏和预约断层，给出可执行修复动作。"
    >
      <div className="space-y-6">
        {(actionMessage || actionError) && (
          <div
            className={
              actionError
                ? 'rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700'
                : 'rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800'
            }
          >
            {actionError || actionMessage}
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 text-orange-500 mb-2">
              <Eye className="w-5 h-5" />
              <span className="text-sm font-medium">高曝光低试戴</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {coldDesigns.filter((d) => d.alert_type === '高曝光低试戴').length}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 text-yellow-500 mb-2">
              <MousePointer className="w-5 h-5" />
              <span className="text-sm font-medium">高试戴低收藏</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {coldDesigns.filter((d) => d.alert_type === '高试戴低收藏').length}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 text-pink-500 mb-2">
              <Heart className="w-5 h-5" />
              <span className="text-sm font-medium">高收藏低预约</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {coldDesigns.filter((d) => d.alert_type === '高收藏低预约').length}
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 text-red-500 mb-2">
              <TrendingDown className="w-5 h-5" />
              <span className="text-sm font-medium">连续下滑</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {coldDesigns.filter((d) => d.alert_type === '连续下滑').length}
            </p>
          </div>
        </div>

        {/* Cold Designs List */}
        <div className="bg-white rounded-xl border border-gray-100">
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <h2 className="font-semibold text-gray-900">需要关注的款式</h2>
            </div>
          </div>
          <div className="divide-y divide-gray-100">
            {coldDesigns.map((item) => (
              <div key={item.design.id} className="p-4 flex gap-4">
                {/* Design Image */}
                <div className="w-24 h-24 rounded-lg bg-gray-100 overflow-hidden shrink-0">
                  <OpsImage
                    src={item.design.image_url}
                    alt={item.design.name}
                    className="w-full h-full object-cover"
                    fallbackLabel="款图缺失"
                  />
                </div>

                {/* Info */}
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900">{item.design.name}</h3>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${getAlertColor(item.alert_type)}`}>
                        {item.alert_type}
                      </span>
                    </div>
                    <div className="text-right text-sm">
                      <div className="flex items-center gap-1 text-gray-500">
                        <Eye className="w-4 h-4" />
                        <span>{item.metrics.impressions}</span>
                      </div>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="flex gap-4 mt-3 text-sm">
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">试戴率:</span>
                      <span className={`font-medium ${item.metrics.try_on_rate < 5 ? 'text-red-500' : 'text-gray-700'}`}>
                        {item.metrics.try_on_rate}%
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">收藏率:</span>
                      <span className={`font-medium ${item.metrics.favorite_rate < 20 ? 'text-red-500' : 'text-gray-700'}`}>
                        {item.metrics.favorite_rate}%
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">预约率:</span>
                      <span className={`font-medium ${item.metrics.booking_rate < 5 ? 'text-red-500' : 'text-gray-700'}`}>
                        {item.metrics.booking_rate}%
                      </span>
                    </div>
                  </div>

                  {/* Analysis */}
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">
                      <span className="font-medium text-gray-800">原因分析:</span> {item.reason}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      <span className="font-medium text-gray-800">优化建议:</span> {item.suggestion}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 mt-3">
                    <button
                      type="button"
                      disabled={updatingId === item.design.id}
                      onClick={() => handleAdjustPlacement(item)}
                      className="px-3 py-1.5 bg-rose-500 text-white text-sm rounded-lg hover:bg-rose-600 transition-colors disabled:opacity-50"
                    >
                      {updatingId === item.design.id ? '处理中' : '调整推荐位'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleOpenTagEditor(item)}
                      className="px-3 py-1.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      编辑标签
                    </button>
                    <button
                      type="button"
                      disabled={updatingId === item.design.id}
                      onClick={() => handleArchiveDesign(item)}
                      className="px-3 py-1.5 border border-red-300 text-red-600 text-sm rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      下架
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Auto Actions */}
        <div className="bg-white rounded-xl p-4 border border-gray-100">
          <h2 className="font-semibold text-gray-900 mb-3">自动处理规则</h2>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <input type="checkbox" id="rule1" className="rounded" defaultChecked />
              <label htmlFor="rule1" className="text-sm text-gray-700">
                连续 7 天试戴率低于 5% 自动移出热门推荐位
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="rule2" className="rounded" defaultChecked />
              <label htmlFor="rule2" className="text-sm text-gray-700">
                试戴率高但收藏率低于 10% 的款式自动推送优化建议
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="rule3" className="rounded" />
              <label htmlFor="rule3" className="text-sm text-gray-700">
                收藏率高但预约率为 0 的款式自动推送促销活动
              </label>
            </div>
          </div>
        </div>

        {editingItem && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4">
            <div className="w-full max-w-lg rounded-[2rem] bg-white p-5 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-400">Tag repair</p>
                  <h2 className="mt-1 text-lg font-bold text-stone-950">编辑 {editingItem.design.name} 标签</h2>
                </div>
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="rounded-full bg-stone-100 p-2 text-stone-500"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <p className="mb-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
                建议基于问题原因重写风格标签，例如：通勤、裸感、短甲、法式。多个标签用逗号分隔。
              </p>
              <input
                value={tagDraft}
                onChange={(event) => setTagDraft(event.target.value)}
                placeholder="例如：通勤, 裸感, 短甲"
                className="w-full rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none focus:border-stone-950"
              />
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="flex-1 rounded-2xl border border-stone-200 py-3 text-sm font-semibold text-stone-600"
                >
                  取消
                </button>
                <button
                  type="button"
                  disabled={updatingId === editingItem.design.id}
                  onClick={handleSaveTags}
                  className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50 disabled:opacity-50"
                >
                  {updatingId === editingItem.design.id && <Loader2 className="h-4 w-4 animate-spin" />}
                  保存标签
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </OpsShell>
  );
}
