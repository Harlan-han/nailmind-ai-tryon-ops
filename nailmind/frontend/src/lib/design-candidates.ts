import { getCurrentUserId } from './auth';

export interface DesignCandidate {
  id: number;
  name: string;
  image_url: string;
  style_tags: string[];
  color_tags?: string[];
  added_at: string;
}

const DESIGN_CANDIDATES_KEY = 'design_candidates';

function resolveCandidatesKey() {
  const userId = getCurrentUserId();
  return userId ? `design_candidates_user_${userId}` : DESIGN_CANDIDATES_KEY;
}

function readCandidates(): DesignCandidate[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(resolveCandidatesKey()) || '[]');
  } catch {
    return [];
  }
}

function writeCandidates(candidates: DesignCandidate[]) {
  localStorage.setItem(resolveCandidatesKey(), JSON.stringify(candidates));
}

export function getDesignCandidates() {
  return readCandidates();
}

export function isDesignCandidate(designId: number) {
  return readCandidates().some((candidate) => candidate.id === designId);
}

export function toggleDesignCandidate(candidate: Omit<DesignCandidate, 'added_at'>) {
  const candidates = readCandidates();
  const exists = candidates.some((item) => item.id === candidate.id);
  if (exists) {
    writeCandidates(candidates.filter((item) => item.id !== candidate.id));
    return false;
  }

  writeCandidates([
    {
      ...candidate,
      added_at: new Date().toISOString(),
    },
    ...candidates,
  ]);
  return true;
}

export function removeDesignCandidate(designId: number) {
  writeCandidates(readCandidates().filter((candidate) => candidate.id !== designId));
}
