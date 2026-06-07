'use client';

import { FormEvent, Suspense, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  ChevronRight,
  Filter,
  Loader2,
  Search,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';
import { api } from '@/lib/api';
import { MobileShell } from '@/components/mobile-shell';

interface Design {
  id: number;
  name: string;
  image_url: string;
  style_tags: string[];
  color_tags?: string[];
  scene_tags?: string[];
  is_hot: boolean;
  is_new: boolean;
  try_on_count?: number;
  favorite_count?: number;
}

const ALL_STYLE = '不限风格';
const ALL_COLOR = '不限颜色';
const ALL_SCENE = '不限场景';

function DesignsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [designs, setDesigns] = useState<Design[]>([]);
  const [activeStyle, setActiveStyle] = useState(searchParams.get('style') || ALL_STYLE);
  const [activeColor, setActiveColor] = useState(searchParams.get('color') || ALL_COLOR);
  const [activeScene, setActiveScene] = useState(searchParams.get('scene') || ALL_SCENE);
  const [styleTags, setStyleTags] = useState<string[]>([ALL_STYLE]);
  const [colorTags, setColorTags] = useState<string[]>([ALL_COLOR]);
  const [sceneTags, setSceneTags] = useState<string[]>([ALL_SCENE]);
  const [searchText, setSearchText] = useState(searchParams.get('q') || '');
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sourceLabel = useMemo(() => {
    if (searchParams.get('source') === 'profile') return '来自你的偏好画像';
    if (searchParams.get('source') === 'home') return '从首页继续探索';
    return '浏览所有可试戴模板';
  }, [searchParams]);

  async function loadTags() {
    await Promise.resolve();
    try {
      const [styles, colors, scenes] = await Promise.all([
        api.getStyleTags(),
        api.getColorTags(),
        api.getSceneTags(),
      ]);
      setStyleTags([ALL_STYLE, ...styles.tags]);
      setColorTags([ALL_COLOR, ...colors.tags]);
      setSceneTags([ALL_SCENE, ...scenes.tags]);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadDesigns() {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { limit: '60' };
      if (activeStyle !== ALL_STYLE) params.style_tags = activeStyle;
      if (activeColor !== ALL_COLOR) params.color_tags = activeColor;
      if (activeScene !== ALL_SCENE) params.scene_tags = activeScene;
      if (query.trim()) params.q = query.trim();
      const data = await api.listDesigns(params);
      setDesigns(data);
    } catch (err) {
      console.error(err);
      setError('款式加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadTags);
  }, []);

  useEffect(() => {
    void Promise.resolve().then(loadDesigns);
  }, [activeStyle, activeColor, activeScene, query]);

  const goBack = () => {
    if (window.history.length > 1) {
      router.back();
      return;
    }
    router.push('/');
  };

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setQuery(searchText.trim());
  };

  const resetSearch = () => {
    setSearchText('');
    setQuery('');
  };

  const resetFilters = () => {
    setActiveStyle(ALL_STYLE);
    setActiveColor(ALL_COLOR);
    setActiveScene(ALL_SCENE);
    resetSearch();
  };

  const hasActiveFilter =
    activeStyle !== ALL_STYLE || activeColor !== ALL_COLOR || activeScene !== ALL_SCENE || Boolean(query);

  return (
    <MobileShell>
      <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-[#fbf7ef]/85 px-5 pb-3 pt-4 backdrop-blur-2xl">
        <div className="mb-4 flex items-center justify-between">
          <button
            type="button"
            onClick={goBack}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-stone-700 shadow-sm"
            aria-label="返回上一级"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-stone-400">Choose Style</p>
            <h1 className="text-lg font-bold text-stone-950">选择款式</h1>
          </div>
          <Link
            href="/upload"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-stone-700 shadow-sm"
            aria-label="手部档案"
          >
            <SlidersHorizontal className="h-5 w-5" />
          </Link>
        </div>

        <form
          onSubmit={submitSearch}
          className="flex items-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm text-stone-500 shadow-sm"
        >
          <Search className="h-4 w-4" />
          <input
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-stone-900 outline-none placeholder:text-stone-400"
            placeholder="搜索猫眼、婚礼、银色、短甲..."
          />
          {query && (
            <button type="button" onClick={resetSearch} className="text-xs font-semibold text-stone-400">
              清除
            </button>
          )}
          <button type="submit" className="rounded-full bg-stone-950 px-3 py-1.5 text-xs font-bold text-amber-50">
            搜索
          </button>
        </form>
      </header>

      <main className="space-y-5 px-5 py-5">
        <section className="overflow-hidden rounded-[2rem] bg-stone-950 p-5 text-amber-50">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-2 text-sm text-amber-100/70">{sourceLabel}</p>
              <h2 className="text-2xl font-bold leading-tight">挑一款，再进入详情上传手照生成</h2>
              <p className="mt-2 text-sm leading-6 text-amber-100/75">
                这里和首页模板流使用同一套视觉与跳转逻辑，点卡片进入模板详情页。
              </p>
            </div>
            <Sparkles className="mt-1 h-7 w-7 shrink-0 text-amber-200" />
          </div>
        </section>

        <section className="rounded-[2rem] border border-stone-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-bold text-stone-950">
                <Filter className="h-4 w-4" />
                组合筛选
              </div>
              <p className="mt-1 text-xs text-stone-500">风格、颜色、场景会取交集；搜索词会继续缩小结果。</p>
            </div>
            {hasActiveFilter && (
              <button type="button" onClick={resetFilters} className="shrink-0 text-xs font-semibold text-stone-400">
                重置
              </button>
            )}
          </div>
          <div className="space-y-3">
            <FilterGroup label="风格" tags={styleTags} active={activeStyle} onChange={setActiveStyle} />
            <FilterGroup label="颜色" tags={colorTags} active={activeColor} onChange={setActiveColor} />
            <FilterGroup label="场景" tags={sceneTags} active={activeScene} onChange={setActiveScene} />
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-bold">全部模板</h3>
            <span className="text-sm text-stone-500">
              {query ? `“${query}” · ` : ''}
              {designs.length} 款
            </span>
          </div>

          {error && <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

          {loading ? (
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4, 5, 6].map((item) => (
                <div key={item} className="animate-pulse overflow-hidden rounded-[1.5rem] bg-white shadow-sm">
                  <div className="aspect-square bg-stone-200" />
                  <div className="space-y-2 p-3">
                    <div className="h-4 rounded bg-stone-200" />
                    <div className="h-3 w-2/3 rounded bg-stone-200" />
                  </div>
                </div>
              ))}
            </div>
          ) : designs.length === 0 ? (
            <div className="rounded-[2rem] border border-dashed border-stone-200 bg-white p-8 text-center">
              <p className="font-semibold text-stone-900">没有匹配款式</p>
              <p className="mt-1 text-sm text-stone-500">当前条件是组合筛选，减少一个标签或换个搜索词试试。</p>
            </div>
          ) : (
            <div className="columns-2 gap-3 [column-fill:_balance]">
              {designs.map((design, index) => (
                <Link
                  key={design.id}
                  href={`/tryon?design=${design.id}`}
                  className="mb-3 inline-block w-full break-inside-avoid overflow-hidden rounded-[1.5rem] bg-white shadow-sm"
                >
                  <div className={index % 3 === 1 ? 'relative aspect-[3/4]' : 'relative aspect-square'}>
                    <img src={design.image_url} alt={design.name} className="h-full w-full object-cover" />
                    <div className="absolute left-3 top-3 flex gap-1">
                      {design.is_hot && (
                        <span className="rounded-full bg-orange-500 px-2 py-1 text-[10px] font-bold text-white">热门</span>
                      )}
                      {design.is_new && (
                        <span className="rounded-full bg-emerald-500 px-2 py-1 text-[10px] font-bold text-white">新品</span>
                      )}
                    </div>
                  </div>
                  <div className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="line-clamp-1 font-semibold text-stone-950">{design.name}</h4>
                      <ChevronRight className="h-4 w-4 shrink-0 text-stone-300" />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {design.style_tags?.slice(0, 2).map((tag) => (
                        <span key={tag} className="rounded-full bg-stone-100 px-2 py-1 text-[11px] text-stone-500">
                          {tag}
                        </span>
                      ))}
                    </div>
                    <p className="mt-2 text-[11px] text-stone-400">{design.try_on_count || 0} 次试戴</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </MobileShell>
  );
}

function FilterGroup({
  label,
  tags,
  active,
  onChange,
}: {
  label: string;
  tags: string[];
  active: string;
  onChange: (tag: string) => void;
}) {
  return (
    <div className="grid grid-cols-[44px_minmax(0,1fr)] items-center gap-2">
      <div className="text-xs font-bold text-stone-500">{label}</div>
      <TagRail tags={tags} active={active} onChange={onChange} />
    </div>
  );
}

function TagRail({
  tags,
  active,
  onChange,
}: {
  tags: string[];
  active: string;
  onChange: (tag: string) => void;
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none]">
      {tags.map((tag) => (
        <button
          key={tag}
          type="button"
          onClick={() => onChange(tag)}
          className={
            active === tag
              ? 'shrink-0 rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50'
              : 'shrink-0 rounded-full bg-[#fbf7ef] px-4 py-2 text-sm font-medium text-stone-600'
          }
        >
          {tag}
        </button>
      ))}
    </div>
  );
}

export default function DesignsPage() {
  return (
    <Suspense
      fallback={
        <MobileShell>
          <div className="flex min-h-screen items-center justify-center text-stone-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            加载款式中
          </div>
        </MobileShell>
      }
    >
      <DesignsContent />
    </Suspense>
  );
}
