const AUTH_COOKIE_NAMES = {
  consumer: 'nailmind_consumer_auth_token',
  operator: 'nailmind_operator_auth_token',
};

const CONSUMER_PRIVATE_PREFIXES = [
  '/upload',
  '/assistant',
  '/tryon',
  '/processing',
  '/records',
  '/candidates',
  '/compare',
  '/profile',
];

const OPERATOR_PRIVATE_PREFIXES = ['/admin', '/merchant'];

function isPathInPrefixes(pathname, prefixes) {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function base64UrlDecode(value) {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padding = normalized.length % 4 ? '='.repeat(4 - (normalized.length % 4)) : '';
  if (typeof atob === 'function') {
    return atob(normalized + padding);
  }
  return Buffer.from(normalized + padding, 'base64').toString('utf8');
}

function decodeJwtPayload(token) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    return JSON.parse(base64UrlDecode(parts[1]));
  } catch {
    return null;
  }
}

function isOperatorPayload(payload) {
  return payload?.user_type === 'merchant' || payload?.user_type === 'admin';
}

function isValidPayload(payload, nowSeconds) {
  if (!payload) return false;
  if (typeof payload.sub !== 'string' || !/^[1-9]\d*$/.test(payload.sub)) return false;
  if (!['consumer', 'merchant', 'admin'].includes(payload.user_type)) return false;
  if (typeof payload.exp !== 'number') return false;
  return payload.exp > nowSeconds;
}

function sessionFromToken(token, nowSeconds) {
  const payload = decodeJwtPayload(token);
  if (!isValidPayload(payload, nowSeconds)) return null;
  return {
    payload,
    isOperator: isOperatorPayload(payload),
  };
}

function buildLoginDestination(pathname, search) {
  const nextPath = `${pathname}${search || ''}`;
  return `/login?next=${encodeURIComponent(nextPath)}`;
}

function safeConsumerNextPath(nextPath) {
  if (!nextPath || !nextPath.startsWith('/') || nextPath.startsWith('//')) return '/';
  if (nextPath.startsWith('/admin') || nextPath.startsWith('/merchant')) return '/';
  if (nextPath === '/login' || nextPath.startsWith('/login?') || nextPath.startsWith('/login/')) return '/';
  return nextPath;
}

function resolveRouteAuth({ pathname, search = '', cookies = {}, nowSeconds = Math.floor(Date.now() / 1000) }) {
  const consumerSession = sessionFromToken(cookies[AUTH_COOKIE_NAMES.consumer], nowSeconds);
  const operatorSession = sessionFromToken(cookies[AUTH_COOKIE_NAMES.operator], nowSeconds);
  const isOperatorRoute = isPathInPrefixes(pathname, OPERATOR_PRIVATE_PREFIXES);
  const isConsumerRoute = isPathInPrefixes(pathname, CONSUMER_PRIVATE_PREFIXES);

  if (pathname === '/admin/login') {
    if (operatorSession?.isOperator) {
      return { action: 'redirect', destination: '/admin/assistant' };
    }
    return { action: 'next' };
  }

  if (pathname === '/login') {
    if (consumerSession && !consumerSession.isOperator) {
      const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
      return { action: 'redirect', destination: safeConsumerNextPath(params.get('next')) };
    }
    return { action: 'next' };
  }

  if (isOperatorRoute) {
    if (!operatorSession?.isOperator) {
      return { action: 'redirect', destination: '/admin/login' };
    }
    return { action: 'next' };
  }

  if (isConsumerRoute) {
    if (!consumerSession || consumerSession.isOperator) {
      return { action: 'redirect', destination: buildLoginDestination(pathname, search) };
    }
    return { action: 'next' };
  }

  return { action: 'next' };
}

module.exports = {
  AUTH_COOKIE_NAMES,
  CONSUMER_PRIVATE_PREFIXES,
  OPERATOR_PRIVATE_PREFIXES,
  resolveRouteAuth,
  safeConsumerNextPath,
};
