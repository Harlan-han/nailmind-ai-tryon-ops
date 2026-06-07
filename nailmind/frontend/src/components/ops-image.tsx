'use client';

import { useState } from 'react';
import { ImageIcon } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api';

const apiOrigin = (() => {
  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return '';
  }
})();

export function normalizeAssetUrl(src?: string | null) {
  if (!src) return '';
  if (/^https?:\/\//i.test(src)) return src;
  if (src.startsWith('/uploads/')) return apiOrigin ? `${apiOrigin}${src}` : src;
  return src;
}

export function OpsImage({
  src,
  alt,
  className,
  fallbackLabel = '图片未加载',
}: {
  src?: string | null;
  alt: string;
  className: string;
  fallbackLabel?: string;
}) {
  const [failed, setFailed] = useState(false);
  const normalizedSrc = normalizeAssetUrl(src);

  if (failed || !normalizedSrc) {
    return (
      <div className={`${className} flex flex-col items-center justify-center bg-stone-100 text-center text-xs text-stone-500`}>
        <ImageIcon className="mb-1 h-5 w-5 text-stone-300" />
        <span className="font-medium text-stone-600">{fallbackLabel}</span>
      </div>
    );
  }

  return (
    <img
      src={normalizedSrc}
      alt={alt}
      className={className}
      onError={() => setFailed(true)}
    />
  );
}
