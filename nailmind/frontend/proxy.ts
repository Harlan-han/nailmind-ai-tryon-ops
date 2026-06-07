import { NextRequest, NextResponse } from 'next/server';
import { AUTH_COOKIE_NAMES, resolveRouteAuth } from './src/lib/route-guards.js';

export function proxy(request: NextRequest) {
  const decision = resolveRouteAuth({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    cookies: {
      [AUTH_COOKIE_NAMES.consumer]: request.cookies.get(AUTH_COOKIE_NAMES.consumer)?.value,
      [AUTH_COOKIE_NAMES.operator]: request.cookies.get(AUTH_COOKIE_NAMES.operator)?.value,
    },
  });

  if (decision.action === 'redirect' && decision.destination) {
    return NextResponse.redirect(new URL(decision.destination, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/login',
    '/admin/:path*',
    '/merchant/:path*',
    '/upload',
    '/tryon',
    '/processing',
    '/records',
    '/candidates',
    '/compare',
    '/profile',
  ],
};
