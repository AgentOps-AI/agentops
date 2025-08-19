'use client';

import { useProject } from '@/app/providers/project-provider';
import { useHeaderContext } from '@/app/providers/header-provider';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import {
  File01Icon as FileCode2,
  CodeFolderIcon,
  ArrowRight01Icon as ChevronRight,
  CheckmarkCircle01Icon as Check,
  Loading03Icon as Loader2,
} from 'hugeicons-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import axios from 'axios';
import { Step } from './components/Step';
import { PaginatedTracesResponse } from '@/hooks/useTraces';
import { OsType } from './types';
import StartingFresh from './components/StartingFresh';
import ExistingCodebase from './components/ExistingCodebase';
import ApiKeySection from './components/ApiKeySection';

export default function EmptyProject() {
  const { selectedProject } = useProject();
  const { setHeaderTitle, setHeaderContent } = useHeaderContext();
  const { toast } = useToast();
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [isVerifying, setIsVerifying] = useState(false);
  const [hasEvents, setHasEvents] = useState(false);
  const [verificationAttempts, setVerificationAttempts] = useState(0);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [selectedNewFramework, setSelectedNewFramework] = useState<string | null>(null);
  const [osType, _setOsType] = useState<OsType>('unix');

  useEffect(() => {
    setHeaderTitle('Start using AgentOps');
    setHeaderContent(<></>);
  }, [setHeaderTitle, setHeaderContent]);

  const steps = [
    { label: 'Get Started', step: 0 },
    { label: 'Install', step: 1 },
    { label: 'Plans', step: 2 },
    { label: 'Verify', step: 3 },
  ];

  const navigateToStep = (stepIndex: number) => {
    // For step 0 (Get Started), always allow navigation and reset selections
    if (stepIndex === 0) {
      setSelectedTemplate(null);
      setSelectedNewFramework(null);
      setCurrentStep(0);
      return;
    }

    // For other steps, only allow navigation if they're accessible
    if (stepIndex <= currentStep || stepIndex <= 3) {
      setCurrentStep(stepIndex);
    }
  };

  const pricingPlans = [
    {
      name: 'Basic',
      price: '$0',
      period: 'per month',
      description: 'Free up to 100 sessions',
      features: ['Agent Agnostic SDK', 'LLM Cost Tracking (400+ LLMs)', 'Replay Analytics'],
      action: 'Start for Free',
      href: '#',
      onClick: () => setCurrentStep(3),
    },
    {
      name: 'Pro',
      price: '$40',
      period: 'per month',
      description: 'Up to 1,000 sessions',
      features: [
        'Increased event limit',
        'Unlimited log retention',
        'Trace and event export',
        'Dedicated Slack and email support',
        'Role-based permissioning',
      ],
      action: 'Upgrade',
      href: '#',
      highlight: true,
      onClick: () => router.push('/settings/organization'),
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: 'starts at',
      description: "Going beyond? Let's chat",
      features: [
        'SLA',
        'Custom SSO',
        'Alerts and notifications',
        'On-premise deployment',
        'Custom data retention policy',
        'Self-hosting (AWS, GCP, Azure)',
        'SOC-2, HIPAA, NIST AI RMF',
      ],
      action: 'Get a Demo',
      href: 'https://cal.com/team/agency-ai/enterprise-feature',
      onClick: () => window.open('https://cal.com/team/agency-ai/enterprise-feature', '_blank'),
    },
  ];

  async function checkForSessions() {
    if (!selectedProject?.id) {
      console.error('No selected project ID available for verification.');
      toast({ title: 'Error', description: 'Project not selected.', variant: 'destructive' });
      return;
    }
    setIsVerifying(true);
    try {
      const params = new URLSearchParams();
      params.append('limit', '10');
      params.append('offset', '0');

      const fetchSessions = fetchAuthenticatedApi<PaginatedTracesResponse>(
        `/v4/traces/list/${selectedProject.id}?${params.toString()}`,
      );
      const delay = new Promise((resolve) => setTimeout(resolve, 2000));

      const [tracesResponse] = await Promise.all([fetchSessions, delay]);

      const formData = {
        framework: selectedTemplate ? 'OpenAI Agents SDK' : 'Unknown',
        template: selectedTemplate || 'existing_codebase',
        selected_type: !selectedTemplate ? 'existing_project' : 'new_project',
        project_id: selectedProject?.id,
        project_name: selectedProject?.name,
      };

      try {
        await axios.post('https://submit-form.com/kwomKFAMl', formData);
      } catch (formError) {
        console.warn('Failed to submit form data:', formError);
        // Continue even if form submission fails
      }

      if (tracesResponse?.traces && tracesResponse.traces.length > 0) {
        setHasEvents(true);
      }
    } catch (error: unknown) {
      console.error('Error verifying installation:', error);
      toast({
        title: 'Verification Error',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
      setHasEvents(false);
    } finally {
      setIsVerifying(false);
      setVerificationAttempts((prev) => prev + 1);
    }
  }

  if (currentStep === 0) {
    return (
      <div className="flex min-h-screen flex-col">
        {/* Stepper */}
        <div className="border-b border-gray-200 dark:border-gray-800">
          <div className="mx-auto max-w-screen-xl">
            <div className="flex items-center">
              {steps.map((step, index) => (
                <Step
                  key={step.label}
                  label={step.label}
                  isActive={currentStep === index}
                  isComplete={currentStep > index}
                  onClick={() => navigateToStep(index)}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1">
          <div className="mx-auto max-w-4xl p-8">
            <h2 className="mb-12 text-center text-4xl font-bold text-gray-900 dark:text-gray-100">
              {"Let's get you started with AgentOps"}
            </h2>

            <div className="grid grid-cols-2 gap-6">
              <div
                className="group relative flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl border border-gray-200 bg-gradient-to-br from-gray-50 to-gray-100 p-8 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl dark:border-gray-700 dark:from-gray-800 dark:to-gray-900"
                onClick={() => setCurrentStep(1)}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-purple-600/10 opacity-0 transition-opacity duration-300 group-hover:opacity-100 dark:from-blue-600/20 dark:to-purple-600/20" />

                <div className="relative z-10 flex h-full flex-col justify-between">
                  <div className="space-y-6">
                    <div className="inline-flex rounded-lg bg-blue-500/10 p-3 ring-1 ring-blue-500/20 dark:bg-blue-500/10 dark:ring-blue-500/20">
                      <CodeFolderIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    </div>

                    <div>
                      <h3 className="mb-2 text-2xl font-bold text-gray-900 dark:text-white">
                        Existing Codebase
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400">
                        Add AgentOps to your current project in minutes
                      </p>
                    </div>
                  </div>

                  <div className="mt-8">
                    <div className="inline-flex items-center gap-2 rounded-full bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-600 ring-1 ring-blue-500/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20">
                      <span>Quick integration</span>
                      <ChevronRight className="h-4 w-4" />
                    </div>
                  </div>
                </div>
              </div>

              <div
                className="group relative flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl border border-gray-200 bg-gradient-to-br from-gray-50 to-gray-100 p-8 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl dark:border-gray-700 dark:from-gray-800 dark:to-gray-900"
                onClick={() => {
                  setSelectedTemplate('starting-fresh');
                  setCurrentStep(1);
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-blue-600/10 opacity-0 transition-opacity duration-300 group-hover:opacity-100 dark:from-purple-600/20 dark:to-blue-600/20" />

                <div className="relative z-10 flex h-full flex-col justify-between">
                  <div className="space-y-6">
                    <div className="inline-flex rounded-lg bg-purple-500/10 p-3 ring-1 ring-purple-500/20 dark:bg-purple-500/10 dark:ring-purple-500/20">
                      <FileCode2 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                    </div>

                    <div>
                      <h3 className="mb-2 text-2xl font-bold text-gray-900 dark:text-white">
                        Starting Fresh
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400">
                        Build a new agent with our pre-built templates
                      </p>
                    </div>
                  </div>

                  <div className="mt-8">
                    <div className="inline-flex items-center gap-2 rounded-full bg-purple-500/10 px-4 py-2 text-sm font-medium text-purple-600 ring-1 ring-purple-500/20 dark:bg-purple-500/10 dark:text-purple-400 dark:ring-purple-500/20">
                      <span>Perfect for new projects</span>
                      <ChevronRight className="h-4 w-4" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === 1) {
    return (
      <div className="flex min-h-screen flex-col">
        {/* Stepper */}
        <div className="border-b border-gray-200 dark:border-gray-800">
          <div className="mx-auto max-w-screen-xl">
            <div className="flex items-center">
              {steps.map((step, index) => (
                <Step
                  key={step.label}
                  label={step.label}
                  isActive={currentStep === index}
                  isComplete={currentStep > index}
                  onClick={() => navigateToStep(index)}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Render the appropriate component based on selection */}
        {selectedTemplate ? (
          <StartingFresh
            selectedProject={selectedProject}
            selectedTemplate={selectedTemplate}
            selectedNewFramework={selectedNewFramework || ''}
            osType={osType}
            onBack={() => {
              setSelectedTemplate(null);
              setSelectedNewFramework(null);
              setCurrentStep(0);
            }}
            onNavigateToStep={navigateToStep}
          />
        ) : (
          <ExistingCodebase
            selectedProject={selectedProject}
            onBack={() => setCurrentStep(0)}
            onNavigateToStep={navigateToStep}
          />
        )}
      </div>
    );
  }

  if (currentStep === 2) {
    return (
      <div className="flex min-h-screen flex-col">
        {/* Stepper */}
        <div className="border-b border-gray-200 dark:border-gray-800">
          <div className="mx-auto max-w-screen-xl">
            <div className="flex items-center">
              {steps.map((step, index) => (
                <Step
                  key={step.label}
                  label={step.label}
                  isActive={currentStep === index}
                  isComplete={currentStep > index}
                  onClick={() => navigateToStep(index)}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-7xl flex-1 p-8">
          <div className="mb-12 text-center">
            <h1 className="mb-4 text-4xl font-bold">Free to get started. Flexibility at scale.</h1>
          </div>

          <div className="grid grid-cols-3 gap-8">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className={cn(
                  'rounded-xl border-2 p-8',
                  'transition-all duration-200',
                  plan.highlight
                    ? 'border-gray-800 bg-gray-900 text-white'
                    : 'border-gray-200 dark:border-gray-800',
                )}
              >
                <div className="mb-6">
                  <h3
                    className={cn(
                      'mb-1 text-xl font-semibold',
                      !plan.highlight && 'text-gray-900 dark:text-gray-100',
                    )}
                  >
                    {plan.name}
                  </h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold">{plan.price}</span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">{plan.period}</span>
                  </div>
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    {plan.description}
                  </p>
                </div>

                <Button
                  className="mb-6 w-full"
                  variant={plan.highlight ? 'default' : 'outline'}
                  onClick={plan.onClick}
                >
                  {plan.action}
                </Button>

                <div className="space-y-3">
                  {plan.features.map((feature) => (
                    <div key={feature} className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      <span
                        className={cn(
                          'text-sm',
                          !plan.highlight && 'text-gray-600 dark:text-gray-300',
                        )}
                      >
                        {feature}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 flex max-w-full justify-between px-8">
            <Button variant="outline" onClick={() => setCurrentStep(1)} className="px-8">
              <ChevronRight className="mr-2 h-4 w-4 rotate-180" />
              Back to installation
            </Button>
            <Button onClick={() => setCurrentStep(3)} className="px-8">
              Skip
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === 3) {
    return (
      <div className="flex min-h-screen flex-col">
        {/* Stepper */}
        <div className="border-b border-gray-200 dark:border-gray-800">
          <div className="mx-auto max-w-screen-xl">
            <div className="flex items-center">
              {steps.map((step, index) => (
                <Step
                  key={step.label}
                  label={step.label}
                  isActive={currentStep === index}
                  isComplete={currentStep > index}
                  onClick={() => navigateToStep(index)}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-1 items-start justify-center">
          <div className="w-full max-w-2xl p-8">
            <h2 className="mb-8 text-2xl font-bold">Verify installation</h2>

            <div className="space-y-6">
              <ApiKeySection
                selectedProject={selectedProject}
                title="1. Verify API Key"
                description="Make sure you've set your AgentOps API key correctly."
              />

              <div className="rounded-lg border bg-gray-50 p-6 dark:bg-gray-900">
                <h3 className="mb-2 text-lg font-semibold">2. Check Installation</h3>
                <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
                  Run your agent and verify the installation was successful:
                </p>
                <Button onClick={checkForSessions} disabled={isVerifying} className="w-full">
                  {isVerifying ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Checking for events...
                    </>
                  ) : (
                    'Check installation'
                  )}
                </Button>

                {verificationAttempts > 0 && hasEvents && (
                  <div className="mt-4 border-l-4 border-green-500 bg-green-50 p-4 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                    <p className="text-sm">
                      <Check className="mr-1 inline-block h-5 w-5" /> Success! Traces received from
                      your agent.
                    </p>
                    <div className="mt-2">
                      <Button variant="outline" size="sm" asChild>
                        <Link href="/traces">
                          View your traces
                          <ChevronRight className="ml-2 h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  </div>
                )}

                {verificationAttempts > 0 && !hasEvents && (
                  <div className="mt-4 border-l-4 border-yellow-500 bg-yellow-50 p-4 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                    <p className="text-sm">
                      No events received. Please check:
                      <ul className="ml-4 mt-2 list-disc">
                        <li>Your API key is set correctly</li>
                        <li>Your agent is running</li>
                        <li>{"You've initialized AgentOps in your code"}</li>
                      </ul>
                    </p>
                  </div>
                )}
              </div>

              {verificationAttempts > 0 && hasEvents && (
                <div className="mt-6">
                  <Button size="lg" className="w-full" onClick={() => setCurrentStep(2)}>
                    Next Step: Choose your plan
                    <ChevronRight className="ml-2 h-5 w-5" />
                  </Button>
                </div>
              )}

              <div className="border-t pt-8">
                <h2 className="mb-4 text-xl font-semibold">Need help?</h2>
                <div className="space-y-4">
                  <Button variant="outline" asChild className="w-full">
                    <Link href="https://docs.agentops.ai" target="_blank">
                      Read the docs
                    </Link>
                  </Button>
                  <Button variant="outline" asChild className="w-full">
                    <Link href="https://github.com/AgentOps-AI/agentops/issues" target="_blank">
                      Raise an issue
                    </Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
