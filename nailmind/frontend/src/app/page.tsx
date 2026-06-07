'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Camera,
  ChevronRight,
  Loader2,
  Search,
  Sparkles,
  UserRound,
} from 'lucide-react';
import { api } from '@/lib/api';
import { MobileShell } from '@/components/mobile-shell';

interface Design {
  id: number;
  name: string;
  image_url: string;
  style_tags: string[];
  color_tags?: string[];
  is_hot: boolean;
  is_new: boolean;
  try_on_count?: number;
  favorite_count?: number;
}

const ALL_STYLE = '全部风格';

export default function Home() {
  const [designs, setDesigns] = useState<Design[]>([]);
  const [categories, setCategories] = useState<string[]>([ALL_STYLE]);
  const [activeCategory, setActiveCategory] = useState(ALL_STYLE);
  const [searchText, setSearchText] = useState('');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadTags() {
    await Promise.resolve();
    try {
      const styles = await api.getStyleTags();
      setCategories([ALL_STYLE, ...styles.tags]);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadDesigns() {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { limit: '30' };
      if (activeCategory !== ALL_STYLE) {
        params.style_tags = activeCategory;
      }
      if (query.trim()) {
        params.q = query.trim();
      }
      const data = await api.listDesigns(params);
      setDesigns(data);
    } catch (err) {
      console.error(err);
      setError('模板加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadTags);
  }, []);

  useEffect(() => {
    void Promise.resolve().then(loadDesigns);
  }, [activeCategory, query]);

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setQuery(searchText.trim());
  };

  const clearSearch = () => {
    setSearchText('');
    setQuery('');
  };

  return (
    <MobileShell>
        <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-[#fbf7ef]/85 px-5 pb-3 pt-4 backdrop-blur-2xl">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">NailMind</p>
              <h1 className="text-2xl font-bold tracking-tight">选择一款开始</h1>
            </div>
            <Link
              href="/profile"
              className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-stone-700 shadow-sm"
              aria-label="个人档案"
            >
              <UserRound className="h-5 w-5" />
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
              placeholder="搜索法式、猫眼、婚礼、短甲"
            />
            {query && (
              <button type="button" onClick={clearSearch} className="text-xs font-semibold text-stone-400">
                清除
              </button>
            )}
            <button type="submit" className="rounded-full bg-stone-950 px-3 py-1.5 text-xs font-bold text-amber-50">
              搜索
            </button>
          </form>
        </header>

        <section className="px-5 py-5">
          <div className="rounded-[2rem] bg-stone-950 p-5 text-amber-50">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold leading-tight">先看模板，再上传手照生成</h2>
                <p className="mt-2 text-sm leading-6 text-amber-100/75">
                  点击模板进入详情页，上传照片后再发起 AI 试戴。离开页面也不会重复生成。
                </p>
              </div>
              <Sparkles className="mt-1 h-7 w-7 shrink-0 text-amber-200" />
            </div>
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-4 py-2 text-sm font-semibold text-stone-950"
            >
              <Camera className="h-4 w-4" />
              先建手部档案
            </Link>
          </div>
        </section>

        <section className="px-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold">{query ? `“${query}”相关模板` : '美甲模板'}</h3>
              <p className="mt-1 text-xs text-stone-500">首页是风格快捷筛选；完整页可按风格、颜色、场景组合筛选。</p>
            </div>
            <Link href="/designs?source=home" className="flex items-center text-sm font-medium text-stone-500">
              全部款式
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mb-4 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none]">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
                className={
                  activeCategory === category
                    ? 'shrink-0 rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-amber-50'
                    : 'shrink-0 rounded-full bg-white px-4 py-2 text-sm font-medium text-stone-600 shadow-sm'
                }
              >
                {category}
              </button>
            ))}
          </div>

          <Link
            href="/profile"
            className="mb-4 flex items-center justify-between rounded-[1.5rem] border border-stone-200 bg-white p-4 shadow-sm"
          >
            <div>
              <p className="text-sm font-bold text-stone-950">我的偏好画像</p>
              <p className="mt-1 text-xs text-stone-500">查看收藏、候选和试戴沉淀出的推荐依据</p>
            </div>
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-stone-950 text-amber-50">
              <UserRound className="h-5 w-5" />
            </span>
          </Link>

          <Link
            href="/designs?source=home"
            className="mb-4 flex items-center justify-between rounded-[1.5rem] bg-stone-950 p-4 text-amber-50 shadow-sm"
          >
            <div>
              <p className="text-sm font-bold">进入完整选款页</p>
              <p className="mt-1 text-xs text-amber-100/70">更多筛选、更多模板，统一进入详情后上传生成</p>
            </div>
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/15">
              <ChevronRight className="h-5 w-5" />
            </span>
          </Link>

          {error && <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

          {loading ? (
            <div className="flex items-center justify-center py-20 text-stone-400">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              正在加载模板
            </div>
          ) : designs.length === 0 ? (
            <div className="rounded-[2rem] border border-dashed border-stone-200 bg-white p-8 text-center">
              <p className="font-semibold text-stone-900">没有匹配款式</p>
              <p className="mt-1 text-sm text-stone-500">换一个标签或搜索词试试。</p>
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
                    <h4 className="line-clamp-1 font-semibold">{design.name}</h4>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {design.style_tags?.slice(0, 2).map((tag) => (
                        <span key={tag} className="rounded-full bg-stone-100 px-2 py-1 text-[11px] text-stone-500">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
    </MobileShell>
  );
}
