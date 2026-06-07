import { API_BASE_URL } from './config';
import { AUTH_COOKIE_NAMES, safeConsumerNextPath as resolveSafeConsumerNextPath } from './route-guards.js';

export interface AuthUser {
  id: number;
  phone: string;
  nickname?: string | null;
  avatar_url?: string | null;
  user_type: 'consumer' | 'merchant' | 'admin' | string;
  created_at?: string;
}

const AUTH_TOKEN_KEY = 'nailmind_auth_token';
const AUTH_USER_KEY = 'nailmind_auth_user';
const CONSUMER_AUTH_TOKEN_KEY = 'nailmind_consumer_auth_token';
const CONSUMER_AUTH_USER_KEY = 'nailmind_consumer_auth_user';
const OPERATOR_AUTH_TOKEN_KEY = 'nailmind_operator_auth_token';
const OPERATOR_AUTH_USER_KEY = 'nailmind_operator_auth_user';
const AUTH_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

type AuthScope = 'consumer' | 'operator';

function canUseStorage() {
  return typeof window !== 'undefined' && !!window.localStorage;
}

export function getAuthToken() {
  if (!canUseStorage()) return null;
  const scope = getCurrentScope();
  const scopedToken = localStorage.getItem(resolveTokenKey(scope));
  if (scopedToken) return scopedToken;

  const cookieToken = readAuthCookie(scope);
  if (cookieToken) return cookieToken;

  const legacyUser = getLegacyUser();
  if (!legacyUser) return null;
  if (scope === 'consumer' && isOperator(legacyUser)) return null;
  if (scope === 'operator' && !isOperator(legacyUser)) return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function getCurrentUser(): AuthUser | null {
  if (!canUseStorage()) return null;
  const scope = getCurrentScope();
  const raw = localStorage.getItem(resolveUserKey(scope)) || localStorage.getItem(AUTH_USER_KEY);
  if (!raw) return null;
  try {
    const user = JSON.parse(raw) as AuthUser;
    if (scope === 'consumer' && isOperator(user)) return null;
    if (scope === 'operator' && !isOperator(user)) return null;
    return user;
  } catch {
    return null;
  }
}

export function getCurrentUserId() {
  const user = getCurrentUser();
  if (user?.id) return user.id;
  if (!canUseStorage()) return null;
  if (getCurrentScope() !== 'consumer') return null;
  const legacyId = localStorage.getItem('user_id');
  return legacyId ? Number(legacyId) : null;
}

export function saveAuthSession(token: string, user: AuthUser) {
  if (!canUseStorage()) return;
  const scope = isOperator(user) ? 'operator' : 'consumer';
  localStorage.setItem(resolveTokenKey(scope), token);
  localStorage.setItem(resolveUserKey(scope), JSON.stringify(user));
  setAuthCookie(scope, token);
  if (scope === 'consumer') {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    localStorage.setItem('user_id', String(user.id));
  }
}

export function clearAuthSession() {
  if (!canUseStorage()) return;
  const scope = getCurrentScope();
  localStorage.removeItem(resolveTokenKey(scope));
  localStorage.removeItem(resolveUserKey(scope));
  clearAuthCookie(scope);
  if (scope === 'consumer') {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    localStorage.removeItem('user_id');
  }
}

export function requireLogin(nextPath: string) {
  return `/login?next=${encodeURIComponent(nextPath)}`;
}

export function safeConsumerNextPath(nextPath: string | null | undefined) {
  return resolveSafeConsumerNextPath(nextPath);
}

export function isOperator(user: AuthUser | null) {
  return user?.user_type === 'merchant' || user?.user_type === 'admin';
}

export function getCurrentScope(): AuthScope {
  if (typeof window !== 'undefined') {
    const path = window.location.pathname;
    if (path.startsWith('/admin') || path.startsWith('/merchant')) return 'operator';
  }
  return 'consumer';
}

function resolveTokenKey(scope: AuthScope) {
  return scope === 'operator' ? OPERATOR_AUTH_TOKEN_KEY : CONSUMER_AUTH_TOKEN_KEY;
}

function resolveUserKey(scope: AuthScope) {
  return scope === 'operator' ? OPERATOR_AUTH_USER_KEY : CONSUMER_AUTH_USER_KEY;
}

function setAuthCookie(scope: AuthScope, token: string) {
  const cookieName = scope === 'operator' ? AUTH_COOKIE_NAMES.operator : AUTH_COOKIE_NAMES.consumer;
  document.cookie = `${cookieName}=${encodeURIComponent(token)}; Path=/; Max-Age=${AUTH_COOKIE_MAX_AGE_SECONDS}; SameSite=Lax`;
}

function clearAuthCookie(scope: AuthScope) {
  const cookieName = scope === 'operator' ? AUTH_COOKIE_NAMES.operator : AUTH_COOKIE_NAMES.consumer;
  document.cookie = `${cookieName}=; Path=/; Max-Age=0; SameSite=Lax`;
}

function readAuthCookie(scope: AuthScope) {
  if (typeof document === 'undefined') return null;
  const cookieName = scope === 'operator' ? AUTH_COOKIE_NAMES.operator : AUTH_COOKIE_NAMES.consumer;
  const prefix = `${cookieName}=`;
  const cookie = document.cookie
    .split(';')
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix));
  if (!cookie) return null;
  return decodeURIComponent(cookie.slice(prefix.length));
}

function getLegacyUser(): AuthUser | null {
  return readStoredUser(AUTH_USER_KEY);
}

function readStoredUser(key: string): AuthUser | null {
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export async function validateAuthSession(): Promise<AuthUser | null> {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      clearAuthSession();
      return null;
    }
    const user = (await response.json()) as AuthUser;
    const scope = getCurrentScope();
    if (scope === 'consumer' && isOperator(user)) {
      clearAuthSession();
      return null;
    }
    if (scope === 'operator' && !isOperator(user)) {
      clearAuthSession();
      return null;
    }
    saveAuthSession(token, user);
    return user;
  } catch {
    return getCurrentUser();
  }
}
