import { TryOnRecord } from './api';

const CURRENT_TRY_ON_ID_KEY = 'current_try_on_id';
const CURRENT_DESIGN_ID_KEY = 'current_design_id';
const CURRENT_HAND_PHOTO_ID_KEY = 'current_hand_photo_id';
const CURRENT_HAND_PHOTO_URL_KEY = 'current_hand_photo_url';

const pendingKey = (designId: number, handPhotoId: number) => `pending_try_on_${designId}_${handPhotoId}`;
const startedAtKey = (tryOnId: number) => `try_on_started_at_${tryOnId}`;

export type CurrentHandPhoto = {
  id: number;
  image_url: string;
};

export function saveCurrentHandPhoto(photo: CurrentHandPhoto) {
  localStorage.setItem(CURRENT_HAND_PHOTO_ID_KEY, photo.id.toString());
  localStorage.setItem(CURRENT_HAND_PHOTO_URL_KEY, photo.image_url);
}

export function clearCurrentHandPhoto() {
  localStorage.removeItem(CURRENT_HAND_PHOTO_ID_KEY);
  localStorage.removeItem(CURRENT_HAND_PHOTO_URL_KEY);
}

export function saveCurrentTryOnSession(
  tryOn: TryOnRecord,
  handPhotoUrl?: string,
  options: { resetStartedAt?: boolean } = {}
) {
  localStorage.setItem(CURRENT_TRY_ON_ID_KEY, tryOn.id.toString());
  localStorage.setItem(CURRENT_DESIGN_ID_KEY, tryOn.nail_design_id.toString());
  if (handPhotoUrl) {
    saveCurrentHandPhoto({ id: tryOn.hand_photo_id, image_url: handPhotoUrl });
  } else {
    localStorage.setItem(CURRENT_HAND_PHOTO_ID_KEY, tryOn.hand_photo_id.toString());
  }
  localStorage.setItem(pendingKey(tryOn.nail_design_id, tryOn.hand_photo_id), tryOn.id.toString());

  if (tryOn.status === 'pending' || tryOn.status === 'processing') {
    const key = startedAtKey(tryOn.id);
    if (options.resetStartedAt || !localStorage.getItem(key)) {
      const createdAt = Date.parse(tryOn.created_at);
      localStorage.setItem(
        key,
        String(options.resetStartedAt || Number.isNaN(createdAt) ? Date.now() : createdAt)
      );
    }
  }
}

export function getCurrentTryOnId() {
  const stored = localStorage.getItem(CURRENT_TRY_ON_ID_KEY);
  return stored ? Number(stored) : null;
}

export function getTryOnStartedAt(tryOnId: number) {
  const stored = localStorage.getItem(startedAtKey(tryOnId));
  const timestamp = stored ? Number(stored) : Date.now();
  return Number.isFinite(timestamp) ? timestamp : Date.now();
}

export function getStoredHandPhoto() {
  const photoId = localStorage.getItem(CURRENT_HAND_PHOTO_ID_KEY);
  const photoUrl = localStorage.getItem(CURRENT_HAND_PHOTO_URL_KEY);
  return {
    id: photoId ? Number(photoId) : null,
    url: photoUrl || null,
  };
}

export function getPendingTryOnId(designId: number, handPhotoId: number) {
  const stored = localStorage.getItem(pendingKey(designId, handPhotoId));
  return stored ? Number(stored) : null;
}

export function clearPendingTryOn(designId: number, handPhotoId: number) {
  localStorage.removeItem(pendingKey(designId, handPhotoId));
}

export function resetFailedTryOnForRetry(tryOn: TryOnRecord) {
  clearPendingTryOn(tryOn.nail_design_id, tryOn.hand_photo_id);
  localStorage.removeItem(CURRENT_TRY_ON_ID_KEY);
  localStorage.removeItem(startedAtKey(tryOn.id));
  localStorage.setItem(CURRENT_DESIGN_ID_KEY, tryOn.nail_design_id.toString());
  localStorage.setItem(CURRENT_HAND_PHOTO_ID_KEY, tryOn.hand_photo_id.toString());
  localStorage.removeItem(CURRENT_HAND_PHOTO_URL_KEY);
}
