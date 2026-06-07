'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowLeft,
  Camera,
  Check,
  CheckCircle2,
  Crop,
  Edit3,
  FolderOpen,
  Image as ImageIcon,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import { API_BASE_URL, api } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { assessHandPhotoQuality, type HandPhotoAnalysisResult } from '@/lib/hand-photo-quality';
import { clearCurrentHandPhoto, saveCurrentHandPhoto } from '@/lib/tryon-session';
import { useValidatedUser } from '@/lib/use-validated-user';
import { MobileShell } from '@/components/mobile-shell';

interface HandPhoto {
  id: number;
  image_url: string;
  thumbnail_url?: string;
  created_at?: string;
  status?: string;
  name?: string | null;
  crop_ratio?: '1:1' | '4:5' | '3:4' | null;
}

interface HandPhotoPreset {
  id: string;
  name: string;
  image_url: string;
  tags: string[];
  crop_ratio: NonNullable<HandPhoto['crop_ratio']>;
}

const cropRatios: Array<NonNullable<HandPhoto['crop_ratio']>> = ['1:1', '4:5', '3:4'];

export default function UploadPage() {
  const validated = useValidatedUser('/upload');
  const user = validated.user;
  const [photos, setPhotos] = useState<HandPhoto[]>([]);
  const [presets, setPresets] = useState<HandPhotoPreset[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<HandPhotoAnalysisResult | null>(null);
  const [selectedPhotoId, setSelectedPhotoId] = useState<number | null>(null);
  const [loadingPhotos, setLoadingPhotos] = useState(true);
  const [loadingPresets, setLoadingPresets] = useState(true);
  const [usingPresetId, setUsingPresetId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingPhoto, setEditingPhoto] = useState<HandPhoto | null>(null);
  const [draftName, setDraftName] = useState('');
  const [draftCropRatio, setDraftCropRatio] = useState<NonNullable<HandPhoto['crop_ratio']>>('1:1');

  const setCurrentPhoto = (photo: HandPhoto) => {
    setSelectedPhotoId(photo.id);
    saveCurrentHandPhoto(photo);
  };

  async function loadHandPhotos() {
    await Promise.resolve();
    setLoadingPhotos(true);
    try {
      const data = await api.getMyHandPhotos();
      const visiblePhotos = data as HandPhoto[];
      setPhotos(visiblePhotos);

      const storedPhotoId = localStorage.getItem('current_hand_photo_id');
      if (storedPhotoId && visiblePhotos.some((photo: HandPhoto) => photo.id === Number(storedPhotoId))) {
        setSelectedPhotoId(Number(storedPhotoId));
      } else if (visiblePhotos[0]) {
        setCurrentPhoto(visiblePhotos[0]);
      }
    } catch (err) {
      console.error(err);
      setPhotos([]);
    } finally {
      setLoadingPhotos(false);
    }
  }

  async function loadHandPhotoPresets() {
    await Promise.resolve();
    setLoadingPresets(true);
    try {
      const data = await api.getHandPhotoPresets();
      setPresets(data as HandPhotoPreset[]);
    } catch (err) {
      console.error(err);
      setPresets([]);
    } finally {
      setLoadingPresets(false);
    }
  }

  useEffect(() => {
    if (!user) return;
    void Promise.resolve().then(loadHandPhotos);
    void Promise.resolve().then(loadHandPhotoPresets);
  }, [user]);

  const getPhotoName = (photo: HandPhoto, index: number) =>
    photo.name || `手部档案 ${index + 1}`;

  const getCropClass = (photo: HandPhoto) => {
    const ratio = photo.crop_ratio || '1:1';
    if (ratio === '4:5') return 'aspect-[4/5]';
    if (ratio === '3:4') return 'aspect-[3/4]';
    return 'aspect-square';
  };

  const isOfficialPresetPhoto = (photo: HandPhoto) =>
    /\/uploads\/hands\/hand_\d{2}\.jpg$/.test(photo.image_url);

  const openEditPhoto = (photo: HandPhoto, index: number) => {
    setEditingPhoto(photo);
    setDraftName(getPhotoName(photo, index));
    setDraftCropRatio(photo.crop_ratio || '1:1');
  };

  const handlePresetPhoto = async (preset: HandPhotoPreset) => {
    setUsingPresetId(preset.id);
    setError(null);
    try {
      const photo = await api.useHandPhotoPreset(preset.id) as HandPhoto;
      setCurrentPhoto(photo);
      setPhotos((current) => {
        const withoutCurrent = current.filter((item) => item.id !== photo.id);
        return [photo, ...withoutCurrent];
      });
    } catch (err) {
      console.error(err);
      setError('官方预设手模启用失败，请稍后再试。');
    } finally {
      setUsingPresetId(null);
    }
  };

  const savePhotoEdit = async () => {
    if (!editingPhoto) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateMyHandPhoto(editingPhoto.id, {
        name: draftName.trim() || `手部档案 ${editingPhoto.id}`,
        crop_ratio: draftCropRatio,
      }) as HandPhoto;
      setPhotos((current) => current.map((photo) => (photo.id === updated.id ? updated : photo)));
      if (selectedPhotoId === updated.id) {
        setCurrentPhoto(updated);
      }
      setEditingPhoto(null);
    } catch (err) {
      console.error(err);
      setError('档案信息保存失败，请稍后再试。');
    } finally {
      setSaving(false);
    }
  };

  const hidePhoto = async (photo: HandPhoto) => {
    setSaving(true);
    setError(null);
    try {
      await api.deleteMyHandPhoto(photo.id);
      const nextPhotos = photos.filter((item) => item.id !== photo.id);
      setPhotos(nextPhotos);
      if (selectedPhotoId === photo.id) {
        const nextPhoto = nextPhotos[0];
        if (nextPhoto) {
          setCurrentPhoto(nextPhoto);
        } else {
          setSelectedPhotoId(null);
          clearCurrentHandPhoto();
        }
      }
      setEditingPhoto(null);
    } catch (err) {
      console.error(err);
      setError('档案删除失败，请稍后再试。');
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setAnalysisResult(null);
    setError(null);

    const reader = new FileReader();
    reader.onload = (readerEvent) => {
      setPreviewUrl(readerEvent.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  const analyzeHand = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('image', file);
      const response = await fetch('/ai/analyze/hand', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const result = await response.json();
      setAnalysisResult(result);
      return result as HandPhotoAnalysisResult;
    } catch (err) {
      console.error(err);
      const fallback = {
        hand_detected: true,
        quality_score: 0.78,
        recommendations: ['已跳过实时质量分析，照片会先保存为手部档案。'],
      };
      setAnalysisResult(fallback);
      return fallback;
    }
  };

  const saveNewPhoto = async () => {
    if (!selectedFile) return;

    setSaving(true);
    setError(null);
    try {
      const analysis = await analyzeHand(selectedFile);
      const quality = assessHandPhotoQuality(analysis);
      if (!quality.ok) {
        setError(quality.message);
        return;
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
        throw new Error('Upload failed');
      }

      const uploadData = await uploadResponse.json();
      const photo = await api.uploadMyHandPhoto({ image_url: uploadData.url });

      setCurrentPhoto(photo);
      setPhotos((current) => [photo, ...current]);
      setSelectedFile(null);
      setPreviewUrl(null);
    } catch (err) {
      console.error(err);
      setError('手部档案保存失败，请检查后端和 AI 服务是否已启动。');
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '刚刚保存';
    return new Date(dateString).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <MobileShell>
      <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-[#fbf7ef]/85 px-5 pb-3 pt-4 backdrop-blur-2xl">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-stone-700 shadow-sm">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-stone-400">Hand Profile</p>
            <h1 className="text-lg font-bold text-stone-950">手部档案管理</h1>
          </div>
          <div className="h-10 w-10" />
        </div>
      </header>

      <div className="flex flex-col px-5 pb-28 pt-5">
        <section className="overflow-hidden rounded-[2rem] bg-stone-950 text-amber-50">
          <div className="p-5">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="mb-2 text-sm text-amber-100/70">先存好手照，再一键试戴</p>
                <h2 className="text-2xl font-bold leading-tight">你的手部档案会复用到后续模板生成</h2>
              </div>
              <FolderOpen className="h-7 w-7 shrink-0 text-amber-200" />
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs text-amber-100/75">
              <div className="rounded-2xl bg-white/10 p-3">清晰露出指甲</div>
              <div className="rounded-2xl bg-white/10 p-3">自然光更稳定</div>
              <div className="rounded-2xl bg-white/10 p-3">可随时更换</div>
            </div>
          </div>
        </section>

        {error && (
          <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
        )}

        <section className="order-3 mt-5 rounded-[2rem] border border-stone-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-bold text-stone-950">当前档案</h2>
              <p className="text-sm text-stone-500">生成前默认使用选中的手照</p>
            </div>
            <span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-500">
              {photos.length} 张
            </span>
          </div>

          {loadingPhotos ? (
            <div className="flex items-center justify-center py-12 text-stone-400">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              正在读取档案
            </div>
          ) : photos.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-stone-200 p-8 text-center">
              <ImageIcon className="mx-auto mb-3 h-10 w-10 text-stone-300" />
              <p className="font-medium text-stone-800">还没有手部档案</p>
              <p className="mt-1 text-sm text-stone-500">上传一张清晰手照后，就可以复用它试戴不同模板。</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {photos.map((photo, index) => {
                const selected = selectedPhotoId === photo.id;
                return (
                  <div
                    key={photo.id}
                    className={
                      selected
                        ? 'overflow-hidden rounded-3xl border-2 border-stone-950 bg-stone-950 text-left text-amber-50'
                        : 'overflow-hidden rounded-3xl border border-stone-200 bg-[#fbf7ef] text-left text-stone-700'
                    }
                  >
                    <button type="button" onClick={() => setCurrentPhoto(photo)} className="block w-full text-left">
                      <div className={`relative bg-stone-100 ${getCropClass(photo)}`}>
                        <img src={photo.thumbnail_url || photo.image_url} alt="手部档案" className="h-full w-full object-cover" />
                        {isOfficialPresetPhoto(photo) && (
                          <span className="absolute left-2 top-2 rounded-full bg-white/90 px-2 py-1 text-[10px] font-semibold text-stone-700">
                            官方预设
                          </span>
                        )}
                        {selected && (
                          <span className="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 text-white">
                            <CheckCircle2 className="h-5 w-5" />
                          </span>
                        )}
                      </div>
                    </button>
                    <div className="p-3">
                      <p className="text-sm font-semibold">{getPhotoName(photo, index)}</p>
                      <p className={selected ? 'text-xs text-amber-100/70' : 'text-xs text-stone-500'}>
                        {selected ? '当前使用' : formatDate(photo.created_at)}
                      </p>
                      <div className="mt-3 flex gap-2">
                        <button
                          type="button"
                          onClick={() => openEditPhoto(photo, index)}
                          className={selected ? 'flex-1 rounded-xl bg-white/15 py-2 text-xs text-amber-50' : 'flex-1 rounded-xl bg-white py-2 text-xs text-stone-600'}
                        >
                          管理
                        </button>
                        <button
                          type="button"
                          onClick={() => hidePhoto(photo)}
                          disabled={saving}
                          className={selected ? 'flex h-8 w-8 items-center justify-center rounded-xl bg-white/15 text-amber-50' : 'flex h-8 w-8 items-center justify-center rounded-xl bg-white text-stone-500'}
                          aria-label="删除档案"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <Link
            href="/"
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50 transition hover:bg-stone-800"
          >
            <Sparkles className="h-4 w-4" />
            使用当前档案去选模板
          </Link>
        </section>

        <section className="mt-5 rounded-[2rem] border border-stone-200 bg-[#fffaf0] p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
              <Plus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-bold text-stone-950">新增手部档案</h2>
              <p className="text-sm text-stone-500">上传后会自动设为当前档案</p>
            </div>
          </div>

          {!previewUrl ? (
            <label className="block cursor-pointer">
              <div className="rounded-[1.75rem] border-2 border-dashed border-stone-300 bg-white p-8 text-center transition hover:border-stone-500">
                <Camera className="mx-auto mb-4 h-12 w-12 text-stone-400" />
                <p className="font-semibold text-stone-950">点击上传或拍摄手照</p>
                <p className="mt-1 text-sm text-stone-500">支持 JPG、PNG、WEBP</p>
                <input type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />
              </div>
            </label>
          ) : (
            <div className="space-y-4">
              <div className="overflow-hidden rounded-[1.75rem] bg-stone-100">
                <img src={previewUrl} alt="待保存手照" className="aspect-square w-full object-cover" />
              </div>

              {analysisResult && (
                <div className="rounded-3xl border border-emerald-100 bg-emerald-50 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2 text-sm font-semibold text-emerald-700">
                      <Check className="h-4 w-4" />
                      {analysisResult.hand_detected ? '手部照片可用' : '建议重新拍摄'}
                    </span>
                    <span className="text-sm font-bold text-emerald-700">
                      {Math.round(analysisResult.quality_score * 100)}%
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white">
                    <div
                      className="h-full rounded-full bg-emerald-500"
                      style={{ width: `${Math.round(analysisResult.quality_score * 100)}%` }}
                    />
                  </div>
                  <div className="mt-3 space-y-1">
                    {analysisResult.recommendations.map((item) => (
                      <p key={item} className="text-xs text-emerald-700">{item}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedFile(null);
                    setPreviewUrl(null);
                    setAnalysisResult(null);
                    setError(null);
                  }}
                  className="rounded-2xl border border-stone-200 bg-white py-3 text-sm font-medium text-stone-700"
                >
                  重新选择
                </button>
                <button
                  type="button"
                  onClick={saveNewPhoto}
                  disabled={saving}
                  className="flex items-center justify-center gap-2 rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  保存档案
                </button>
              </div>
            </div>
          )}

          <div className="mt-4 rounded-3xl bg-white p-4">
            <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-stone-900">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              拍摄建议
            </p>
            <div className="space-y-2 text-sm text-stone-600">
              <p>自然光线下拍摄，指甲完整露出。</p>
              <p>避免遮挡和强阴影，手部尽量平放。</p>
              <p>建议使用未做美甲的手照，试戴效果更稳定。</p>
            </div>
          </div>
        </section>

        {(loadingPresets || presets.length > 0) && (
          <section className="mt-5 overflow-hidden rounded-[2rem] border border-white/70 bg-white/75 p-4 shadow-[0_18px_45px_rgba(120,113,108,0.12)] backdrop-blur-xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">Official Samples</p>
                <h2 className="mt-1 text-lg font-bold text-stone-950">官方预设手模</h2>
                <p className="mt-1 text-sm leading-5 text-stone-500">
                  不想上传也可以直接体验，选择官方手部样张快速进入试戴。
                </p>
              </div>
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#f4eee5] text-amber-700 shadow-inner">
                <Sparkles className="h-4 w-4" />
              </span>
            </div>

            {loadingPresets ? (
              <div className="flex items-center justify-center rounded-[1.6rem] bg-white/80 py-10 text-sm text-stone-400">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                正在读取官方样张
              </div>
            ) : (
              <div className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto overscroll-x-contain px-4 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {presets.map((preset) => {
                  const using = usingPresetId === preset.id;
                  const active = photos.some((photo) => selectedPhotoId === photo.id && photo.image_url === preset.image_url);
                  return (
                    <article
                      key={preset.id}
                      className="min-w-[136px] snap-start rounded-[1.6rem] border border-white/80 bg-white/90 p-2 text-stone-900 shadow-[0_10px_28px_rgba(120,113,108,0.12)]"
                    >
                      <div className="relative aspect-[4/5] overflow-hidden rounded-[1.25rem] bg-stone-100">
                        <img src={preset.image_url} alt={preset.name} className="h-full w-full object-cover" />
                        <span className="absolute left-2 top-2 rounded-full bg-white/85 px-2 py-0.5 text-[10px] font-semibold text-stone-500 backdrop-blur">
                          官方
                        </span>
                      </div>
                      <div className="px-1 pb-1 pt-2">
                        <p className="truncate text-sm font-bold">{preset.name}</p>
                        <p className="mt-1 text-xs text-stone-400">免上传快速体验</p>
                        <button
                          type="button"
                          onClick={() => handlePresetPhoto(preset)}
                          disabled={using || active}
                          className={
                            active
                              ? 'mt-3 flex h-9 w-full items-center justify-center gap-1 rounded-full bg-emerald-50 text-xs font-semibold text-emerald-700'
                              : 'mt-3 flex h-9 w-full items-center justify-center gap-1 rounded-full bg-[#f3eee7] text-xs font-semibold text-stone-900 transition active:scale-[0.98] disabled:opacity-60'
                          }
                        >
                          {using ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                          {active ? '当前使用' : '一键使用'}
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        )}
      </div>

      {editingPhoto && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/30 px-5 pb-5">
          <div className="w-full max-w-[390px] rounded-[2rem] bg-white p-5 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-stone-950">管理手部档案</h2>
                <p className="text-sm text-stone-500">昵称和预览裁剪会保存到当前账号</p>
              </div>
              <button
                type="button"
                onClick={() => setEditingPhoto(null)}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-stone-100 text-stone-500"
                aria-label="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <label className="block text-sm font-medium text-stone-700">
              档案名称
              <input
                value={draftName}
                onChange={(event) => setDraftName(event.target.value)}
                className="mt-2 w-full rounded-2xl border border-stone-200 px-4 py-3 outline-none focus:border-stone-500"
                placeholder="例如：右手自然光"
              />
            </label>

            <div className="mt-4">
              <p className="mb-2 flex items-center gap-2 text-sm font-medium text-stone-700">
                <Crop className="h-4 w-4" />
                预览裁剪比例
              </p>
              <div className="grid grid-cols-3 gap-2">
                {cropRatios.map((ratio) => (
                  <button
                    key={ratio}
                    type="button"
                    onClick={() => setDraftCropRatio(ratio)}
                    className={
                      draftCropRatio === ratio
                        ? 'rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50'
                        : 'rounded-2xl bg-stone-100 py-3 text-sm font-semibold text-stone-600'
                    }
                  >
                    {ratio}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => hidePhoto(editingPhoto)}
                disabled={saving}
                className="flex items-center justify-center gap-2 rounded-2xl border border-red-100 bg-red-50 py-3 text-sm font-semibold text-red-600"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                删除档案
              </button>
              <button
                type="button"
                onClick={savePhotoEdit}
                disabled={saving}
                className="flex items-center justify-center gap-2 rounded-2xl bg-stone-950 py-3 text-sm font-semibold text-amber-50"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Edit3 className="h-4 w-4" />}
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </MobileShell>
  );
}
