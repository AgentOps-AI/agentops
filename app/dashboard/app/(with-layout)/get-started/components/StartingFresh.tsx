'use client';

import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import {
    ArrowRight01Icon as ChevronRight,
    LinkSquare02Icon as ExternalLink,
} from 'hugeicons-react';
import { cn } from '@/lib/utils';
import { useState, useMemo } from 'react';
import { exampleNotebooks } from '../data/example-frameworks';
import ApiKeySection from './ApiKeySection';

interface StartingFreshProps {
    selectedProject: any;
    selectedTemplate: string;
    selectedNewFramework: string;
    osType: string;
    onBack: () => void;
    onNavigateToStep: (step: number) => void;
}

export default function StartingFresh({
    selectedProject,
    selectedTemplate,
    selectedNewFramework,
    osType,
    onBack,
    onNavigateToStep,
}: StartingFreshProps) {
    const { toast } = useToast();
    const [selectedTab, setSelectedTab] = useState<'frameworks' | 'providers'>('frameworks');

    // Separate frameworks and providers
    const { frameworks, providers } = useMemo(() => {
        const providerFrameworks = ['OpenAI', 'Anthropic', 'Google Gemini', 'LiteLLM', 'WatsonX', 'xAI'];

        const frameworks = exampleNotebooks.filter(
            example => !providerFrameworks.includes(example.framework)
        );

        const providers = exampleNotebooks.filter(
            example => providerFrameworks.includes(example.framework)
        );

        return { frameworks, providers };
    }, []);

    const currentExamples = selectedTab === 'frameworks' ? frameworks : providers;
    const [selectedExample, setSelectedExample] = useState(currentExamples[0]);

    // Update selected example when tab changes
    const handleTabChange = (tab: 'frameworks' | 'providers') => {
        setSelectedTab(tab);
        const examples = tab === 'frameworks' ? frameworks : providers;
        setSelectedExample(examples[0]);
    };

    return (
        <div className="mt-8">
            <div className="mb-4">
                <button
                    onClick={onBack}
                    className="mb-4 flex items-center text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
                >
                    <ChevronRight className="mr-1 h-4 w-4 rotate-180" />
                    Back to templates
                </button>
                <h2 className="text-2xl font-bold">Starting Fresh</h2>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    Explore example notebooks from the AgentOps repository and get started quickly
                </p>
            </div>

            <div className="mt-6 flex gap-6">
                {/* Sidebar with example notebooks */}
                <div className="w-64 flex-shrink-0 border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
                    {/* Tab selector */}
                    <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                        <div className="flex rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
                            <button
                                onClick={() => handleTabChange('frameworks')}
                                className={cn(
                                    'flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                                    selectedTab === 'frameworks'
                                        ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                                        : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
                                )}
                            >
                                Frameworks
                            </button>
                            <button
                                onClick={() => handleTabChange('providers')}
                                className={cn(
                                    'flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                                    selectedTab === 'providers'
                                        ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                                        : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
                                )}
                            >
                                Providers
                            </button>
                        </div>
                    </div>

                    <div className="sticky top-0 bg-white p-4 pb-2 dark:bg-gray-900">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                            {selectedTab === 'frameworks' ? 'Framework Examples' : 'Provider Examples'}
                        </h2>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {currentExamples.length} examples available
                        </p>
                    </div>
                    <div className="h-[500px] overflow-y-auto px-4 pb-4">
                        <div className="space-y-2">
                            {currentExamples.map((example) => (
                                <button
                                    key={example.id}
                                    onClick={() => setSelectedExample(example)}
                                    className={cn(
                                        'w-full rounded-lg p-3 text-left transition-colors',
                                        selectedExample?.id === example.id
                                            ? 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
                                            : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800/50'
                                    )}
                                >
                                    <div className="flex flex-col gap-1">
                                        <div className="flex items-center gap-2">
                                            <div className="flex h-5 w-5 items-center justify-center">{example.icon}</div>
                                            <div className="font-medium">{example.framework}</div>
                                        </div>
                                        <div className="text-sm text-gray-600 dark:text-gray-400 truncate">
                                            {example.name}
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Main content */}
                <div className="flex-1">
                    {selectedExample ? (
                        <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                            <h3 className="mb-4 flex items-center gap-3 text-xl font-semibold">
                                {selectedExample.icon}
                                {selectedExample.name}
                            </h3>

                            <div className="mb-6">
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                    Framework: {selectedExample.framework}
                                </p>
                                <div className="space-y-1">
                                    {Array.isArray(selectedExample.description) && selectedExample.description.map((point: string, index: number) => (
                                        <p key={index} className="text-sm text-gray-700 dark:text-gray-300">
                                            {point}
                                        </p>
                                    ))}
                                </div>
                            </div>

                            {/* API Key Section */}
                            <div className="mb-6">
                                <ApiKeySection
                                    selectedProject={selectedProject}
                                    description="Use this key in the example notebook to track your agents"
                                />
                            </div>

                            <div className="flex gap-4">
                                <Button
                                    size="lg"
                                    onClick={() => window.open(selectedExample.colabUrl, '_blank')}
                                    className="flex items-center gap-2"
                                >
                                    <img
                                        src="https://colab.research.google.com/img/colab_favicon_256px.png"
                                        alt="Google Colab"
                                        className="h-5 w-5"
                                    />
                                    Open in Google Colab
                                    <ExternalLink className="h-4 w-4" />
                                </Button>

                                <Button
                                    size="lg"
                                    variant="outline"
                                    onClick={() => window.open('https://github.com/AgentOps-AI/agentops/tree/main/examples', '_blank')}
                                    className="flex items-center gap-2"
                                >
                                    Access examples
                                    <ExternalLink className="h-4 w-4" />
                                </Button>
                            </div>

                            <div className="mt-4">
                                <Button
                                    onClick={() => onNavigateToStep(2)}
                                    className="w-full flex items-center justify-center gap-2"
                                >
                                    Next: Verify Installation
                                    <ChevronRight className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                            <p className="text-center text-gray-500 dark:text-gray-400">
                                Select an example to get started
                            </p>
                        </div>
                    )}

                    <div className="mt-6 text-center">
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                            Want to integrate with your existing codebase instead?
                        </p>
                        <button
                            onClick={() => onNavigateToStep(0)}
                            className="mt-2 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                            Choose a different path →
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
} 