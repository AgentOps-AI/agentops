// app/(with-layout)/welcome/layout.tsx
import type { Metadata } from 'next';
import { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Welcome | AgentOps',
  description: 'Welcome to AgentOps - Complete your profile to get started',
};

interface WelcomeLayoutProps {
  children: ReactNode;
}

export default function WelcomeLayout({ children }: WelcomeLayoutProps) {
  return <div className="flex min-h-screen flex-col">{children}</div>;
}
