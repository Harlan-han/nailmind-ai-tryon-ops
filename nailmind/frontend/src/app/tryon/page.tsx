'use client';

import { ChangeEvent, Suspense, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  Bookmark,
  Camera,
  Check,
  Copy,
  MessageCircle,
  Download,
  Image as ImageIcon,
  Loader2,
  Send,
  Phone,
  RotateCcw,
  Share2,
  Sparkles,
  Upload,
} from 'lucide-react';
import { API_BASE_URL, api, TryOnRecord } from '@/lib/api';
import { getAuthToken, getCurrentUserId, requireLogin } from '@/lib/auth';
import {
  clearPendingTryOn,
  getPendingTryOnId,
  getStoredHandPhoto,
  resetFailedTryOnForRetry,
  saveCurrentHandPhoto,
  saveCurrentTryOnSession,
} from '@/lib/tryon-session';
import {
  isDesignCandidate,
  toggleDesignCandidate as toggleStoredDesignCandidate,
} from '@/lib/design-candidates';
import { useValidatedUser } from '@/lib/use-validated-user';

interface Design {
  id: number;
  name: string;
  image_url: string;
  style_tags: string[];
  color_tags: string[];
  scene_tags?: string[];
  shape?: string;
  description: string;
  try_on_count: number;
  favorite_count: number;
}

interface Recommendation {
  id: number;
  name: string;
  image_url: string;
  style_tags: string[];
  reason?: string;
}

interface RecommendationItemResponse {
  design: {
    id: number;
    name: string;
    image_url: string;
    style_tags?: string[];
  };
  reason?: string;
}

interface HandPhoto {
  id: number;
  image_url: string;
  thumbnail_url?: string;
  created_at?: string;
}

type ViewMode = 'result' | 'original';

interface DesignComment {
  content: string;
  author_name: string;
  user_id: number | null;
  created_at: string;
}

function TryOnContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const designId = searchParams.get('design');
  const tryOnId = searchParams.get('id');
  const validated = useValidatedUser(`/tryon${tryOnId ? `?id=${tryOnId}` : designId ? `?design=${designId}` : ''}`);

  const [design, setDesign] = useState<Design | null>(null);
  const [tryOn, setTryOn] = useState<TryOnRecord | null>(null);
  const [handPreviewUrl, setHandPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [storedHandPhotoId, setStoredHandPhotoId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('result');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [handPhotos, setHandPhotos] = useState<HandPhoto[]>([]);
  const [showArchivePicker, setShowArchivePicker] = useState(false);
  const [designCandidate, setDesignCandidate] = useState(false);
  const [comments, setComments] = useState<DesignComment[]>([]);
  const [commentText, setCommentText] = useState('');
  const [bookingPhone, setBookingPhone] = useState(() =>
    typeof window === 'undefined' ? '' : localStorage.getItem('booking_phone') || ''
  );
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [bookingMessage, setBookingMessage] = useState<string | null>(null);
  const [showShareSheet, setShowShareSheet] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const [shareToast, setShareToast] = useState<string | null>(null);
  const user = validated.user;
  const generationStartedRef = useRef(false);
  const shareToastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!user) return;
    if (tryOnId) return;
    api.getMyHandPhotos()
      .then((data) => {
        setHandPhotos(data);
        const stored = getStoredHandPhoto();
        if (stored.id) {
          const current = (data as HandPhoto[]).find((photo) => photo.id === stored.id);
          if (current) {
            saveCurrentHandPhoto(current);
            setStoredHandPhotoId(current.id);
            setHandPreviewUrl(current.image_url);
          }
        }
      })
      .catch(() => setHandPhotos([]));
  }, [user, tryOnId]);

  useEffect(() => {
    if (!design) return;
    let active = true;
    const currentDesign = design;

    async function loadDesignNotes() {
      await Promise.resolve();
      if (!active) return;

      setDesignCandidate(isDesignCandidate(currentDesign.id));
      try {
        const userId = getCurrentUserId();
        const rawComments = JSON.parse(localStorage.getItem(`design_comments_user_${userId || 'guest'}_${currentDesign.id}`) || '[]');
        setComments(
          rawComments.map((comment: string | DesignComment) =>
            typeof comment === 'string'
              ? {
                  content: comment,
                  author_name: user?.nickname || '试戴用户',
                  user_id: userId,
                  created_at: new Date().toISOString(),
                }
              : comment
          )
        );
      } catch {
        setComments([]);
      }
    }

    loadDesignNotes();
    return () => {
      active = false;
    };
  }, [design, user]);

  useEffect(() => () => {
    if (shareToastTimerRef.current) {
      clearTimeout(shareToastTimerRef.current);
    }
  }, []);

  const normalizeDesign = (source: Partial<Design> & { id: number; name: string; image_url: string }): Design => ({
    id: source.id,
    name: source.name,
    image_url: source.image_url,
    style_tags: source.style_tags || [],
    color_tags: source.color_tags || [],
    scene_tags: source.scene_tags || [],
    shape: source.shape,
    description: source.description || '适合日常、约会和通勤场景的美甲模板。',
    try_on_count: source.try_on_count || 0,
    favorite_count: source.favorite_count || 0,
  });

  async function loadDesign(id: number) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDesign(id);
      setDesign(normalizeDesign(data));
    } catch (err) {
      console.error(err);
      setError('模板加载失败，请返回重新选择');
    } finally {
      setLoading(false);
    }
  }

  async function loadRecommendations(recordId: number, currentDesignId: number) {
    try {
      const data = await api.getRecommendations(recordId) as {
        similar_designs?: RecommendationItemResponse[];
        better_for_you?: RecommendationItemResponse[];
      };
      const items = [
        ...(data.similar_designs || []).map((item) => ({ ...item.design, style_tags: item.design.style_tags || [], reason: item.reason || '相似风格' })),
        ...(data.better_for_you || []).map((item) => ({ ...item.design, style_tags: item.design.style_tags || [], reason: item.reason || '可能更适合你' })),
      ];
      const unique = items.filter((item, index, self) => item.id !== currentDesignId && index === self.findIndex((next) => next.id === item.id));
      setRecommendations(unique.slice(0, 4));
    } catch (err) {
      console.error(err);
    }
  }

  async function resolveHandPhotoForTryOn(tryOnRecord: TryOnRecord) {
    const photos = await api.getMyHandPhotos() as HandPhoto[];
    setHandPhotos(photos);
    const photo = photos.find((item) => item.id === tryOnRecord.hand_photo_id);
    if (!photo) {
      return null;
    }
    saveCurrentHandPhoto(photo);
    setStoredHandPhotoId(photo.id);
    setHandPreviewUrl(photo.image_url);
    return photo;
  }

  async function loadTryOn(id: number) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTryOn(id);
      setTryOn(data);
      const handPhoto = await resolveHandPhotoForTryOn(data);
      saveCurrentTryOnSession(data, handPhoto?.image_url);

      if (data.nail_design) {
        setDesign(normalizeDesign(data.nail_design));
      } else {
        const designData = await api.getDesign(data.nail_design_id);
        setDesign(normalizeDesign(designData));
      }

      if (data.status === 'pending' || data.status === 'processing') {
        router.replace('/processing');
        return;
      }
      if (data.status === 'failed' || data.status === 'fallback_completed') {
        resetFailedTryOnForRetry(data);
        router.replace(`/tryon?design=${data.nail_design_id}`);
        return;
      }

      await loadRecommendations(data.id, data.nail_design_id);
    } catch (err) {
      console.error(err);
      setError('试戴结果加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function loadInitialView() {
      await Promise.resolve();
      if (!active) return;

      const stored = getStoredHandPhoto();
      setStoredHandPhotoId(stored.id);
      setHandPreviewUrl(stored.url);

      if (tryOnId) {
        await loadTryOn(Number(tryOnId));
        return;
      }
      if (designId) {
        await loadDesign(Number(designId));
        return;
      }
      setLoading(false);
    }

    void loadInitialView();
    return () => {
      active = false;
    };
  }, [designId, tryOnId, validated.user]);

  const handleFileSelect = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setStoredHandPhotoId(null);
    setError(null);
    const reader = new FileReader();
    reader.onload = (readerEvent) => {
      setHandPreviewUrl(readerEvent.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const selectArchivePhoto = (photo: HandPhoto) => {
    setSelectedFile(null);
    setStoredHandPhotoId(photo.id);
    setHandPreviewUrl(photo.image_url);
    saveCurrentHandPhoto(photo);
    setShowArchivePicker(false);
  };

  const uploadHandPhoto = async () => {
    if (!user) {
      router.push(requireLogin(`/tryon${designId ? `?design=${designId}` : ''}`));
      throw new Error('请先登录后再生成试戴');
    }
    if (!selectedFile) {
      if (storedHandPhotoId && handPreviewUrl) {
        return { id: storedHandPhotoId, image_url: handPreviewUrl };
      }
      throw new Error('请先上传手部照片');
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    const uploadResponse = await fetch(`${API_BASE_URL}/upload/hand-photo`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getAuthToken() || ''}`,
      },
      body: formData,
    });
    if (!uploadResponse.ok) {
      throw new Error('照片上传失败');
    }
    const uploaded = await uploadResponse.json();

    const photo = await api.uploadMyHandPhoto({ image_url: uploaded.url });
    saveCurrentHandPhoto(photo);
    setStoredHandPhotoId(photo.id);
    return photo;
  };

  const startGeneration = async () => {
    if (!design) return;
    if (!user) {
      router.push(requireLogin(`/tryon?design=${design.id}`));
      return;
    }
    if (generationStartedRef.current) return;
    generationStartedRef.current = true;
    setUploading(true);
    setError(null);
    try {
      const photo = await uploadHandPhoto();
      const pendingTryOnId = getPendingTryOnId(design.id, photo.id);
      if (pendingTryOnId) {
        const existing = await api.getTryOn(pendingTryOnId);
        if (existing.status === 'pending' || existing.status === 'processing') {
          saveCurrentTryOnSession(existing, photo.image_url);
          router.push('/processing');
          return;
        }
        if (existing.status === 'completed' && existing.result_image_url) {
          saveCurrentTryOnSession(existing, photo.image_url);
          router.push(`/tryon?id=${existing.id}`);
          return;
        }
        clearPendingTryOn(design.id, photo.id);
      }

      const created = await api.createTryOn({
        hand_photo_id: photo.id,
        nail_design_id: design.id,
      });
      saveCurrentTryOnSession(created, photo.image_url, { resetStartedAt: true });
      router.push('/processing');
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : '生成发起失败，请重试');
    } finally {
      setUploading(false);
      generationStartedRef.current = false;
    }
  };

  const toggleCandidate = async () => {
    if (!tryOn) return;
    await api.toggleCandidate(tryOn.id);
    setTryOn({ ...tryOn, is_candidate: !tryOn.is_candidate });
  };

  const showShareToast = (message: string) => {
    setShareToast(message);
    if (shareToastTimerRef.current) {
      clearTimeout(shareToastTimerRef.current);
    }
    shareToastTimerRef.current = setTimeout(() => setShareToast(null), 1800);
  };

  const copyShareLink = async () => {
    const url = window.location.href;
    window.focus();
    let copiedByEvent = false;
    const copyHandler = (event: ClipboardEvent) => {
      event.clipboardData?.setData('text/plain', url);
      event.preventDefault();
      copiedByEvent = true;
    };
    document.addEventListener('copy', copyHandler);
    try {
      if (document.execCommand('copy') || copiedByEvent) {
        return true;
      }
    } catch {
      // Continue with input selection fallback.
    } finally {
      document.removeEventListener('copy', copyHandler);
    }

    const textarea = document.createElement('textarea');
    textarea.value = url;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.inset = '0 auto auto 0';
    textarea.style.width = '1px';
    textarea.style.height = '1px';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
    try {
      if (document.execCommand('copy')) {
        return true;
      }
    } catch {
      // Ignore and try the async Clipboard API below.
    } finally {
      document.body.removeChild(textarea);
    }
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(url);
        return true;
      } catch {
        // Browser permission can reject Clipboard API; the UI handles the final failure.
      }
    }
    return false;
  };

  const openShareSheet = () => {
    setShowShareSheet(true);
    setShareToast(null);
    setShareCopied(false);
  };

  const copyShareFromSheet = async () => {
    await copyShareLink();
    setShareCopied(true);
    showShareToast('链接已复制');
  };

  const toggleDesignCandidate = () => {
    if (!design) return;
    const next = toggleStoredDesignCandidate({
      id: design.id,
      name: design.name,
      image_url: design.image_url,
      style_tags: design.style_tags || [],
      color_tags: design.color_tags || [],
    });
    setDesignCandidate(next);
  };

  const submitComment = () => {
    if (!design || !commentText.trim()) return;
    const userId = getCurrentUserId();
    const nextComments = [
      {
        content: commentText.trim(),
        author_name: user?.nickname || '试戴用户',
        user_id: userId,
        created_at: new Date().toISOString(),
      },
      ...comments,
    ].slice(0, 6);
    setComments(nextComments);
    localStorage.setItem(`design_comments_user_${userId || 'guest'}_${design.id}`, JSON.stringify(nextComments));
    setCommentText('');
  };

  const downloadResult = () => {
    const imageUrl = tryOn?.result_image_url;
    if (!imageUrl) return;
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `nailmind-tryon-${tryOn.id}.png`;
    link.click();
  };

  const submitBookingIntent = async () => {
    if (!tryOn || !design) return;
    if (!user) {
      router.push(requireLogin(`/tryon?id=${tryOn.id}`));
      return;
    }
    const phone = bookingPhone.trim();
    if (!phone) {
      setBookingMessage('请先填写手机号，方便商家跟进。');
      return;
    }

    setBookingSubmitting(true);
    setBookingMessage(null);
    try {
      await api.createBookingIntent(
        {
          try_on_record_id: tryOn.id,
          nail_design_id: tryOn.nail_design_id,
          phone,
          notes: `来自试戴结果页：${design.name}`,
        }
      );
      localStorage.setItem('booking_phone', phone);
      setTryOn({ ...tryOn, has_booking_intent: true });
      setBookingMessage('预约意向已提交，运营端会进入跟进队列。');
    } catch (err) {
      console.error(err);
      setBookingMessage('预约提交失败，请稍后再试。');
    } finally {
      setBookingSubmitting(false);
    }
  };

  if (loading) {
    return <LoadingScreen text="正在加载模板..." />;
  }

  if (tryOnId && tryOn) {
    const imageUrl = viewMode === 'original' ? handPreviewUrl : tryOn.result_image_url;
    return (
      <MobileShell title="试戴结果" backHref="/records">
        <section className="px-5 pt-4">
          <div className="overflow-hidden rounded-[2rem] bg-white shadow-sm">
            <div className="relative aspect-[4/5] bg-stone-100">
              {imageUrl ? (
                <img src={imageUrl} alt="试戴图片" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center text-stone-400">暂无图片</div>
              )}
              <div className="absolute left-3 top-3 rounded-full bg-black/55 px-3 py-1 text-xs text-white backdrop-blur">
                {viewMode === 'original' ? '原始手照' : 'AI 试戴'}
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 rounded-2xl bg-stone-100 p-1">
            <button
              onClick={() => setViewMode('result')}
              className={viewMode === 'result' ? 'rounded-xl bg-white py-2 text-sm font-semibold shadow-sm' : 'py-2 text-sm text-stone-500'}
            >
              试戴效果
            </button>
            <button
              onClick={() => setViewMode('original')}
              className={viewMode === 'original' ? 'rounded-xl bg-white py-2 text-sm font-semibold shadow-sm' : 'py-2 text-sm text-stone-500'}
            >
              原始照片
            </button>
          </div>
        </section>

        <DesignInfo design={design} showImage />

        <section className="grid grid-cols-3 gap-3 px-5">
          <ActionButton active={tryOn.is_candidate} icon={Bookmark} label={tryOn.is_candidate ? '已入清单' : '入清单'} onClick={toggleCandidate} />
          <ActionButton icon={Share2} label="分享" onClick={openShareSheet} />
          <ActionButton icon={Download} label="下载" onClick={downloadResult} />
        </section>

        <section className="px-5">
          <div className="rounded-[2rem] bg-white p-4 shadow-sm">
            {tryOn.has_booking_intent ? (
              <div className="rounded-2xl bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
                <div className="flex items-center gap-2 font-semibold">
                  <Check className="h-5 w-5" />
                  已提交预约意向
                </div>
                <p className="mt-2 text-emerald-700">商家会在运营端看到这条试戴转化，并继续跟进到店确认。</p>
              </div>
            ) : (
              <>
                <div className="mb-3">
                  <h3 className="font-bold">预约到店体验</h3>
                  <p className="mt-1 text-sm text-stone-500">留下手机号，这次试戴会同步进入商家跟进队列。</p>
                </div>
                <div className="flex gap-2">
                  <input
                    value={bookingPhone}
                    onChange={(event) => setBookingPhone(event.target.value)}
                    placeholder="输入手机号"
                    inputMode="tel"
                    className="min-w-0 flex-1 rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none focus:border-stone-950"
                  />
                  <button
                    type="button"
                    onClick={submitBookingIntent}
                    disabled={bookingSubmitting}
                    className="flex shrink-0 items-center justify-center gap-2 rounded-2xl bg-stone-950 px-4 py-3 text-sm font-semibold text-amber-50 disabled:opacity-50"
                  >
                    {bookingSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Phone className="h-4 w-4" />}
                    提交
                  </button>
                </div>
              </>
            )}
            {bookingMessage && <p className="mt-3 text-sm text-stone-600">{bookingMessage}</p>}
          </div>
        </section>

        {recommendations.length > 0 && (
          <section className="px-5 pb-8">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-bold">还可以试试</h3>
              <Link href="/" className="text-sm text-stone-500">更多模板</Link>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {recommendations.map((item) => (
                <Link key={item.id} href={`/tryon?design=${item.id}`} className="overflow-hidden rounded-2xl bg-white shadow-sm">
                  <div className="aspect-square bg-stone-100">
                    <img src={item.image_url} alt={item.name} className="h-full w-full object-cover" />
                  </div>
                  <div className="p-3">
                    <p className="line-clamp-1 text-sm font-semibold">{item.name}</p>
                    <p className="mt-1 line-clamp-1 text-xs text-stone-500">{item.reason}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
        <ShareSheet
          open={showShareSheet}
          copied={shareCopied}
          toast={shareToast}
          onClose={() => setShowShareSheet(false)}
          onCopy={copyShareFromSheet}
        />
      </MobileShell>
    );
  }

  return (
    <MobileShell title="模板详情" backHref="/">
      {error && <p className="mx-5 mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <section className="px-5 pt-4">
        <div className="overflow-hidden rounded-[2rem] bg-white shadow-sm">
          <div className="aspect-[4/5] bg-stone-100">
            {design && <img src={design.image_url} alt={design.name} className="h-full w-full object-cover" />}
          </div>
        </div>
      </section>

      <DesignInfo design={design} />

      <section className="grid grid-cols-3 gap-3 px-5">
        <ActionButton active={designCandidate} icon={Bookmark} label={designCandidate ? '已入清单' : '加入清单'} onClick={toggleDesignCandidate} />
        <ActionButton icon={MessageCircle} label={`${comments.length} 评论`} onClick={() => document.getElementById('design-comments')?.scrollIntoView({ behavior: 'smooth' })} />
        <ActionButton icon={Share2} label="转发" onClick={openShareSheet} />
      </section>

      <section className="px-5">
        <div className="rounded-[2rem] bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="font-bold">上传手部照片</h3>
              <p className="mt-1 text-sm text-stone-500">只有点击生成后才会创建新任务</p>
            </div>
            <button
              type="button"
              onClick={() => setShowArchivePicker((current) => !current)}
              className="rounded-full bg-stone-100 px-3 py-1.5 text-xs font-semibold text-stone-600"
            >
              切换档案
            </button>
          </div>

          {showArchivePicker && (
            <div className="mb-4 flex gap-3 overflow-x-auto pb-1">
              {handPhotos.length === 0 ? (
                <Link href="/upload" className="w-full rounded-2xl border border-dashed border-stone-300 p-4 text-center text-sm text-stone-500">
                  还没有档案，去新增
                </Link>
              ) : (
                handPhotos.map((photo) => (
                  <button
                    key={photo.id}
                    type="button"
                    onClick={() => selectArchivePhoto(photo)}
                    className={
                      storedHandPhotoId === photo.id
                        ? 'w-20 shrink-0 overflow-hidden rounded-2xl border-2 border-stone-950 bg-stone-950 text-xs text-amber-50'
                        : 'w-20 shrink-0 overflow-hidden rounded-2xl border border-stone-200 bg-stone-50 text-xs text-stone-500'
                    }
                  >
                    <img src={photo.thumbnail_url || photo.image_url} alt="手部档案" className="aspect-square w-full object-cover" />
                    <span className="block truncate px-2 py-2">{storedHandPhotoId === photo.id ? '当前' : '切换'}</span>
                  </button>
                ))
              )}
            </div>
          )}

          {handPreviewUrl ? (
            <div className="overflow-hidden rounded-2xl bg-stone-100">
              <img src={handPreviewUrl} alt="手部预览" className="aspect-square w-full object-cover" />
            </div>
          ) : (
            <label className="block cursor-pointer rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-8 text-center">
              <Upload className="mx-auto mb-3 h-8 w-8 text-stone-400" />
              <p className="font-semibold">点击上传手照</p>
              <p className="mt-1 text-sm text-stone-500">建议自然光、指甲完整露出</p>
              <input type="file" accept="image/*" className="hidden" onChange={handleFileSelect} />
            </label>
          )}

          {handPreviewUrl && (
            <label className="mt-3 block cursor-pointer rounded-2xl border border-stone-200 px-4 py-3 text-center text-sm font-medium text-stone-600">
              重新上传
              <input type="file" accept="image/*" className="hidden" onChange={handleFileSelect} />
            </label>
          )}
        </div>
      </section>

      <section id="design-comments" className="px-5">
        <div className="rounded-[2rem] bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-bold">评论与笔记</h3>
            <span className="text-xs text-stone-400">本地体验版</span>
          </div>
          <div className="flex gap-2">
            <input
              value={commentText}
              onChange={(event) => setCommentText(event.target.value)}
              placeholder="记录你对这款的想法"
              className="min-w-0 flex-1 rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none focus:border-stone-500"
            />
            <button
              type="button"
              onClick={submitComment}
              className="flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-950 text-amber-50"
              aria-label="发布评论"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-4 space-y-2">
            {comments.length === 0 ? (
              <p className="rounded-2xl bg-stone-50 px-4 py-3 text-sm text-stone-500">还没有评论，可以先写一条试戴笔记。</p>
            ) : (
              comments.map((comment, index) => (
                <div key={`${comment.content}-${index}`} className="rounded-2xl bg-stone-50 px-4 py-3 text-sm text-stone-700">
                  <div className="mb-1 flex items-center justify-between gap-3 text-xs text-stone-400">
                    <span className="font-semibold text-stone-600">{comment.author_name}</span>
                    <span>{new Date(comment.created_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}</span>
                  </div>
                  <p>{comment.content}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="sticky bottom-0 mt-6 border-t border-stone-200 bg-[#fbf7ef]/90 p-5 backdrop-blur-2xl">
        <button
          onClick={startGeneration}
          disabled={!design || !handPreviewUrl || uploading}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-stone-950 py-4 font-semibold text-amber-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {uploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Sparkles className="h-5 w-5" />}
          {uploading ? '正在发起生成' : '生成 AI 试戴'}
        </button>
      </section>
      <ShareSheet
        open={showShareSheet}
        copied={shareCopied}
        toast={shareToast}
        onClose={() => setShowShareSheet(false)}
        onCopy={copyShareFromSheet}
      />
    </MobileShell>
  );
}

const shareTargets = [
  { label: '微信', className: 'bg-emerald-500 text-white', icon: MessageCircle },
  { label: '朋友圈', className: 'bg-lime-500 text-white', icon: Share2 },
  { label: '小红书', className: 'bg-red-500 text-white', icon: Bookmark },
  { label: '微博', className: 'bg-orange-400 text-white', icon: MessageCircle },
  { label: '复制链接', className: 'bg-stone-950 text-amber-50', icon: Copy },
];

function ShareSheet({
  open,
  copied,
  toast,
  onClose,
  onCopy,
}: {
  open: boolean;
  copied: boolean;
  toast: string | null;
  onClose: () => void;
  onCopy: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/35 px-3 pb-3 backdrop-blur-sm">
      <div className="w-full max-w-[420px] overflow-hidden rounded-[2rem] bg-[#f7f2eb] shadow-2xl">
        <div className="px-5 pb-3 pt-4 text-center">
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-stone-300" />
          <h3 className="text-lg font-bold text-stone-950">分享试戴结果</h3>
          <p className="mt-1 text-sm text-stone-500">
            {copied ? '链接已复制，可以粘贴发送给好友。' : '选择分享方式，系统会复制当前结果链接。'}
          </p>
        </div>

        {toast && (
          <div className="mx-5 mb-4 rounded-2xl bg-stone-950 px-4 py-3 text-center text-sm font-semibold text-amber-50 shadow-lg">
            {toast}
          </div>
        )}

        <div className="flex gap-3 overflow-x-auto px-5 pb-5">
          {shareTargets.map((target) => {
            const Icon = target.icon;
            return (
              <button
                key={target.label}
                type="button"
                onClick={onCopy}
                className="w-20 shrink-0 text-center"
              >
                <span className={`mx-auto flex h-14 w-14 items-center justify-center rounded-2xl ${target.className}`}>
                  <Icon className="h-6 w-6" />
                </span>
                <span className="mt-2 block text-xs font-semibold text-stone-800">{target.label}</span>
              </button>
            );
          })}
        </div>

        <div className="border-t border-stone-200 bg-white/70 p-3">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-2xl bg-white py-3 text-sm font-semibold text-stone-800 shadow-sm"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}

function DesignInfo({ design, showImage = false }: { design: Design | null; showImage?: boolean }) {
  if (!design) return null;
  return (
    <section className="px-5 py-4">
      <div className="rounded-[2rem] bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="flex min-w-0 gap-3">
            {showImage && (
              <div className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-stone-100">
                <img src={design.image_url} alt={design.name} className="h-full w-full object-cover" />
              </div>
            )}
            <div className="min-w-0">
            <h2 className="text-xl font-bold">{design.name}</h2>
            <p className="mt-1 text-sm leading-6 text-stone-500">{design.description}</p>
            </div>
          </div>
          <div className="rounded-2xl bg-stone-100 px-3 py-2 text-right text-xs text-stone-500">
            <p className="font-bold text-stone-900">{design.try_on_count}</p>
            试戴
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {[...(design.style_tags || []), ...(design.color_tags || [])].slice(0, 5).map((tag) => (
            <span key={tag} className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-600">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function ActionButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active?: boolean;
  icon: typeof Bookmark;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={active ? 'rounded-2xl bg-rose-50 p-3 text-rose-600' : 'rounded-2xl bg-white p-3 text-stone-600 shadow-sm'}
    >
      <Icon className={active ? 'mx-auto h-5 w-5 fill-current' : 'mx-auto h-5 w-5'} />
      <span className="mt-1 block text-xs">{label}</span>
    </button>
  );
}

function MobileShell({ title, backHref, children }: { title: string; backHref: string; children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f7f2eb] text-stone-950">
      <main className="mx-auto min-h-screen max-w-[430px] bg-[#fbf7ef] shadow-2xl shadow-stone-200/80">
        <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-[#fbf7ef]/85 px-5 py-4 backdrop-blur-2xl">
          <div className="flex items-center justify-between">
            <Link href={backHref} className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-stone-700 shadow-sm">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <h1 className="font-bold">{title}</h1>
            <Link href="/records" className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-stone-700 shadow-sm">
              <RotateCcw className="h-5 w-5" />
            </Link>
          </div>
        </header>
        <div className="space-y-4">{children}</div>
      </main>
    </div>
  );
}

function LoadingScreen({ text }: { text: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#fbf7ef] text-stone-500">
      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
      {text}
    </div>
  );
}

export default function TryOnPage() {
  return (
    <Suspense fallback={<LoadingScreen text="加载中..." />}>
      <TryOnContent />
    </Suspense>
  );
}
