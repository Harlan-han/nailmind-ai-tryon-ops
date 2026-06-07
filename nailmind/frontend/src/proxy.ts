import { NextResponse, type NextRequest } from 'next/server';

import { AUTH_COOKIE_NAMES, resolveRouteAuth } from './lib/route-guards.js';

type CookieNames = Record<string, string>;

export function proxy(request: NextRequest) {
  const cookies: Record<string, string> = {};

  Object.values(AUTH_COOKIE_NAMES as CookieNames).forEach((name) => {
    const value = request.cookies.get(name)?.value;
    if (value) cookies[name] = value;
  });

  const result = resolveRouteAuth({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    cookies,
  });

  if (result.action === 'redirect') {
    return NextResponse.redirect(new URL(result.destination, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/login',
    '/admin/login',
    '/admin/:path*',
    '/merchant/:path*',
    '/upload/:path*',
    '/assistant/:path*',
    '/tryon/:path*',
    '/processing/:path*',
    '/records/:path*',
    '/candidates/:path*',
    '/compare/:path*',
    '/profile/:path*',
  ],
};
