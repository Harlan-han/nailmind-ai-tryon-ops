'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Bookmark, X, Eye, Sparkles, ArrowRight } from 'lucide-react';
import { api, type TryOnRecord } from '@/lib/api';
import { useValidatedUser } from '@/lib/use-validated-user';
import { MobileShell } from '@/components/mobile-shell';
import {
  getDesignCandidates,
  removeDesignCandidate,
  type DesignCandidate,
} from '@/lib/design-candidates';

interface CandidateRecord extends TryOnRecord {
  result_image_url: string | null;
  nail_design: {
    id: number;
    name: string;
    image_url: string;
    style_tags: string[];
    color_tags?: string[];
  };
}

export default function CandidatesPage() {
  const router = useRouter();
  const { user } = useValidatedUser('/candidates');
  const [candidates, setCandidates] = useState<CandidateRecord[]>([]);
  const [designCandidates, setDesignCandidates] = useState<DesignCandidate[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadCandidates() {
    await Promise.resolve();
    setLoading(true);
    try {
      setDesignCandidates(getDesignCandidates());
      const data = await api.getMyCandidateTryOns();
      setCandidates(data.filter((record) => !!record.nail_design) as CandidateRecord[]);
    } catch (error) {
      console.error('Failed to load candidates:', error);
      setCandidates([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!user) return;
    void Promise.resolve().then(loadCandidates);
  }, [user]);

  const handleRemoveDesign = (e: React.MouseEvent, designId: number) => {
    e.stopPropagation();
    removeDesignCandidate(designId);
    setDesignCandidates((prev) => prev.filter((candidate) => candidate.id !== designId));
  };

  const handleRemove = async (e: React.MouseEvent, recordId: number) => {
    e.stopPropagation();
    try {
      await api.toggleCandidate(recordId);
      setCandidates((prev) => prev.filter((c) => c.id !== recordId));
    } catch (error) {
      console.error('Failed to remove candidate:', error);
    }
  };

  const handleCompare = () => {
    router.push('/compare');
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  const totalCandidates = designCandidates.length + candidates.length;

  return (
    <MobileShell>
      <header className="sticky top-0 z-50 border-b border-stone-200/70 bg-[#fbf7ef]/85 backdrop-blur-2xl">
        <div className="px-5 h-14 flex items-center">
          <Link href="/" className="flex items-center text-gray-600 hover:text-rose-600">
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回
          </Link>
          <h1 className="flex-1 text-center font-semibold text-gray-900">我的候选</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="px-5 py-6 space-y-6">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-gray-900">候选清单</h2>
          <p className="text-sm text-gray-500 mt-1">所有想继续对比、生成或预约的款式都放在这里</p>
        </div>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl p-4 border border-gray-100 animate-pulse">
                <div className="flex gap-4">
                  <div className="w-24 h-24 rounded-lg bg-gray-200 shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/2" />
                    <div className="h-3 bg-gray-200 rounded w-1/3" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : totalCandidates === 0 ? (
          <div className="text-center py-20">
            <Bookmark className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">候选清单为空</p>
            <p className="text-gray-400 text-sm mt-1">在模板详情页点击“加入清单”，或试戴结果页点击“候选”。</p>
            <Link
              href="/designs"
              className="inline-flex items-center gap-2 mt-6 bg-rose-500 text-white px-6 py-3 rounded-full font-medium hover:bg-rose-600 transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              去选款式
            </Link>
          </div>
        ) : (
          <>
            {candidates.length >= 2 && (
              <button
                onClick={handleCompare}
                className="w-full bg-gradient-to-r from-rose-500 to-pink-500 text-white py-3 rounded-xl font-medium hover:shadow-lg transition-shadow flex items-center justify-center gap-2"
              >
                <Sparkles className="w-5 h-5" />
                对比这 {candidates.length} 款
                <ArrowRight className="w-4 h-4" />
              </button>
            )}

            {designCandidates.length > 0 && (
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-stone-950">待试戴模板</h3>
                  <span className="text-xs text-stone-400">{designCandidates.length} 款</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {designCandidates.map((design) => (
                    <Link
                      key={design.id}
                      href={`/tryon?design=${design.id}`}
                      className="overflow-hidden rounded-[1.5rem] bg-white shadow-sm"
                    >
                      <div className="relative aspect-square bg-stone-100">
                        <img src={design.image_url} alt={design.name} className="h-full w-full object-cover" />
                        <button
                          type="button"
                          onClick={(event) => handleRemoveDesign(event, design.id)}
                          className="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur"
                          aria-label="移出候选"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="p-3">
                        <p className="line-clamp-1 text-sm font-semibold text-stone-950">{design.name}</p>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {design.style_tags?.slice(0, 2).map((tag) => (
                            <span key={tag} className="rounded-full bg-stone-100 px-2 py-1 text-[11px] text-stone-500">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <p className="mt-2 text-xs text-stone-400">点击进入详情并生成试戴</p>
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            <div className="space-y-4">
              {candidates.length > 0 && (
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-stone-950">已试戴候选</h3>
                  <span className="text-xs text-stone-400">{candidates.length} 条</span>
                </div>
              )}
              {candidates.map((record) => (
                <div
                  key={record.id}
                  className="bg-white rounded-xl p-4 border border-gray-100 hover:border-rose-200 transition-colors"
                >
                  <div className="flex gap-4">
                    <Link
                      href={`/tryon?id=${record.id}`}
                      className="w-24 h-24 rounded-lg bg-gray-100 overflow-hidden shrink-0"
                    >
                      <img
                        src={record.result_image_url || record.nail_design.image_url}
                        alt={record.nail_design.name}
                        className="w-full h-full object-cover"
                      />
                    </Link>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div>
                          <Link href={`/tryon?id=${record.id}`}>
                            <h3 className="font-semibold text-gray-900 truncate hover:text-rose-600 transition-colors">
                              {record.nail_design.name}
                            </h3>
                          </Link>
                          <p className="text-xs text-gray-500 mt-1">{formatDate(record.created_at)}</p>
                        </div>
                        <button
                          onClick={(e) => handleRemove(e, record.id)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="flex flex-wrap gap-1 mt-2">
                        {record.nail_design.style_tags?.slice(0, 2).map((tag) => (
                          <span key={tag} className="text-xs bg-rose-50 text-rose-600 px-2 py-0.5 rounded-full">
                            {tag}
                          </span>
                        ))}
                        {record.nail_design.color_tags?.slice(0, 2).map((tag) => (
                          <span key={tag} className="text-xs bg-pink-50 text-pink-600 px-2 py-0.5 rounded-full">
                            {tag}
                          </span>
                        ))}
                      </div>

                      <div className="flex gap-3 mt-3">
                        <Link
                          href={`/tryon?id=${record.id}`}
                          className="text-xs text-rose-600 flex items-center gap-1 hover:underline"
                        >
                          <Eye className="w-3 h-3" />
                          查看详情
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </MobileShell>
  );
}
