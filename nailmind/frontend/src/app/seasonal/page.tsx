'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Calendar, Sparkles, Clock, Heart } from 'lucide-react';
import { api } from '@/lib/api';

interface SeasonalTheme {
  id: string;
  name: string;
  description: string;
  icon: string;
  keywords: string[];
  colors: string[];
  designs: Array<{
    design: {
      id: number;
      name: string;
      image_url: string;
      style_tags: string[];
      color_tags: string[];
    };
    match_score: number;
  }>;
}

interface FestivalTheme {
  festival: {
    id: string;
    name: string;
    description: string;
    icon: string;
  };
  designs: Array<{
    design: {
      id: number;
      name: string;
      image_url: string;
      style_tags: string[];
      color_tags: string[];
    };
    score: number;
  }>;
}

interface UpcomingTheme {
  id: string;
  name: string;
  description: string;
  icon: string;
  days_until: number;
}

export default function SeasonalPage() {
  const [currentThemes, setCurrentThemes] = useState<{
    season: SeasonalTheme;
    festivals: FestivalTheme[];
  } | null>(null);
  const [upcomingThemes, setUpcomingThemes] = useState<UpcomingTheme[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    await Promise.resolve();
    setLoading(true);
    try {
      const [current, upcoming] = await Promise.all([
        api.getCurrentThemes(),
        api.getUpcomingThemes(30),
      ]);
      setCurrentThemes(current);
      setUpcomingThemes(upcoming);
    } catch (error) {
      console.error('Failed to load seasonal themes:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadData);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-rose-50 to-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-rose-100">
        <div className="max-w-lg mx-auto px-4 h-14 flex items-center">
          <Link href="/" className="flex items-center text-gray-600 hover:text-rose-600">
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回
          </Link>
          <h1 className="flex-1 text-center font-semibold text-gray-900">节日专题</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {loading ? (
          <div className="space-y-6 animate-pulse">
            <div className="bg-gray-200 rounded-2xl p-6 h-64" />
            <div className="bg-gray-200 rounded-2xl p-5 h-48" />
            <div className="bg-gray-200 rounded-2xl p-5 h-40" />
          </div>
        ) : (
          <>
            {/* Current Season */}
            {currentThemes?.season && (
              <section className="bg-gradient-to-r from-rose-500 to-pink-500 rounded-2xl p-6 text-white">
                <div className="flex items-center gap-3 mb-4">
                  <div className="text-4xl">{currentThemes.season.icon}</div>
                  <div>
                    <h2 className="text-2xl font-bold">{currentThemes.season.name}</h2>
                    <p className="text-rose-100">{currentThemes.season.description}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                  {currentThemes.season.colors.map((color) => (
                    <span key={color} className="px-3 py-1 bg-white/20 rounded-full text-sm">
                      {color}
                    </span>
                  ))}
                </div>

                <p className="text-sm text-rose-100 mb-4">推荐款式</p>
                <div className="grid grid-cols-3 gap-3">
                  {currentThemes.season.designs?.slice(0, 3).map((item) => (
                    <Link
                      key={item.design.id}
                      href={`/tryon?design=${item.design.id}`}
                      className="aspect-square rounded-xl overflow-hidden bg-white/10"
                    >
                      <img
                        src={item.design.image_url}
                        alt={item.design.name}
                        className="w-full h-full object-cover"
                      />
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Active Festivals */}
            {currentThemes?.festivals && currentThemes.festivals.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-5 h-5 text-rose-500" />
                  <h3 className="font-semibold text-gray-900">限时活动</h3>
                </div>

                <div className="space-y-4">
                  {currentThemes.festivals.map((festival) => (
                    <div
                      key={festival.festival.id}
                      className="bg-white rounded-2xl p-5 shadow-sm border border-rose-100"
                    >
                      <div className="flex items-center gap-3 mb-4">
                        <div className="text-3xl">{festival.festival.icon}</div>
                        <div>
                          <h4 className="font-semibold text-gray-900">{festival.festival.name}</h4>
                          <p className="text-sm text-gray-500">{festival.festival.description}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-2">
                        {festival.designs?.slice(0, 3).map((item) => (
                          <Link
                            key={item.design.id}
                            href={`/tryon?design=${item.design.id}`}
                            className="aspect-square rounded-xl overflow-hidden bg-gray-100"
                          >
                            <img
                              src={item.design.image_url}
                              alt={item.design.name}
                              className="w-full h-full object-cover"
                            />
                          </Link>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Upcoming */}
            {upcomingThemes.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-5 h-5 text-rose-500" />
                  <h3 className="font-semibold text-gray-900">即将开始</h3>
                </div>

                <div className="space-y-3">
                  {upcomingThemes.slice(0, 3).map((theme) => (
                    <div
                      key={theme.id}
                      className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex items-center gap-3"
                    >
                      <div className="text-2xl">{theme.icon}</div>
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">{theme.name}</h4>
                        <p className="text-sm text-gray-500">{theme.description}</p>
                      </div>
                      <span className="text-sm text-rose-600 bg-rose-50 px-3 py-1 rounded-full">
                        {theme.days_until}天后
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Browse All */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-rose-100">
              <div className="flex items-center gap-2 mb-4">
                <Calendar className="w-5 h-5 text-rose-500" />
                <h3 className="font-semibold text-gray-900">按场景选款式</h3>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {['日常通勤', '约会聚会', '婚礼重要场合', '度假旅行'].map((scene) => (
                  <Link
                    key={scene}
                    href={`/designs?scene=${scene}`}
                    className="p-4 bg-gray-50 rounded-xl text-center hover:bg-rose-50 transition-colors"
                  >
                    <Heart className="w-5 h-5 text-rose-400 mx-auto mb-2" />
                    <span className="text-sm text-gray-700">{scene}</span>
                  </Link>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
