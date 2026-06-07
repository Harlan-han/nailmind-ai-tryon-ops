'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, requireLogin, validateAuthSession, type AuthUser } from './auth';

export function useValidatedUser(nextPath: string) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;

    async function validateUser() {
      const cachedUser = getCurrentUser();
      await Promise.resolve();

      if (active) {
        setUser(cachedUser);
      }
      const freshUser = await validateAuthSession();
      if (!freshUser) {
        router.replace(requireLogin(nextPath));
        if (active) {
          setChecking(false);
        }
        return;
      }
      if (active) {
        setUser(freshUser);
        setChecking(false);
      }
    }

    validateUser().catch(() => {
      if (active) {
        setChecking(false);
      }
    });

    return () => {
      active = false;
    };
  }, [nextPath, router]);

  return { user, checking };
}
