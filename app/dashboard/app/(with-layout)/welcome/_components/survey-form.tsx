'use client';

import { useEffect, useState } from 'react';
import { redirect, RedirectType, useRouter } from 'next/navigation';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import {
  Building2, Rocket, Target, Share2, Code2, Factory, Wrench, ArrowLeft, Loader, MoveUpRight,
  FileText, Youtube, ExternalLink, Coins, BeakerIcon, Computer
} from 'lucide-react';
import { CloudServerIcon } from 'hugeicons-react';

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { userQueryKey, useUser } from '@/hooks/queries/useUser';
import { useQueryClient } from '@tanstack/react-query';
import { technologies, frameworks, providers, companySizes, stages, referralSources } from './constants';
import { toast } from '@/components/ui/use-toast';

const baseFormSchema = z.object({
  email: z.string().optional(),
  company_size: z.string().min(1, 'Company size is required'),
  build_purpose: z.string().min(25, 'Please describe what you are trying to build. Minimum 25 characters'),
  stage: z.string().min(1, 'Stage is required'),
  referral_source: z.string(),
  technologies: z.array(z.string()).min(1, 'Please select at least one technology'),
  company_name: z.string().min(1, 'Company name is required'),
  tools_used: z.string().optional(),
  other_technology: z.string().optional(),
  usage_type: z.string().min(1, 'Please select how you plan to use AgentOps'),
});

const otherReferralSchema = z.object({
  other_referral: z.string().optional(),
});

const helpNeededSchema = z.object({
  help_needed: z.array(z.string()).min(1, 'Please select at least one option'),
});

const inputStyles = "border-gray-200 dark:border-gray-700 focus:border-blue-500 dark:focus:border-blue-400";

const step1Schema = z.object({
  company_size: z.string().min(1, 'Company size is required'),
  build_purpose: z.string().min(25, 'Please describe what you are trying to build. Minimum 25 characters'),
  stage: z.string().min(1, 'Stage is required'),
  referral_source: z.string(),
  technologies: z.array(z.string()).min(1, 'Please select at least one technology'),
  company_name: z.string().min(1, 'Company name is required'),
  tools_used: z.string().optional(),
  other_technology: z.string().optional(),
});

const IconWrapper = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", className)}>
    {children}
  </div>
);

