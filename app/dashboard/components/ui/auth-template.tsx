import AgentOpsBanner from '@/components/icons/AgentOpsBanner';
import { BackgroundCircuit } from '@/components/ui/background-circuit';
import { Button } from '@/components/ui/button';
import { ArrowRight01Icon as ArrowRight } from 'hugeicons-react';
import Link from 'next/link';
import { ReactNode } from 'react';

interface AuthTemplateProps {
  children: ReactNode;
  [key: string]: any;
}

export const AuthTemplate = ({ children, ...props }: AuthTemplateProps) => {
  return (
    <div
      className="align-center relative flex min-h-screen w-full justify-center overflow-hidden"
      {...props}
    >
      <BackgroundCircuit className="fixed inset-0 h-full w-full" />
      <div className="flex items-center justify-center p-10">
        <div className="relative z-10 grid lg:grid-cols-2 lg:gap-28">
          <div className="hidden flex-col lg:mt-5 lg:flex">
            <div className="flex w-[441px] flex-col items-start justify-start gap-5">
              <AgentOpsBanner />
              <p className="max-w-2xl font-nasalization text-xl sm:text-4xl">
                The essential toolkit for ambitious AI agents
              </p>
            </div>
          </div>

          <div className="flex flex-col items-center">
            <div className="content-center">
              <div className="mx-8 py-4 sm:mx-0 sm:max-w-96 sm:py-0">{children}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
