'use client';

import { useEffect, useState } from 'react';
import { Plus, Search, Edit2, Trash2, Eye, Star, Sparkles, X } from 'lucide-react';
import { api } from '@/lib/api';
import { OpsShell, OpsStatCard } from '@/components/ops-shell';

interface Design {
  id: number;
  name: string;
  description: string;
  image_url: string;
  style_tags: string[];
  color_tags: string[];
  scene_tags: string[];
  length: string;
  shape: string;
  status: string;
  is_hot: boolean;
  is_new: boolean;
  view_count: number;
  try_on_count: number;
  favorite_count: number;
  booking_count: number;
  created_at: string;
}

interface DesignForm {
  name: string;
  description: string;
  image_url: string;
  style_tags: string;
  color_tags: string;
  scene_tags: string;
  length: string;
  shape: string;
}

const INITIAL_FORM: DesignForm = {
  name: '',
  description: '',
  image_url: '',
  style_tags: '',
  color_tags: '',
  scene_tags: '',
  length: '',
  shape: '',
};

export default function DesignsPage() {
  const [designs, setDesigns] = useState<Design[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [showModal, setShowModal] = useState(false);
  const [editingDesign, setEditingDesign] = useState<Design | null>(null);
  const [form, setForm] = useState<DesignForm>(INITIAL_FORM);
  const [tagOptions, setTagOptions] = useState({
    styleTags: [] as string[],
    colorTags: [] as string[],
    sceneTags: [] as string[],
  });

  useEffect(() => {
    loadDesigns();
    loadTagOptions();
  }, []);

  async function loadTagOptions() {
    try {
      const config = await api.getOperationsConfig();
      setTagOptions({
        styleTags: config.styleTags,
        colorTags: config.colorTags,
        sceneTags: config.sceneTags,
      });
    } catch (error) {
      console.error('Failed to load tag options:', error);
    }
  }

  async function loadDesigns() {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        limit: '100',
        include_inactive: 'true',
        only_servable: 'true',
        dedupe_images: 'true',
      };
      if (statusFilter !== 'all') {
        // Note: API doesn't support status filter directly, we'll filter locally
      }
      const data = await api.listDesigns(params);
      setDesigns(data);
    } catch (error) {
      console.error('Failed to load designs:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredDesigns = designs.filter(d => {
    const matchesSearch = d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         d.style_tags?.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === 'all' || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleCreate = () => {
    setEditingDesign(null);
    setForm(INITIAL_FORM);
    setShowModal(true);
  };

  const handleEdit = (design: Design) => {
    setEditingDesign(design);
    setForm({
      name: design.name,
      description: design.description || '',
      image_url: design.image_url,
      style_tags: design.style_tags?.join(', ') || '',
      color_tags: design.color_tags?.join(', ') || '',
      scene_tags: design.scene_tags?.join(', ') || '',
      length: design.length || '',
      shape: design.shape || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async () => {
    try {
      const data = {
        ...form,
        style_tags: form.style_tags.split(',').map(t => t.trim()).filter(Boolean),
        color_tags: form.color_tags.split(',').map(t => t.trim()).filter(Boolean),
        scene_tags: form.scene_tags.split(',').map(t => t.trim()).filter(Boolean),
        status: 'active',
        is_hot: false,
        is_new: true,
      };

      if (editingDesign) {
        await api.updateDesign(editingDesign.id, data);
      } else {
        await api.createDesign(data);
      }

      setShowModal(false);
      loadDesigns();
    } catch (error) {
      console.error('Failed to save design:', error);
      alert('保存失败，请检查输入');
    }
  };

  const applyTag = (field: 'style_tags' | 'color_tags' | 'scene_tags', tag: string) => {
    const values = form[field].split(',').map(t => t.trim()).filter(Boolean);
    if (!values.includes(tag)) {
      setForm({ ...form, [field]: [...values, tag].join(', ') });
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要下架归档这款美甲吗？历史试戴和预约记录会保留。')) return;

    try {
      await api.deleteDesign(id);
      loadDesigns();
    } catch (error) {
      console.error('Failed to delete design:', error);
      alert('下架失败');
    }
  };

  const toggleHot = async (design: Design) => {
    try {
      await api.toggleDesignHot(design.id, !design.is_hot);
      loadDesigns();
    } catch (error) {
      console.error('Failed to toggle hot status:', error);
    }
  };

  const toggleNew = async (design: Design) => {
    try {
      await api.toggleDesignNew(design.id, !design.is_new);
      loadDesigns();
    } catch (error) {
      console.error('Failed to toggle new status:', error);
    }
  };

  const toggleStatus = async (design: Design) => {
    try {
      const newStatus = design.status === 'active' ? 'inactive' : 'active';
      await api.updateDesignStatus(design.id, newStatus);
      loadDesigns();
    } catch (error) {
      console.error('Failed to toggle status:', error);
    }
  };

  return (
    <OpsShell
      title="款式管理"
      subtitle="维护美甲模板资产，控制上架、热门、新品和推荐位状态。"
      action={
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50"
        >
          <Plus className="w-4 h-4" />
          新增款式
        </button>
      }
    >
      <div>
        {/* Filters */}
        <div className="rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-4 shadow-sm mb-6">
          <div className="flex flex-col gap-4 md:flex-row">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
              <input
                type="text"
                placeholder="搜索款式名称或标签..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-3 border border-stone-200 rounded-2xl bg-white text-sm focus:outline-none focus:border-stone-950"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'all' | 'active' | 'inactive')}
              className="px-4 py-3 border border-stone-200 rounded-2xl bg-white text-sm focus:outline-none focus:border-stone-950"
            >
              <option value="all">全部状态</option>
              <option value="active">已上架</option>
              <option value="inactive">已下架</option>
            </select>
          </div>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          <OpsStatCard label="总款式数" value={designs.length} helper="当前资产池" tone="bg-[#fffaf0]" />
          <OpsStatCard label="热门款式" value={designs.filter(d => d.is_hot).length} helper="推荐位重点观察" tone="bg-amber-50" />
          <OpsStatCard label="新品" value={designs.filter(d => d.is_new).length} helper="近期上新" tone="bg-blue-50" />
          <OpsStatCard label="总试戴次数" value={designs.reduce((sum, d) => sum + d.try_on_count, 0)} helper="用户兴趣信号" tone="bg-white" />
        </div>

        {/* Designs Grid */}
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 animate-pulse">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => (
              <div key={i}>
                <div className="aspect-square rounded-xl bg-gray-200" />
                <div className="mt-2 h-4 bg-gray-200 rounded w-3/4" />
                <div className="mt-1 h-3 bg-gray-200 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : filteredDesigns.length === 0 ? (
          <div className="text-center py-20 text-stone-400 rounded-[2rem] border border-dashed border-stone-300 bg-[#fffaf0]">
            <p>暂无款式数据</p>
            <button
              onClick={handleCreate}
              className="mt-4 text-stone-950 text-sm font-semibold hover:underline"
            >
              添加第一款
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {filteredDesigns.map((design) => (
              <div
                key={design.id}
                className={`bg-white rounded-3xl border border-stone-200 overflow-hidden transition-shadow hover:shadow-lg ${
                  design.status === 'inactive' ? 'opacity-60' : ''
                }`}
              >
                {/* Image */}
                <div className="aspect-square relative">
                  <DesignCover src={design.image_url} alt={design.name} />
                  {/* Badges */}
                  <div className="absolute top-2 left-2 flex gap-1">
                    {design.is_hot && (
                    <span className="px-2 py-0.5 bg-stone-950 text-amber-50 text-xs rounded-full flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        热门
                      </span>
                    )}
                    {design.is_new && (
                      <span className="px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">
                        新品
                      </span>
                    )}
                  </div>
                  {/* Status Badge */}
                  <div className="absolute top-2 right-2">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      design.status === 'active'
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-stone-100 text-stone-600'
                    }`}>
                      {design.status === 'active' ? '上架' : '下架'}
                    </span>
                  </div>
                </div>

                {/* Info */}
                <div className="p-3">
                  <h3 className="font-medium text-gray-900 truncate">{design.name}</h3>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {design.style_tags?.slice(0, 2).map((tag) => (
                      <span key={tag} className="text-xs bg-amber-50 text-amber-900 px-2 py-0.5 rounded-full">
                        {tag}
                      </span>
                    ))}
                    {design.color_tags?.slice(0, 1).map((tag) => (
                      <span key={tag} className="text-xs bg-stone-100 text-stone-600 px-2 py-0.5 rounded-full">
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* Stats */}
                  <div className="flex gap-3 mt-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Eye className="w-3 h-3" />
                      {design.view_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <Star className="w-3 h-3" />
                      {design.favorite_count}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
                    <button
                      onClick={() => handleEdit(design)}
                      className="flex-1 flex items-center justify-center gap-1 py-1.5 text-sm text-stone-600 hover:bg-stone-50 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                      编辑
                    </button>
                    <button
                      onClick={() => toggleHot(design)}
                      className={`flex-1 flex items-center justify-center gap-1 py-1.5 text-sm rounded-lg transition-colors ${
                        design.is_hot
                          ? 'text-amber-800 bg-amber-50'
                          : 'text-stone-600 hover:bg-stone-50'
                      }`}
                    >
                      <Sparkles className="w-4 h-4" />
                      {design.is_hot ? '热门' : '标记'}
                    </button>
                    <button
                      onClick={() => toggleStatus(design)}
                      className={`flex-1 flex items-center justify-center gap-1 py-1.5 text-sm rounded-lg transition-colors ${
                        design.status === 'active'
                          ? 'text-red-600 hover:bg-red-50'
                          : 'text-green-600 hover:bg-green-50'
                      }`}
                    >
                      {design.status === 'active' ? '下架' : '上架'}
                    </button>
                    <button
                      onClick={() => handleDelete(design.id)}
                      className="flex items-center justify-center p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-[2rem] w-full max-w-lg max-h-[90vh] overflow-y-auto m-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">
                {editingDesign ? '编辑款式' : '新增款式'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* Image URL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">图片 URL</label>
                <input
                  type="text"
                  value={form.image_url}
                  onChange={(e) => setForm({ ...form, image_url: e.target.value })}
                  placeholder="https://example.com/image.jpg"
                  className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                />
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">款式名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="如：法式渐变"
                  className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="款式描述..."
                  rows={3}
                  className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                />
              </div>

              {/* Style Tags */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">风格标签</label>
                <input
                  type="text"
                  value={form.style_tags}
                  onChange={(e) => setForm({ ...form, style_tags: e.target.value })}
                  placeholder="如：法式, 渐变, 简约（用逗号分隔）"
                  className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                />
                <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                  {tagOptions.styleTags.slice(0, 16).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => applyTag('style_tags', tag)}
                      className="shrink-0 rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-900"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Color Tags */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">颜色标签</label>
                <input
                  type="text"
                  value={form.color_tags}
                  onChange={(e) => setForm({ ...form, color_tags: e.target.value })}
                  placeholder="如：裸色, 粉色, 白色（用逗号分隔）"
                  className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                />
                <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                  {tagOptions.colorTags.slice(0, 16).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => applyTag('color_tags', tag)}
                      className="shrink-0 rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Scene Tags */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">场合适用</label>
                <input
                  type="text"
                  value={form.scene_tags}
                  onChange={(e) => setForm({ ...form, scene_tags: e.target.value })}
                  placeholder="如：日常, 婚礼, 职场（用逗号分隔）"
                  className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                />
                <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                  {tagOptions.sceneTags.slice(0, 16).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => applyTag('scene_tags', tag)}
                      className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Length & Shape */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">长度</label>
                  <select
                    value={form.length}
                    onChange={(e) => setForm({ ...form, length: e.target.value })}
                    className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                  >
                    <option value="">请选择</option>
                    <option value="短">短</option>
                    <option value="中">中</option>
                    <option value="长">长</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">形状</label>
                  <select
                    value={form.shape}
                    onChange={(e) => setForm({ ...form, shape: e.target.value })}
                    className="w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-stone-950"
                  >
                    <option value="">请选择</option>
                    <option value="方形">方形</option>
                    <option value="圆形">圆形</option>
                    <option value="尖形">尖形</option>
                    <option value="椭圆形">椭圆形</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-3 p-4 border-t border-gray-100">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 py-2 border border-stone-300 text-stone-700 rounded-xl hover:bg-stone-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                className="flex-1 py-2 bg-stone-950 text-amber-50 rounded-xl hover:bg-stone-800 transition-colors"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </OpsShell>
  );
}

function DesignCover({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);

  if (failed || !src) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center bg-stone-100 px-3 text-center text-xs text-stone-500">
        <span className="font-medium text-stone-700">封面异常</span>
        <span className="mt-1 line-clamp-2 break-all">{src || '未配置图片'}</span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className="w-full h-full object-cover"
      onError={() => setFailed(true)}
    />
  );
}