export function SurveyForm() {
  const queryClient = useQueryClient();
  const { data: userData, isLoading: userDataLoading } = useUser();
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [showSurvey, setShowSurvey] = useState<boolean | undefined>(true);
  const [showOtherReferral, setShowOtherReferral] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedCards, setSelectedCards] = useState<number[]>([]);
  const [noCardIsSelected, setNoCardIsSelected] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [showOtherTechnology, setShowOtherTechnology] = useState(false);

  const steps = ['Getting Started', 'About you', 'How can we help?', 'One last thing...'];
  const cards = [
    {
      id: 1,
      title: 'Logging and debugging',
      description: 'I need to debug my agents and understand their logs',
      icon: <Computer className="w-4 h-4" />,
      benefit: "Debug sessions 10x faster than terminal",
    },
    {
      id: 2,
      title: "Track spending",
      description: "I need to track how much I'm spending on LLMs",
      icon: <Coins className="w-4 h-4" />,
      benefit: "Track 100% of spend on LLM providers",
    },
    {
      id: 3,
      title: 'Evaluation and benchmarking',
      description: 'I want to evaluate and test the performance of my agents',
      icon: <BeakerIcon className="w-4 h-4" />,
      benefit: "Up to 30x faster evaluating runs",
    },
    {
      id: 4,
      title: 'Deployments',
      description: 'I want to deploy my agents to production',
      icon: <Rocket className="w-4 h-4" />,
      benefit: "Manage agents in the cloud",
    },
    {
      id: 5,
      title: 'Not sure yet',
    },
  ];

  const formSchema = baseFormSchema.merge(otherReferralSchema).merge(helpNeededSchema).superRefine((data, ctx) => {
    if (data.referral_source === 'Other' && (!data.other_referral || data.other_referral.length === 0)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Please specify the referral source!',
        path: ['other_referral'],
      });
    }
  });

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: '',
      company_size: '',
      build_purpose: '',
      stage: '',
      referral_source: '',
      technologies: [],
      company_name: '',
      tools_used: '',
      other_technology: '',
      usage_type: '',
      other_referral: '',
      help_needed: [],
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const baseFormValid = baseFormSchema.safeParse(values).success;
    const otherReferralValid = otherReferralSchema.safeParse(values).success;
    const helpNeededValid = helpNeededSchema.safeParse(values).success;

    if (!baseFormValid || !otherReferralValid || !helpNeededValid || !userData?.id) {
      return;
    }
    setIsSubmitting(true);

    const submissionValues = {
      ...values,
      email: userData.email || '',
    };

    try {
      // Submit to our API proxy which handles external submissions
      const response = await fetch('/api/survey-submission', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(submissionValues),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to submit survey');
      }

      // Log any non-critical errors from external services
      if (result.errors && result.errors.length > 0) {
        console.warn('Some external submissions failed:', result.errors);
      }

      // Mark survey as complete in our database
      await fetchAuthenticatedApi('/opsboard/users/update', {
        method: 'POST',
        body: JSON.stringify({ survey_is_complete: true }),
      });

      queryClient.invalidateQueries({ queryKey: userQueryKey });
      form.reset();

      setIsSubmitting(false);
      setIsRedirecting(true);
      setShowSurvey(false);
      setCurrentStep(1);

      // Small delay before reload
      setTimeout(() => {
        window.location.reload();
      }, 500);

    } catch (e) {
      console.error('Survey submission error:', e);
      toast({
        title: "Error",
        description: "Failed to submit your survey. Please try again.",
        variant: "destructive",
      });
      setIsSubmitting(false);
    }
  }

  const handleNextStep = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();

    if (currentStep === 0) {
      const isValid = await form.trigger(['usage_type']);
      if (!isValid) return;

      if (form.getValues('usage_type') === 'consulting') {
        window.location.href = 'https://calendly.com/itsada/consultation';
        return;
      }
    }

    if (currentStep === 1) {
      const step1Valid = step1Schema.safeParse(form.getValues()).success;
      const otherReferralValid = otherReferralSchema.safeParse(form.getValues()).success;

      if (form.getValues().referral_source === 'Other' && (!form.getValues().other_referral || !form.getValues().other_referral?.length)) {
        form.setError('other_referral', {
          type: 'manual',
          message: 'Please specify the referral source!'
        });
        return;
      }

      if (!step1Valid || !otherReferralValid) {
        return await form.trigger([
          'company_size',
          'build_purpose',
          'stage',
          'referral_source',
          'technologies',
          'company_name',
        ]);
      }
    }

    if (currentStep === 2 && !selectedCards.length) {
      return setNoCardIsSelected(true);
    }


    setCurrentStep(currentStep + 1 > 3 ? 3 : currentStep + 1);
  };

  const toggleFramework = (framework: string) => {
    if (framework === 'Other') {
      setShowOtherTechnology(!selectedFrameworks.includes(framework));
    }
    setSelectedFrameworks((prev) =>
      prev.includes(framework)
        ? prev.filter((f) => f !== framework)
        : [...prev, framework]
    );
    const updatedFrameworks = selectedFrameworks.includes(framework)
      ? selectedFrameworks.filter((f) => f !== framework)
      : [...selectedFrameworks, framework];
    form.setValue('technologies', [...updatedFrameworks, ...selectedProviders]);
  };

  const toggleProvider = (provider: string) => {
    setSelectedProviders((prev) =>
      prev.includes(provider)
        ? prev.filter((p) => p !== provider)
        : [...prev, provider]
    );
    const updatedProviders = selectedProviders.includes(provider)
      ? selectedProviders.filter((p) => p !== provider)
      : [...selectedProviders, provider];
    form.setValue('technologies', [...selectedFrameworks, ...updatedProviders]);
  };

  const handleCardClick = (id: number) => {
    const updatedCards = selectedCards.includes(id) ? selectedCards.filter((cardId) => cardId !== id) : [...selectedCards, id];
    setSelectedCards(updatedCards);
    const helpNeeded = updatedCards.map((cardId) => cards.find((card) => card.id === cardId)?.title as string);
    form.setValue('help_needed', helpNeeded);
  }

  useEffect(() => {
    if (userData && userData.email) {
      form.setValue('email', userData.email);
    }
  }, [userData, form]);

  useEffect(() => {
    if (userData) {
      if (userData.survey_is_complete) {
        setShowSurvey(false);
        setCurrentStep(1);
        return redirect('/projects');
      }
    }
  }, [userData]);

  return (
    <>
      <div className={cn('fixed w-full h-full inset-0 bg-white dark:bg-gray-950 z-[51] pointer-events-none transition-opacity duration-300', showSurvey ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none invisible')} />
      <div className={cn("fixed inset-0 z-[52] overflow-y-auto transition-opacity duration-300", showSurvey ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none invisible')}>
        <div className="min-h-full py-8 px-4 flex flex-col items-center">
          <div className="relative w-full max-w-2xl p-8 pt-8 bg-white dark:bg-gray-900 rounded-xl">

            <h2 className="mb-2 text-xl font-bold text-gray-900 dark:text-gray-100">
              Before you get started, we want to know more about you.
            </h2>

            <Stepper steps={steps} currentStep={currentStep} onBackClicked={() => setCurrentStep(currentStep - 1 < 0 ? 0 : currentStep - 1)} />
            <h2 className="mt-8 mb-6 text-3xl font-bold text-gray-900 dark:text-gray-100">{steps[currentStep]}</h2>

            <div className='relative'>
              {(isSubmitting || userDataLoading) && (
                <div className="absolute inset-0 z-[53] bg-white/40 dark:bg-gray-950/40 flex items-center justify-center">
                  <Loader className="w-8 h-8 text-gray-800 animate-spin dark:text-gray-200" />
                </div>
              )}
              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className="space-y-8"
                  onChange={() => {
                    form.clearErrors();
                  }}
                >
                  {currentStep === 0 && (
                    <div className="space-y-6">
                      <FormField
                        control={form.control}
                        name="usage_type"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-lg">What are you using AgentOps for?</FormLabel>
                            <FormMessage />
                            <div className="grid grid-cols-3 gap-4 mt-2">
                              <div
                                className={cn(
                                  "relative aspect-square rounded-xl border-2 p-6 cursor-pointer transition-all duration-300",
                                  "hover:border-black dark:hover:border-white hover:shadow-lg",
                                  "flex flex-col items-center justify-center text-center gap-4",
                                  "w-full h-full",
                                  field.value === 'hobby' ? "border-black dark:border-white shadow-lg" : "border-gray-100 dark:border-gray-800"
                                )}
                                onClick={() => field.onChange('hobby')}
                              >
                                <IconWrapper className="bg-purple-100 dark:bg-purple-900/30">
                                  <Rocket className="text-purple-600 dark:text-purple-400" />
                                </IconWrapper>
                                <div className="flex-1 flex flex-col justify-center">
                                  <h3 className="font-semibold text-lg mb-1">Hobby</h3>
                                  <p className="text-sm text-gray-500 dark:text-gray-400">Personal projects and experimentation</p>
                                </div>
                              </div>

                              <div
                                className={cn(
                                  "relative aspect-square rounded-xl border-2 p-6 cursor-pointer transition-all duration-300",
                                  "hover:border-black dark:hover:border-white hover:shadow-lg",
                                  "flex flex-col items-center justify-center text-center gap-4",
                                  "w-full h-full",
                                  field.value === 'work' ? "border-black dark:border-white shadow-lg" : "border-gray-100 dark:border-gray-800"
                                )}
                                onClick={() => field.onChange('work')}
                              >
                                <IconWrapper className="bg-blue-100 dark:bg-blue-900/30">
                                  <Building2 className="text-blue-600 dark:text-blue-400" />
                                </IconWrapper>
                                <div className="flex-1 flex flex-col justify-center">
                                  <h3 className="font-semibold text-lg mb-1">Work</h3>
                                  <p className="text-sm text-gray-500 dark:text-gray-400">Professional or commercial use</p>
                                </div>
                              </div>

                              <div
                                className={cn(
                                  "relative aspect-square rounded-xl border-2 p-6 cursor-pointer transition-all duration-300",
                                  "hover:border-black dark:hover:border-white hover:shadow-lg",
                                  "flex flex-col items-center justify-center text-center gap-4",
                                  "w-full h-full",
                                  field.value === 'consulting' ? "border-black dark:border-white shadow-lg" : "border-gray-100 dark:border-gray-800"
                                )}
                                onClick={() => field.onChange('consulting')}
                              >
                                <IconWrapper className="bg-green-100 dark:bg-green-900/30">
                                  <Wrench className="text-green-600 dark:text-green-400" />
                                </IconWrapper>
                                <div className="flex-1 flex flex-col justify-center">
                                  <h3 className="font-semibold text-lg mb-1">Need Help</h3>
                                  <p className="text-sm text-gray-500 dark:text-gray-400">{"I'm not a developer, help me build an agent"}</p>
                                </div>
                              </div>
                            </div>
                          </FormItem>
                        )}
                      />
                    </div>
                  )}

                  {currentStep === 1 && (
                    <div className="space-y-6">
                      <FormField
                        control={form.control}
                        name="company_name"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2">
                              <Factory className="w-4 h-4" />
                              Company name *
                            </FormLabel>
                            <FormControl>
                              <Input
                                placeholder="Enter your company name"
                                {...field}
                                className={inputStyles}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="company_size"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2">
                              <Building2 className="w-4 h-4" />
                              Company Size *
                            </FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select company size" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent className="z-[55]">
                                {companySizes.map((size) => (
                                  <SelectItem key={size} value={size}>
                                    {size}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="build_purpose"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2">
                              <Rocket className="w-4 h-4" />
                              What are you trying to build? *
                            </FormLabel>
                            <FormControl>
                              <Input placeholder="Describe your project" {...field} className={inputStyles} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="stage"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2">
                              <Target className="w-4 h-4" />
                              What stage are you at? *
                            </FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select your stage" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent className='z-[55]'>
                                {stages.map((stage) => (
                                  <SelectItem key={stage} value={stage}>
                                    {stage}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="referral_source"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2">
                              <Share2 className="w-4 h-4" />
                              How did you hear about us? *
                            </FormLabel>
                            <Select
                              onValueChange={(value) => {
                                field.onChange(value);
                                setShowOtherReferral(value === 'Other');
                              }}
                              defaultValue={field.value}
                            >
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="How did you hear about us?" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent className='z-[55]'>
                                {referralSources.map((source) => (
                                  <SelectItem key={source} value={source}>
                                    {source}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      {showOtherReferral && (
                        <FormField
                          control={form.control}
                          name="other_referral"
                          render={({ field }) => (
                            <FormItem>
                              <FormControl>
                                <Input placeholder="Enter referral source" {...field} className={inputStyles} />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      )}

                      <FormField
                        control={form.control}
                        name="technologies"
                        render={() => (
                          <FormItem>
                            <div className="space-y-4">
                              <div>
                                <FormLabel className="flex items-center gap-2">
                                  <Code2 className="w-4 h-4" />
                                  Frameworks *
                                </FormLabel>
                                <div className="flex flex-wrap gap-2 mt-2">
                                  {frameworks.map((framework) => (
                                    <Badge
                                      key={framework.id}
                                      variant={selectedFrameworks.includes(framework.title) ? 'default' : 'outline'}
                                      className="cursor-pointer flex items-center gap-1"
                                      onClick={() => toggleFramework(framework.title)}
                                    >
                                      {framework.logo}
                                      {framework.title}
                                    </Badge>
                                  ))}
                                </div>
                                {showOtherTechnology && (
                                  <FormField
                                    control={form.control}
                                    name="other_technology"
                                    render={({ field }) => (
                                      <FormItem className="mt-2">
                                        <FormControl>
                                          <Input
                                            placeholder="Enter framework name"
                                            {...field}
                                            className={inputStyles}
                                          />
                                        </FormControl>
                                        <FormMessage />
                                      </FormItem>
                                    )}
                                  />
                                )}
                              </div>

                              <div>
                                <FormLabel className="flex items-center gap-2">
                                  <CloudServerIcon className="w-4 h-4" />
                                  Providers
                                </FormLabel>
                                <div className="flex flex-wrap gap-2 mt-2">
                                  {providers.map((provider) => (
                                    <Badge
                                      key={provider.id}
                                      variant={selectedProviders.includes(provider.title) ? 'default' : 'outline'}
                                      className="cursor-pointer flex items-center gap-1"
                                      onClick={() => toggleProvider(provider.title)}
                                    >
                                      {provider.logo}
                                      {provider.title}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            </div>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="tools_used"
                        render={({ field }) => (
                          <FormItem defaultValue={''}>
                            <FormLabel className="flex items-center gap-2">
                              <Wrench className="w-4 h-4" />
                              Have you tried any other LLM ops or observability tools?
                            </FormLabel>
                            <FormControl>
                              <Input placeholder="Enter tools" {...field} className={inputStyles} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  )}

                  {currentStep === 2 && <>
                    {
                      noCardIsSelected && <p className="text-sm text-red-500">Please select at least one option</p>
                    }
                    <FormField
                      control={form.control}
                      name="help_needed"
                      render={({ field }) => (
                        <FormControl>
                          <div className='pb-10'>
                            {cards.map((card) => (
                              <SelectableCard
                                key={card.id}
                                {...card}
                                selected={selectedCards.includes(card.id)}
                                onClick={() => {
                                  setNoCardIsSelected(false);
                                  handleCardClick(card.id);
                                }}
                              />
                            ))}
                          </div>
                        </FormControl>
                      )}
                    />
                  </>}

                  {currentStep === 3 && <div>
                    <div className="mt-8">
                      <h3 className="text-lg font-semibold mb-4">Resources for your tech stack</h3>
                      <div className='flex flex-wrap gap-2'>
                        {[...selectedFrameworks, ...selectedProviders].map((el: string) => {
                          const tech = technologies.find(t => t.title === el);
                          if (!tech || tech.id === 'other') return null;
                          return <ResourceBox key={tech.id} title={tech.title} youtubeLink={tech.ytLink} docsLink={tech.docLink} icon={tech.logo} />
                        })}
                      </div>
                    </div>
                  </div>}

                  {currentStep !== 3 && <Button className="w-full" onClick={handleNextStep}>Next</Button>}

                  {currentStep === 3 && (
                    <div className={cn(
                      "cursor-pointer"
                    )}>
                      <Button
                        type="submit"
                        className={cn(
                          "w-full transition-all cursor-pointer",
                          (form.formState.isSubmitting || isRedirecting)
                            ? "opacity-50 pointer-events-none"
                            : "opacity-100"
                        )}
                        disabled={form.formState.isSubmitting || isRedirecting}
                      >
                        Submit
                      </Button>
                    </div>
                  )}

                </form>
              </Form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

interface StepperProps {
  steps: string[];
  currentStep: number;
  onBackClicked?: () => void;
}

function Stepper({ steps, currentStep, onBackClicked }: StepperProps) {
  return (
    <div className="w-full max-w-3xl py-3 pt-0 mx-auto">
      <div className="space-y-2">
        <span className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-400">
          <ArrowLeft className='w-4 h-4 cursor-pointer in-out hover:translate-x-[-6px]' onClick={onBackClicked} /> Step {currentStep + 1} of {steps.length}
        </span>

        <div className="flex gap-1 max-w-[45%]">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`h-1 flex-1 rounded-full transition-all duration-300 ${index <= currentStep ? 'bg-black dark:bg-white' : 'bg-gray-200 dark:bg-gray-700'
                }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

interface SelectableCardProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  benefit?: string;
  selected?: boolean;
  hasError?: boolean;
  onClick?: () => void;
}

export function SelectableCard({
  title,
  description,
  icon,
  benefit,
  selected = false,
  onClick
}: SelectableCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "group relative w-full bg-white dark:bg-gray-900 rounded-lg p-4 cursor-pointer transition-all duration-300 mb-4",
        "border-2 hover:border-black dark:hover:border-white hover:shadow-lg hover:shadow-black/20 dark:hover:shadow-white/10",
        "before:absolute before:inset-0 before:rounded-2xl before:bg-gradient-to-b before:from-white/20 dark:before:from-gray-800/20 before:to-white/0 before:opacity-0 before:transition-opacity hover:before:opacity-100",
        selected ? "border-black dark:border-white shadow-lg shadow-black/20 dark:shadow-white/10" : "border-gray-100 dark:border-gray-800",
      )}
    >
      <div className="relative space-y-4">
        <div className="flex items-center space-x-3">
          {icon && (
            <div className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center",
              "bg-gradient-to-br from-blue-500 to-purple-500 text-white",
              "shadow-lg shadow-blue-500/30"
            )}>
              {icon}
            </div>
          )}
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">{title}</h2>
        </div>

        {description && (
          <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
        )}

        {benefit && (
          <div className="absolute right-0 flex items-center gap-2 p-2 px-3 m-0 text-green-600 border border-green-500 rounded-md -top-4 dark:border-green-600 bg-green-50 dark:bg-green-900/50 dark:text-green-400">
            <MoveUpRight className="w-4 h-4" style={{
              strokeWidth: 2
            }} />
            <span className="text-xs font-medium">
              {benefit}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

interface ResourceBoxProps {
  title: string;
  youtubeLink: string;
  docsLink: string;
  icon: React.ReactNode;
}

export function ResourceBox({ title, youtubeLink, docsLink, icon }: ResourceBoxProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-2">
      <div className="flex items-center gap-2 mb-2">
        <div className="p-2 rounded-lg bg-indigo-100 text-indigo-600">
          {icon}
        </div>
        <h3 className="font-semibold text-md text-gray-800">{title}</h3>
      </div>
      <div className="space-y-2 text-xs">
        {youtubeLink && <a
          href={youtubeLink}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-red-600 hover:text-red-700 transition-colors"
        >
          <Youtube size={16} />
          <span>Watch Tutorial</span>
          <ExternalLink size={14} />
        </a>}
        {docsLink && <a
          href={docsLink}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-blue-600 hover:text-blue-700 transition-colors"
        >
          <FileText size={16} />
          <span>Documentation</span>
          <ExternalLink size={14} />
        </a>
        }
      </div>
    </div>
  );
}
