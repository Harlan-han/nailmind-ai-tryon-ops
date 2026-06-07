'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Check, X } from 'lucide-react';
import { api } from '@/lib/api';
import { scoreCandidateDesign } from '@/lib/compare-scoring';
import { useValidatedUser } from '@/lib/use-validated-user';

interface CompareItem {
  id: number;
  design: {
    id: number;
    name: string;
    image_url: string;
    style_tags: string[];
    color_tags: string[];
    scene_tags: string[];
    try_on_count: number;
    favorite_count: number;
  };
  result_image_url: string;
  ai_analysis: {
    skin_tone_match: number;
    style_fit: number;
    occasion_fit: number;
    overall: number;
  };
}

interface CandidateTryOnRecord {
  id: number;
  nail_design_id: number;
  result_image_url: string | null;
  status: string;
  is_candidate: boolean;
  nail_design?: {
    id?: number;
    name?: string;
    image_url?: string;
    style_tags?: string[];
    color_tags?: string[];
    scene_tags?: string[];
    try_on_count?: number;
    favorite_count?: number;
  } | null;
}

interface UserPreferenceProfile {
  preferred_styles?: Array<{ name: string; score: number; count: number }>;
  preferred_colors?: Array<{ name: string; score: number; count: number }>;
  preferred_scenes?: Array<{ name: string; score: number; count: number }>;
  skin_tone?: string | null;
  skin_undertone?: string | null;
}

