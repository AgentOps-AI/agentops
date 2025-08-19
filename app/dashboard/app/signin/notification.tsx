'use client';

import { useToast } from '@/components/ui/use-toast';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AuthNotification(props: { message: string }) {
  const { toast } = useToast();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (props.message)
      toast({
        title: props.message,
        duration: 8000,
      });
  }, [props.message]);

  if (props.message && pathname !== '/signin') router.push('/signin');

  return <div></div>;
}
