import '@/app/globals.css';
import { TooltipProvider } from '@/components/ui/tooltip';
import { signInMethods } from '@/lib/signin';
import { InformationCircleIcon as Info } from 'hugeicons-react';
import Link from 'next/link';
import { PropsWithChildren, Suspense } from 'react';
import HeaderProvider from '@/app/providers/header-provider';
import { SidebarProvider } from '@/app/providers/sidebar-provider';
import { LayoutContentWrapper } from '@/components/layout-content-wrapper';
import ReactQueryProvider from '@/app/providers/react-query-provider';
import ProjectProvider from '@/app/providers/project-provider';
import { SurveyModal } from '@/components/survey-modal';
import { PostHogUserIdentifier } from '@/components/posthog-user-identifier';
import { SurveyCheckProvider } from '@/app/providers/survey-check-provider';
import { PatchNotesProvider } from '@/app/providers/patch-notes-provider';

export default async function AppLayout({ children }: PropsWithChildren) {
  return (
    // The order of these providers is important.
    <ReactQueryProvider>
      <PostHogUserIdentifier />
      <PatchNotesProvider>
        <SurveyCheckProvider>
          <ProjectProvider>
            <TooltipProvider>
              <HeaderProvider>
                <SidebarProvider>
                  <LayoutContentWrapper>
                    {signInMethods.includes('anonymous') && (
                      <div className="mb-2 flex flex-row bg-background px-5 py-5 shadow-md sm:pl-24">
                        <Info />
                        <div className="pl-2">
                          You are using AgentOps in Playground Mode. To access full features and save
                          your traces,{' '}
                          <Link href="https://app.agentops.ai" className="underline">
                            log in or create an account
                          </Link>
                        </div>
                      </div>
                    )}
                    <div className="">
                      <Suspense fallback={<></>}>{children}</Suspense>
                    </div>
                    <SurveyModal />
                  </LayoutContentWrapper>
                </SidebarProvider>
              </HeaderProvider>
            </TooltipProvider>
          </ProjectProvider>
        </SurveyCheckProvider>
      </PatchNotesProvider>
    </ReactQueryProvider>
  );
}
