'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, User, Palette, Sparkles, Bookmark, Calendar, Camera, LogOut } from 'lucide-react';
import { api } from '@/lib/api';
import { clearAuthSession } from '@/lib/auth';
import { useValidatedUser } from '@/lib/use-validated-user';
import { MobileShell } from '@/components/mobile-shell';

interface PreferenceItem {
  name: string;
  score: number;
  count: number;
}

interface UserPreference {
  preferred_styles: PreferenceItem[];
  preferred_colors: PreferenceItem[];
  preferred_scenes: PreferenceItem[];
  skin_tone: string | null;
  skin_undertone: string | null;
  preferred_length: string | null;
  preferred_shape: string | null;
  total_try_ons: number;
  total_favorites: number;
  total_candidates: number;
  total_bookings: number;
}

interface PersonalizedDesign {
  design: {
    id: number;
    name: string;
    image_url: string;
    style_tags: string[];
    color_tags: string[];
  };
  match_score: number;
  reasons: string[];
}

export default function ProfilePage() {
  const router = useRouter();
  const { user } = useValidatedUser('/profile');
  const [preferences, setPreferences] = useState<UserPreference | null>(null);
  const [recommendations, setRecommendations] = useState<PersonalizedDesign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    loadData();
  }, [user]);

  async function loadData() {
    setLoading(true);
    try {
      const [prefData, recData] = await Promise.all([
        api.getMyPreferences(),
        api.getMyPersonalizedRecommendations(),
      ]);
      setPreferences(prefData);
      setRecommendations(recData.recommendations || []);
    } catch (error) {
      console.error('Failed to load profile:', error);
    } finally {
      setLoading(false);
    }
  }

  const skinToneOptions = [
    { value: 'fair', label: '白皙', color: '#FFF5EB' },
    { value: 'light', label: '浅肤色', color: '#FFE4D1' },
    { value: 'medium', label: '自然', color: '#E8C4A0' },
    { value: 'tan', label: '小麦色', color: '#C4956A' },
    { value: 'dark', label: '深肤色', color: '#8B5A2B' },
  ];

  const undertoneOptions = [
    { value: 'warm', label: '暖调', desc: '适合金饰、橘红、大地色' },
    { value: 'cool', label: '冷调', desc: '适合银饰、玫红、蓝紫色' },
    { value: 'neutral', label: '中性', desc: '百搭，多数颜色都适合' },
  ];

  const handleSkinToneUpdate = async (tone: string, undertone?: string) => {
    try {
      await api.updateMySkinTone(tone, undertone);
      loadData();
    } catch (error) {
      console.error('Failed to update skin tone:', error);
    }
  };

  const hasBehaviorSignals = Boolean(
    (preferences?.total_try_ons || 0) +
    (preferences?.total_candidates || 0) +
    (preferences?.total_bookings || 0),
  );

  const handleLogout = () => {
    clearAuthSession();
    router.replace('/login');
  };

  return (
    <MobileShell>
      <header className="sticky top-0 z-50 border-b border-stone-200/70 bg-[#fbf7ef]/85 backdrop-blur-2xl">
        <div className="px-5 h-14 flex items-center">
          <Link href="/" className="flex items-center text-stone-600 hover:text-stone-950">
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回
          </Link>
          <h1 className="flex-1 text-center font-semibold text-stone-950">我的偏好画像</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="px-5 py-6 space-y-6">
        {loading ? (
          <div className="space-y-6 animate-pulse">
            <div className="bg-gray-200 rounded-2xl p-6 h-40" />
            <div className="bg-gray-200 rounded-2xl p-5 h-48" />
            <div className="bg-gray-200 rounded-2xl p-5 h-32" />
          </div>
        ) : (
          <>
            <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-400">账号管理</p>
                  <h2 className="mt-2 truncate text-xl font-bold text-stone-950">
                    {user?.nickname || '美甲试戴账号'}
                  </h2>
                  <p className="mt-1 text-sm text-stone-500">{user?.phone || '当前登录账号'}</p>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex shrink-0 items-center gap-2 rounded-full bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-200"
                >
                  <LogOut className="h-4 w-4" />
                  退出账号
                </button>
              </div>
            </section>

            {/* Stats Overview */}
            <section className="overflow-hidden rounded-[2rem] bg-stone-950 p-6 text-amber-50">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-amber-100/15 rounded-2xl flex items-center justify-center">
                  <User className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="font-semibold text-lg">你的美甲画像</h2>
                  <p className="text-amber-100/70 text-sm">基于你的试戴、候选和预约意向生成</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="bg-white/10 rounded-2xl p-3">
                  <p className="text-2xl font-bold">{preferences?.total_try_ons || 0}</p>
                  <p className="text-xs text-amber-100/70">试戴</p>
                </div>
                <div className="bg-white/10 rounded-2xl p-3">
                  <p className="text-2xl font-bold">{preferences?.total_candidates || 0}</p>
                  <p className="text-xs text-amber-100/70">候选</p>
                </div>
                <div className="bg-white/10 rounded-2xl p-3">
                  <p className="text-2xl font-bold">{preferences?.total_bookings || 0}</p>
                  <p className="text-xs text-amber-100/70">预约</p>
                </div>
              </div>
            </section>

            {/* Skin Tone Settings */}
            <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <Palette className="w-5 h-5 text-stone-700" />
                <h3 className="font-semibold text-stone-950">肤色与色调</h3>
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600 mb-3">选择你的肤色</p>
                  <div className="flex gap-2">
                    {skinToneOptions.map((tone) => (
                      <button
                        key={tone.value}
                        onClick={() => handleSkinToneUpdate(tone.value, preferences?.skin_undertone || undefined)}
                        className={`flex-1 py-2 rounded-xl text-xs font-medium transition-all ${
                          preferences?.skin_tone === tone.value
                            ? 'bg-stone-950 text-amber-50 shadow-md'
                            : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                        }`}
                      >
                        <span
                          className="w-4 h-4 rounded-full inline-block mr-1 border border-gray-300"
                          style={{ backgroundColor: tone.color }}
                        />
                        {tone.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-sm text-gray-600 mb-3">选择你的肤色调</p>
                  <div className="grid grid-cols-3 gap-2">
                    {undertoneOptions.map((tone) => (
                      <button
                        key={tone.value}
                        onClick={() => handleSkinToneUpdate(preferences?.skin_tone || 'medium', tone.value)}
                        className={`p-3 rounded-xl text-center transition-all ${
                          preferences?.skin_undertone === tone.value
                            ? 'bg-stone-950 text-amber-50 shadow-md'
                            : 'bg-[#fbf7ef] text-stone-600 hover:bg-stone-100'
                        }`}
                      >
                        <p className="font-medium text-sm">{tone.label}</p>
                        <p className={`text-xs mt-1 ${preferences?.skin_undertone === tone.value ? 'text-amber-100/70' : 'text-stone-400'}`}>
                          {tone.desc}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            {/* Preferred Styles */}
            {preferences?.preferred_styles && preferences.preferred_styles.length > 0 ? (
              <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-5 h-5 text-stone-700" />
                  <h3 className="font-semibold text-stone-950">偏好的风格</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {preferences.preferred_styles.map((style) => (
                    <div
                      key={style.name}
                      className="flex items-center gap-2 bg-amber-50 text-amber-900 px-3 py-2 rounded-full"
                    >
                      <span className="font-medium">{style.name}</span>
                      <span className="text-xs text-amber-600">{style.count}次</span>
                    </div>
                  ))}
                </div>
              </section>
            ) : hasBehaviorSignals ? null : (
              <section className="rounded-[2rem] border border-dashed border-stone-300 bg-white p-6 text-center shadow-sm">
                <Camera className="mx-auto mb-3 h-10 w-10 text-stone-300" />
                <h3 className="font-semibold text-stone-950">还没有足够行为生成画像</h3>
                <p className="mt-2 text-sm leading-6 text-stone-500">
                  完成一次试戴、加入候选或提交预约意向后，这里会自动沉淀你的真实风格偏好。
                </p>
                <Link
                  href="/designs?source=profile-empty"
                  className="mt-4 inline-flex rounded-2xl bg-stone-950 px-5 py-3 text-sm font-semibold text-amber-50"
                >
                  去选择款式
                </Link>
              </section>
            )}

            {/* Preferred Colors */}
            {preferences?.preferred_colors && preferences.preferred_colors.length > 0 && (
              <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <Palette className="w-5 h-5 text-stone-700" />
                  <h3 className="font-semibold text-stone-950">偏好的颜色</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {preferences.preferred_colors.map((color) => (
                    <div
                      key={color.name}
                      className="flex items-center gap-2 bg-stone-100 text-stone-700 px-3 py-2 rounded-full"
                    >
                      <span className="font-medium">{color.name}</span>
                      <span className="text-xs text-stone-400">{color.count}次</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Personalized Recommendations */}
            {recommendations.length > 0 ? (
              <section>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Bookmark className="w-5 h-5 text-stone-700" />
                    为你推荐
                  </h3>
                  <Link href="/designs?source=profile" className="text-sm font-medium text-stone-600">
                    查看更多
                  </Link>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {recommendations.slice(0, 4).map((rec) => (
                    <Link
                      key={rec.design.id}
                      href={`/tryon?design=${rec.design.id}&source=profile`}
                      className="bg-white rounded-[1.5rem] overflow-hidden shadow-sm border border-stone-200"
                    >
                      <div className="aspect-square bg-gray-100">
                        <img
                          src={rec.design.image_url}
                          alt={rec.design.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="p-3">
                        <p className="font-medium text-sm text-stone-950 truncate">{rec.design.name}</p>
                        <p className="text-xs text-amber-700 mt-1">匹配度 {Math.round(rec.match_score)}%</p>
                        <p className="text-xs text-gray-400 mt-1 truncate">{rec.reasons[0]}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            ) : hasBehaviorSignals ? (
              <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
                <h3 className="font-semibold text-stone-950 flex items-center gap-2">
                  <Bookmark className="w-5 h-5 text-stone-700" />
                  为你推荐
                </h3>
                <p className="mt-2 text-sm leading-6 text-stone-500">
                  暂时没有新的高匹配款式。可以去全部款式页继续浏览，系统会随着你的行为更新推荐。
                </p>
                <Link href="/designs?source=profile" className="mt-4 inline-flex rounded-2xl bg-stone-950 px-5 py-3 text-sm font-semibold text-amber-50">
                  查看全部款式
                </Link>
              </section>
            ) : null}

            {/* Preferred Length & Shape */}
            {(preferences?.preferred_length || preferences?.preferred_shape) && (
              <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <Calendar className="w-5 h-5 text-stone-700" />
                  <h3 className="font-semibold text-stone-950">甲型偏好</h3>
                </div>
                <div className="flex gap-4">
                  {preferences.preferred_length && (
                    <div className="flex-1 bg-[#fbf7ef] rounded-2xl p-4 text-center">
                      <p className="text-xs text-gray-500 mb-1">长度偏好</p>
                      <p className="font-semibold text-gray-900">{preferences.preferred_length}</p>
                    </div>
                  )}
                  {preferences.preferred_shape && (
                    <div className="flex-1 bg-[#fbf7ef] rounded-2xl p-4 text-center">
                      <p className="text-xs text-gray-500 mb-1">形状偏好</p>
                      <p className="font-semibold text-gray-900">{preferences.preferred_shape}</p>
                    </div>
                  )}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </MobileShell>
  );
}