export default function ComparePage() {
  const { user } = useValidatedUser('/compare');
  const [items, setItems] = useState<CompareItem[]>([]);
  const [selectedForRemoval, setSelectedForRemoval] = useState<number[]>([]);
  const [finalChoice, setFinalChoice] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadCandidates() {
    await Promise.resolve();
    setLoading(true);
    try {
      const [records, profile] = await Promise.all([
        api.getMyCandidateTryOns(),
        api.getMyPreferences() as Promise<UserPreferenceProfile>,
      ]);
      const candidates = records as CandidateTryOnRecord[];

      const mapped: CompareItem[] = candidates.map((record) => {
        const design = record.nail_design || {};
        const designForScoring = {
          id: design.id || record.nail_design_id,
          style_tags: design.style_tags || [],
          color_tags: design.color_tags || [],
          scene_tags: design.scene_tags || [],
          try_on_count: design.try_on_count || 0,
          favorite_count: design.favorite_count || 0,
        };

        return {
          id: record.id,
          design: {
            id: design.id || record.nail_design_id,
            name: design.name || `款式 ${record.nail_design_id}`,
            image_url: design.image_url || '',
            style_tags: design.style_tags || [],
            color_tags: design.color_tags || [],
            scene_tags: design.scene_tags || [],
            try_on_count: design.try_on_count || 0,
            favorite_count: design.favorite_count || 0,
          },
          result_image_url: record.result_image_url || design.image_url || '',
          ai_analysis: scoreCandidateDesign(designForScoring, profile),
        };
      });

      setItems(mapped);
    } catch (error) {
      console.error('Failed to load candidates:', error);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!user) return;
    void Promise.resolve().then(loadCandidates);
  }, [user]);

  const toggleRemove = (id: number) => {
    setSelectedForRemoval(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const removeSelected = async () => {
    try {
      // Toggle candidate off for each selected item
      for (const id of selectedForRemoval) {
        await api.toggleCandidate(id);
      }
      setItems(prev => prev.filter(item => !selectedForRemoval.includes(item.id)));
      setSelectedForRemoval([]);
    } catch (error) {
      console.error('Failed to remove candidates:', error);
    }
  };

  const getWinner = () => {
    if (items.length === 0) return null;
    return items.reduce((prev, current) =>
      prev.ai_analysis.overall > current.ai_analysis.overall ? prev : current
    );
  };

  const winner = getWinner();

  return (
    <div className="min-h-screen bg-gradient-to-b from-rose-50 to-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-rose-100">
        <div className="max-w-lg mx-auto px-4 h-14 flex items-center">
          <Link href="/records" className="flex items-center text-gray-600 hover:text-rose-600">
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回
          </Link>
          <h1 className="flex-1 text-center font-semibold text-gray-900">多款对比</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {/* Intro */}
        <div className="text-center">
          <h2 className="text-lg font-semibold text-gray-900">帮你选出最适合的一款</h2>
          <p className="text-sm text-gray-500 mt-1">AI 综合肤色匹配、风格适配、场合适配度给出建议</p>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="aspect-square rounded-xl bg-gray-200" />
                <div className="mt-2 h-4 bg-gray-200 rounded w-3/4 mx-auto" />
                <div className="mt-3 bg-white rounded-lg p-3 border border-gray-100 space-y-2">
                  <div className="h-3 bg-gray-200 rounded w-full" />
                  <div className="h-3 bg-gray-200 rounded w-full" />
                  <div className="h-3 bg-gray-200 rounded w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length > 0 ? (
          <>
            {/* Compare Grid */}
            <div className={`grid gap-4 ${items.length === 2 ? 'grid-cols-2' : items.length === 3 ? 'grid-cols-3' : 'grid-cols-1'}`}>
              {items.map((item) => (
                <div key={item.id} className={`relative ${selectedForRemoval.includes(item.id) ? 'opacity-50' : ''}`}>
                  {/* Selection checkbox */}
                  <button
                    onClick={() => toggleRemove(item.id)}
                    className={`absolute -top-2 -right-2 z-10 w-6 h-6 rounded-full flex items-center justify-center ${
                      selectedForRemoval.includes(item.id)
                        ? 'bg-red-500 text-white'
                        : 'bg-white border border-gray-300 text-gray-400'
                    }`}
                  >
                    <X className="w-4 h-4" />
                  </button>

                  {/* Result Image */}
                  <div className="aspect-square rounded-xl overflow-hidden bg-gray-100 border-2 border-rose-100">
                    <img
                      src={item.result_image_url}
                      alt={item.design.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = item.design.image_url || '';
                      }}
                    />
                  </div>

                  {/* Design Info */}
                  <div className="mt-2 text-center">
                    <h3 className="font-medium text-gray-900">{item.design.name}</h3>
                    <div className="flex gap-1 justify-center mt-1">
                      {item.design.style_tags.slice(0, 2).map((tag: string) => (
                        <span key={tag} className="text-xs bg-rose-100 text-rose-600 px-2 py-0.5 rounded-full">{tag}</span>
                      ))}
                    </div>
                  </div>

                  {/* AI Analysis */}
                  <div className="mt-3 bg-white rounded-lg p-3 border border-gray-100">
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">肤色匹配</span>
                        <span className="font-medium text-rose-600">{(item.ai_analysis.skin_tone_match * 100).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-1.5">
                        <div className="bg-rose-500 h-1.5 rounded-full" style={{ width: `${item.ai_analysis.skin_tone_match * 100}%` }} />
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">风格适配</span>
                        <span className="font-medium text-rose-600">{(item.ai_analysis.style_fit * 100).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-1.5">
                        <div className="bg-rose-500 h-1.5 rounded-full" style={{ width: `${item.ai_analysis.style_fit * 100}%` }} />
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">整体评分</span>
                        <span className="font-bold text-rose-600">{(item.ai_analysis.overall * 100).toFixed(0)}分</span>
                      </div>
                    </div>
                  </div>

                  {/* Winner badge */}
                  {winner?.id === item.id && items.length > 1 && (
                    <div className="absolute top-2 left-2 bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-1 rounded-full">
                      AI 推荐
                    </div>
                  )}

                  {/* Final choice button */}
                  <button
                    onClick={() => setFinalChoice(item.design.id)}
                    className={`w-full mt-2 py-2 rounded-lg text-sm font-medium transition-colors ${
                      finalChoice === item.design.id
                        ? 'bg-green-500 text-white'
                        : 'bg-rose-500 text-white hover:bg-rose-600'
                    }`}
                  >
                    {finalChoice === item.design.id ? '✓ 已选定' : '选定这款'}
                  </button>
                </div>
              ))}
            </div>

            {/* Actions */}
            {selectedForRemoval.length > 0 && (
              <button
                onClick={removeSelected}
                className="w-full py-3 bg-red-50 text-red-600 rounded-xl font-medium hover:bg-red-100 transition-colors"
              >
                移除选中的 {selectedForRemoval.length} 款
              </button>
            )}

            {/* AI Summary */}
            {winner && items.length > 1 && (
              <div className="bg-gradient-to-r from-rose-500 to-pink-500 rounded-xl p-4 text-white">
                <h3 className="font-semibold flex items-center gap-2">
                  <Check className="w-5 h-5" />
                  AI 对比总结
                </h3>
                <p className="mt-2 text-sm text-rose-100">
                  综合肤色匹配度、风格适配度和场合适配度，<strong>{winner.design.name}</strong> 是您的最佳选择。
                  这款美甲与您的肤色匹配度高达 {(winner.ai_analysis.skin_tone_match * 100).toFixed(0)}%，
                  风格上最能展现您的气质。
                </p>
              </div>
            )}

            {/* Final CTA */}
            {finalChoice && (
              <Link
                href={`/tryon?design=${finalChoice}`}
                className="w-full bg-rose-500 text-white py-4 rounded-xl font-medium hover:bg-rose-600 transition-colors flex items-center justify-center gap-2"
              >
                再次试戴选中款式
              </Link>
            )}
          </>
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-500">候选清单为空，去试戴几款再回来对比吧</p>
            <Link href="/designs" className="text-rose-600 text-sm mt-4 inline-block">
              去选款式
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
