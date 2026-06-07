'use client';

import { useEffect, useState } from 'react';
import { Save, RotateCcw, AlertCircle, CheckCircle, Settings, Tag, Sliders, Bell, Palette } from 'lucide-react';
import { api, OperationsConfig } from '@/lib/api';
import { OpsShell, OpsStatCard } from '@/components/ops-shell';

const FALLBACK_CONFIG: OperationsConfig = {
  styleTags: [],
  colorTags: [],
  sceneTags: [],
  hotThreshold: 50,
  newThreshold: 7,
  trendingDays: 7,
  designsPerPage: 20,
  maxCandidates: 10,
  enableAiInsights: true,
  enableNotifications: true,
};

export default function SettingsPage() {
  const [config, setConfig] = useState<OperationsConfig>(FALLBACK_CONFIG);
  const [hasChanges, setHasChanges] = useState(false);
  const [showSaveSuccess, setShowSaveSuccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [activeSection, setActiveSection] = useState<'tags' | 'rules' | 'display'>('tags');

  async function loadConfig() {
    await Promise.resolve();
    setLoading(true);
    setErrorMessage('');
    try {
      const data = await api.getOperationsConfig();
      setConfig(data);
      setHasChanges(false);
    } catch {
      setErrorMessage('配置读取失败，请确认后端服务已启动');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadConfig);
  }, []);

  const handleSave = async () => {
    setErrorMessage('');
    try {
      const saved = await api.updateOperationsConfig(config);
      setConfig(saved);
      setHasChanges(false);
      setShowSaveSuccess(true);
      setTimeout(() => setShowSaveSuccess(false), 3000);
    } catch {
      setErrorMessage('保存失败，请稍后重试');
    }
  };

  const handleReset = () => {
    setConfig(FALLBACK_CONFIG);
    setHasChanges(true);
  };

  const updateConfig = (updates: Partial<OperationsConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
    setHasChanges(true);
  };

  const addTag = (type: 'styleTags' | 'colorTags' | 'sceneTags', value: string) => {
    if (value.trim() && !config[type].includes(value.trim())) {
      updateConfig({ [type]: [...config[type], value.trim()] });
    }
  };

  const removeTag = (type: 'styleTags' | 'colorTags' | 'sceneTags', index: number) => {
    const newTags = [...config[type]];
    newTags.splice(index, 1);
    updateConfig({ [type]: newTags });
  };

  const sections = [
    { id: 'tags' as const, label: '标签管理', icon: Tag },
    { id: 'rules' as const, label: '推荐规则', icon: Sliders },
    { id: 'display' as const, label: '显示设置', icon: Settings },
  ];

  return (
    <OpsShell
      title="配置中心"
      subtitle="管理后端标签、推荐规则和展示开关；款式页、筛选和 Agent 会读取同一套数据。"
      action={
        hasChanges ? (
          <span className="rounded-full bg-amber-50 px-4 py-2 text-sm font-medium text-amber-800">
            有未保存更改
          </span>
        ) : (
          <span className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
            配置已同步
          </span>
        )
      }
    >
      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <OpsStatCard label="风格标签" value={config.styleTags.length} helper="用于模板分类" tone="bg-[#fffaf0]" />
        <OpsStatCard label="颜色标签" value={config.colorTags.length} helper="用于偏好画像" tone="bg-white" />
        <OpsStatCard label="场景标签" value={config.sceneTags.length} helper="用于专题推荐" tone="bg-white" />
        <OpsStatCard label="热门阈值" value={config.hotThreshold} helper="试戴次数触发" tone="bg-amber-50" />
      </section>

      {errorMessage && (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      {loading && (
        <div className="mb-4 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-500">
          正在同步后端配置...
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          {/* Sidebar */}
          <div className="space-y-2">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-left transition-colors ${
                  activeSection === section.id
                    ? 'bg-stone-950 text-amber-50'
                    : 'bg-[#fffaf0] text-stone-700 hover:bg-white border border-stone-200'
                }`}
              >
                <section.icon className="w-5 h-5" />
                <span className="font-medium">{section.label}</span>
              </button>
            ))}

            {/* Save Actions */}
            <div className="mt-6 p-4 bg-white rounded-[2rem] border border-stone-200 space-y-2 shadow-sm">
              <button
                onClick={handleSave}
                disabled={!hasChanges || loading}
                className="w-full flex items-center justify-center gap-2 bg-stone-950 text-amber-50 py-3 rounded-2xl font-medium hover:bg-stone-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Save className="w-4 h-4" />
                保存配置
              </button>
              <button
                onClick={handleReset}
                className="w-full flex items-center justify-center gap-2 border border-stone-300 text-stone-700 py-3 rounded-2xl font-medium hover:bg-stone-50 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                清空手动标签
              </button>
            </div>

            {/* Save Success Toast */}
            {showSaveSuccess && (
              <div className="mt-2 p-3 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                <span className="text-sm text-emerald-700">配置已保存</span>
              </div>
            )}
          </div>

          {/* Content */}
          <div className="space-y-6">
            {/* Tags Section */}
            {activeSection === 'tags' && (
              <>
                {/* Style Tags */}
                <div className="bg-white rounded-[2rem] p-6 border border-stone-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <Palette className="w-5 h-5 text-stone-700" />
                    <h2 className="font-semibold text-stone-950">风格标签</h2>
                  </div>
                  <p className="text-sm text-stone-500 mb-4">
                    这里展示“当前款式有效标签 + 后台补充标签”。若要彻底移除某个正在被款式使用的标签，需要到款式管理中编辑对应款式。
                  </p>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {config.styleTags.map((tag, index) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-amber-50 text-amber-900 rounded-full text-sm"
                      >
                        {tag}
                        <button
                          onClick={() => removeTag('styleTags', index)}
                          className="text-amber-600 hover:text-amber-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const input = e.currentTarget.elements.namedItem('newStyle') as HTMLInputElement;
                      addTag('styleTags', input.value);
                      input.value = '';
                    }}
                    className="flex gap-2"
                  >
                    <input
                      name="newStyle"
                      type="text"
                      placeholder="添加新风格标签"
                      className="flex-1 px-4 py-3 border border-stone-200 rounded-2xl text-sm focus:outline-none focus:border-stone-950"
                    />
                    <button
                      type="submit"
                      className="px-5 py-3 bg-stone-950 text-amber-50 rounded-2xl text-sm font-medium hover:bg-stone-800"
                    >
                      添加
                    </button>
                  </form>
                </div>

                {/* Color Tags */}
                <div className="bg-white rounded-[2rem] p-6 border border-stone-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <Palette className="w-5 h-5 text-stone-700" />
                    <h2 className="font-semibold text-stone-950">颜色标签</h2>
                  </div>
                  <p className="text-sm text-stone-500 mb-4">
                    管理可用的美甲颜色标签
                  </p>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {config.colorTags.map((tag, index) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-stone-100 text-stone-700 rounded-full text-sm"
                      >
                        {tag}
                        <button
                          onClick={() => removeTag('colorTags', index)}
                          className="text-stone-400 hover:text-stone-700"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const input = e.currentTarget.elements.namedItem('newColor') as HTMLInputElement;
                      addTag('colorTags', input.value);
                      input.value = '';
                    }}
                    className="flex gap-2"
                  >
                    <input
                      name="newColor"
                      type="text"
                      placeholder="添加新颜色标签"
                      className="flex-1 px-4 py-3 border border-stone-200 rounded-2xl text-sm focus:outline-none focus:border-stone-950"
                    />
                    <button
                      type="submit"
                      className="px-5 py-3 bg-stone-950 text-amber-50 rounded-2xl text-sm font-medium hover:bg-stone-800"
                    >
                      添加
                    </button>
                  </form>
                </div>

                {/* Scene Tags */}
                <div className="bg-white rounded-[2rem] p-6 border border-stone-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <Bell className="w-5 h-5 text-stone-700" />
                    <h2 className="font-semibold text-stone-950">场景标签</h2>
                  </div>
                  <p className="text-sm text-stone-500 mb-4">
                    管理可用的使用场景标签
                  </p>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {config.sceneTags.map((tag, index) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-sm"
                      >
                        {tag}
                        <button
                          onClick={() => removeTag('sceneTags', index)}
                          className="text-blue-400 hover:text-blue-700"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const input = e.currentTarget.elements.namedItem('newScene') as HTMLInputElement;
                      addTag('sceneTags', input.value);
                      input.value = '';
                    }}
                    className="flex gap-2"
                  >
                    <input
                      name="newScene"
                      type="text"
                      placeholder="添加新场景标签"
                      className="flex-1 px-4 py-3 border border-stone-200 rounded-2xl text-sm focus:outline-none focus:border-stone-950"
                    />
                    <button
                      type="submit"
                      className="px-5 py-3 bg-stone-950 text-amber-50 rounded-2xl text-sm font-medium hover:bg-stone-800"
                    >
                      添加
                    </button>
                  </form>
                </div>
              </>
            )}

            {/* Rules Section */}
            {activeSection === 'rules' && (
              <div className="bg-white rounded-[2rem] p-6 border border-stone-200 shadow-sm space-y-6">
                <div className="flex items-center gap-2 mb-2">
                  <Sliders className="w-5 h-5 text-stone-700" />
                  <h2 className="font-semibold text-stone-950">推荐规则配置</h2>
                </div>

                <div className="space-y-4">
                  {/* Hot Threshold */}
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-2">
                      热门款式阈值（试戴次数）
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="10"
                        max="200"
                        value={config.hotThreshold}
                        onChange={(e) => updateConfig({ hotThreshold: parseInt(e.target.value) })}
                        className="flex-1"
                      />
                      <span className="w-16 text-right font-medium text-stone-950">
                        {config.hotThreshold}
                      </span>
                    </div>
                    <p className="text-xs text-stone-500 mt-1">
                      超过此试戴次数的款式会被标记为热门
                    </p>
                  </div>

                  {/* New Threshold */}
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-2">
                      新品有效期（天）
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="3"
                        max="30"
                        value={config.newThreshold}
                        onChange={(e) => updateConfig({ newThreshold: parseInt(e.target.value) })}
                        className="flex-1"
                      />
                      <span className="w-16 text-right font-medium text-stone-950">
                        {config.newThreshold}
                      </span>
                    </div>
                    <p className="text-xs text-stone-500 mt-1">
                      上架后在此天数内被视为新品
                    </p>
                  </div>

                  {/* Trending Days */}
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-2">
                      趋势统计周期（天）
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="3"
                        max="14"
                        value={config.trendingDays}
                        onChange={(e) => updateConfig({ trendingDays: parseInt(e.target.value) })}
                        className="flex-1"
                      />
                      <span className="w-16 text-right font-medium text-stone-950">
                        {config.trendingDays}
                      </span>
                    </div>
                    <p className="text-xs text-stone-500 mt-1">
                      计算趋势时的数据采样周期
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-blue-50 rounded-2xl">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-blue-500 mt-0.5" />
                    <p className="text-sm text-blue-700">
                      这些设置将影响首页和运营端的数据展示和推荐逻辑
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Display Section */}
            {activeSection === 'display' && (
              <div className="bg-white rounded-[2rem] p-6 border border-stone-200 shadow-sm space-y-6">
                <div className="flex items-center gap-2 mb-2">
                  <Settings className="w-5 h-5 text-stone-700" />
                  <h2 className="font-semibold text-stone-950">显示设置</h2>
                </div>

                <div className="space-y-4">
                  {/* Designs Per Page */}
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-2">
                      每页显示款式数
                    </label>
                    <select
                      value={config.designsPerPage}
                      onChange={(e) => updateConfig({ designsPerPage: parseInt(e.target.value) })}
                      className="w-full px-4 py-3 border border-stone-200 rounded-2xl focus:outline-none focus:border-stone-950"
                    >
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>

                  {/* Max Candidates */}
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-2">
                      候选清单最大数量
                    </label>
                    <select
                      value={config.maxCandidates}
                      onChange={(e) => updateConfig({ maxCandidates: parseInt(e.target.value) })}
                      className="w-full px-4 py-3 border border-stone-200 rounded-2xl focus:outline-none focus:border-stone-950"
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                    </select>
                  </div>

                  {/* Toggle Options */}
                  <div className="space-y-3 pt-4">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={config.enableAiInsights}
                        onChange={(e) => updateConfig({ enableAiInsights: e.target.checked })}
                        className="w-5 h-5 rounded border-stone-300 text-stone-950 focus:ring-stone-950"
                      />
                      <span className="text-stone-700">启用 AI 运营洞察</span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={config.enableNotifications}
                        onChange={(e) => updateConfig({ enableNotifications: e.target.checked })}
                        className="w-5 h-5 rounded border-stone-300 text-stone-950 focus:ring-stone-950"
                      />
                      <span className="text-stone-700">启用通知提醒</span>
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
      </div>
    </OpsShell>
  );
}
