'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useUser } from '@/hooks/queries/useUser';

interface SurveyCheckProviderProps {
  children: React.ReactNode;
}

export function SurveyCheckProvider({ children }: SurveyCheckProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: user } = useUser();

  useEffect(() => {
    if (
      pathname === '/welcome' ||
      pathname === '/signin' ||
      pathname === '/signup' ||
      pathname.startsWith('/auth/')
    ) {
      return;
    }

    if (!user) return;

    if (user.survey_is_complete === false || user.survey_is_complete === null) {
      router.push('/welcome');
    }
  }, [user, pathname, router]);

  return <>{children}</>;
}
