'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Briefcase, Heart, PartyPopper, Gift, Sparkles, ChevronRight, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface Design {
  id: number;
  name: string;
  image_url: string;
  style_tags: string[];
  color_tags: string[];
  scene_tags: string[];
  try_on_count: number;
}

interface SceneRecommendation {
  scene: string;
  icon: React.ReactNode;
  description: string;
  color: string;
  designs: Design[];
}

export default function SceneRecommendationsPage() {
  const router = useRouter();
  const [recommendations, setRecommendations] = useState<SceneRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeScene, setActiveScene] = useState<string | null>(null);

  async function loadRecommendations() {
    await Promise.resolve();
    setLoading(true);
    try {
      // Fetch designs for each scene
      const scenes = [
        {
          id: 'daily',
          name: '日常通勤',
          icon: <Briefcase className="w-6 h-6" />,
          description: '低调优雅，职场必备',
          color: 'bg-blue-50 text-blue-600 border-blue-100',
        },
        {
          id: 'date',
          name: '约会聚会',
          icon: <Heart className="w-6 h-6" />,
          description: '浪漫甜美，心动时刻',
          color: 'bg-pink-50 text-pink-600 border-pink-100',
        },
        {
          id: 'party',
          name: '派对活动',
          icon: <PartyPopper className="w-6 h-6" />,
          description: '吸睛闪耀，全场焦点',
          color: 'bg-purple-50 text-purple-600 border-purple-100',
        },
        {
          id: 'wedding',
          name: '婚礼重要场合',
          icon: <Gift className="w-6 h-6" />,
          description: '精致优雅，最美时刻',
          color: 'bg-rose-50 text-rose-600 border-rose-100',
        },
      ];

      const sceneData: SceneRecommendation[] = [];

      for (const scene of scenes) {
        try {
          const designs = await api.listDesigns({ scene_tags: scene.name, limit: '4' });
          sceneData.push({
            scene: scene.name,
            icon: scene.icon,
            description: scene.description,
            color: scene.color,
            designs: designs.slice(0, 4),
          });
        } catch (e) {
          console.error(`Failed to load designs for ${scene.name}:`, e);
        }
      }

      setRecommendations(sceneData);
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadRecommendations);
  }, []);

  const handleSceneClick = (sceneName: string) => {
    router.push(`/designs?scene=${encodeURIComponent(sceneName)}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-rose-50 to-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-rose-100">
        <div className="max-w-lg mx-auto px-4 h-14 flex items-center">
          <Link href="/" className="flex items-center text-gray-600 hover:text-rose-600">
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回
          </Link>
          <h1 className="flex-1 text-center font-semibold text-gray-900">场景推荐</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {/* Intro */}
        <div className="text-center space-y-2">
          <h2 className="text-xl font-semibold text-gray-900">按场景选款式</h2>
          <p className="text-sm text-gray-500">不同场合，不同风格，找到最适合你的那一款</p>
        </div>

        {loading ? (
          <div className="text-center py-20">
            <Loader2 className="w-8 h-8 text-rose-400 mx-auto animate-spin" />
            <p className="mt-4 text-gray-500">加载场景推荐...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {recommendations.map((rec) => (
              <div key={rec.scene} className="bg-white rounded-2xl p-5 shadow-sm border border-rose-100">
                {/* Scene Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 ${rec.color.split(' ')[0]} rounded-xl flex items-center justify-center`}>
                      <span className={rec.color.split(' ')[1]}>{rec.icon}</span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{rec.scene}</h3>
                      <p className="text-xs text-gray-500">{rec.description}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleSceneClick(rec.scene)}
                    className="text-sm text-rose-600 flex items-center gap-1 hover:underline"
                  >
                    查看更多
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>

                {/* Designs Grid */}
                {rec.designs.length > 0 ? (
                  <div className="grid grid-cols-4 gap-2">
                    {rec.designs.map((design) => (
                      <Link
                        key={design.id}
                        href={`/tryon?design=${design.id}`}
                        className="group"
                      >
                        <div className="aspect-square rounded-lg bg-gray-100 overflow-hidden">
                          <img
                            src={design.image_url}
                            alt={design.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                          />
                        </div>
                        <p className="text-xs text-gray-700 mt-1 truncate">{design.name}</p>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-gray-400 text-sm">
                    暂无该场景推荐款式
                  </div>
                )}

                {/* Scene Tags */}
                <div className="flex flex-wrap gap-2 mt-4">
                  {rec.designs
                    .flatMap((d) => d.style_tags || [])
                    .slice(0, 4)
                    .map((tag) => (
                      <span
                        key={tag}
                        className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full"
                      >
                        {tag}
                      </span>
                    ))}
                </div>
              </div>
            ))}

            {/* AI Recommendation CTA */}
            <div className="bg-gradient-to-r from-rose-500 to-pink-500 rounded-2xl p-6 text-white">
              <div className="flex items-center gap-3 mb-3">
                <Sparkles className="w-6 h-6" />
                <h3 className="font-semibold text-lg">AI 智能推荐</h3>
              </div>
              <p className="text-rose-100 text-sm mb-4">
                不知道选什么？让 AI 根据你的肤色、甲型和使用场景为你推荐最适合的款式
              </p>
              <Link
                href="/profile"
                className="inline-flex items-center gap-2 bg-white text-rose-600 px-6 py-3 rounded-full font-medium hover:bg-rose-50 transition-colors"
              >
                完善我的画像
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>

            {/* Tips */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-rose-100">
              <h3 className="font-semibold text-gray-900 mb-3">💡 选款小贴士</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start gap-2">
                  <span className="text-rose-400">•</span>
                  <span>通勤场合建议选择裸色、法式等低调优雅的款式</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400">•</span>
                  <span>约会时粉色系和闪粉元素能增加甜美感</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400">•</span>
                  <span>派对场合可以尝试更大胆的颜色和装饰</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400">•</span>
                  <span>婚礼等正式场合建议选择经典的法式或珍珠元素</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
