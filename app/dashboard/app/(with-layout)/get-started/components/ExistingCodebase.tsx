'use client';

import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import {
    Copy01Icon as CopyIcon,
    CodeIcon as Code2,
    ArrowRight01Icon as ChevronRight,
    CheckmarkCircle01Icon as Check,
    Loading03Icon as Loader2,
} from 'hugeicons-react';
import { cn } from '@/lib/utils';
import CrewIcon from '@/components/icons/CrewIcon';
import MicrosoftIcon from '@/components/icons/MicrosoftIcon';
import ChatgptIcon from '@/components/icons/ChatgptIcon';
import CamelIcon from '@/components/icons/CamelIcon/CamelIcon';
import LlamaStackIcon from '@/components/icons/LlamaStackIcon/LlamaStackIcon';
import LlamaIndexIcon from '@/components/icons/LlamaIndexIcon';
import HuggingFaceIcon from '@/components/icons/HuggingFaceIcon';
import GoogleIcon from '@/components/icons/GoogleIcon';
import Mem0Icon from '@/components/icons/Mem0Icon';
import TSIcon from '@/components/icons/TSIcon';
import { AG2Icon, AgnoIcon, LangGraphIcon } from '@/components/icons';
import { VibeKitButton } from '@vibe-kit/onboard';
import { Prism, SyntaxHighlighterProps } from 'react-syntax-highlighter';
const SyntaxHighlighter = Prism as any as React.FC<SyntaxHighlighterProps>;
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem,
} from '@/components/ui/select';
import { useState } from 'react';
import { FrameworkType, PackageManager } from '../types';
import { llmProviders } from '../data/llm-providers';
import ApiKeySection from './ApiKeySection';

interface ExistingCodebaseProps {
    selectedProject: any;
    onBack: () => void;
    onNavigateToStep: (step: number) => void;
    initialSelectedFramework?: any;
}

export default function ExistingCodebase({ selectedProject, onBack, onNavigateToStep, initialSelectedFramework }: ExistingCodebaseProps) {
    const { toast } = useToast();
    const [frameworkType, setFrameworkType] = useState<FrameworkType>('framework');
    const [packageManager, setPackageManager] = useState<PackageManager>('uv');
    const [selectedFramework, setSelectedFramework] = useState<any>(initialSelectedFramework || null);
    const [hasSelectedFramework, setHasSelectedFramework] = useState(!!initialSelectedFramework);
    const [installMode, setInstallMode] = useState<'ai' | 'manual'>('ai');

    const frameworks = [
        {
            id: 'crewai',
            name: 'CrewAI',
            installCommand: 'pip install agentops crewai',
            icon: <CrewIcon className="h-5 w-5" />,
            description: 'Create AI agent crews that work together',
        },
        {
            id: 'agno',
            name: 'Agno',
            installCommand: 'pip install agentops agno',
            icon: <AgnoIcon className="h-5 w-5" />,
            description: 'Flexible agent orchestration platform',
        },
        {
            id: 'typescript',
            name: 'Typescript',
            installCommand: 'npm install agentops openai-agents-js',
            icon: <TSIcon className="h-5 w-5" />,
            description: 'JavaScript/Typescrpt SDK for OpenAI Agents',
        },
        {
            id: 'openaiagentssdk',
            name: 'OpenAI Agents SDK',
            installCommand: 'pip install agentops openai-agents',
            icon: <ChatgptIcon className="h-5 w-5" />,
            description: 'Build with OpenAI\'s latest agent framework',
        },
        {
            id: 'google-adk',
            name: 'Google ADK',
            installCommand: 'pip install agentops google-generativeai',
            icon: <GoogleIcon className="h-5 w-5" />,
            description: "Google's modular framework for developing and deploying AI agents",
        },
        {
            id: 'ag2',
            name: 'AG2',
            installCommand: 'pip install agentops ag2',
            icon: <AG2Icon className="h-5 w-5" />,
            description: 'Next-gen multi-agent framework',
        },
        {
            id: 'autogen',
            name: 'AutoGen',
            installCommand: 'pip install agentops autogen',
            icon: <MicrosoftIcon className="h-5 w-5" />,
            description: 'Microsoft\'s multi-agent conversation framework',
        },
        {
            id: 'langgraph',
            name: 'LangGraph',
            installCommand: 'pip install agentops langgraph',
            icon: <LangGraphIcon className="h-5 w-5" />,
            description: 'Build stateful, multi-actor applications with LLMs',
        },
        {
            id: 'smolagents',
            name: 'smolagents',
            installCommand: 'pip install agentops smolagents',
            icon: <HuggingFaceIcon className="h-5 w-5" />,
            description: 'HuggingFace\'s lightweight agent framework',
        },
        {
            id: 'llamaindex',
            name: 'LlamaIndex',
            installCommand: 'pip install agentops llama-index',
            icon: <LlamaIndexIcon className="h-5 w-5" />,
            description: 'Data framework for LLM applications',
        },
        {
            id: 'camelai',
            name: 'CamelAI',
            installCommand: 'pip install agentops camelai',
            icon: <CamelIcon className="h-5 w-5" />,
            description: 'Communicative agents for large-scale collaboration',
        },
        {
            id: 'LlamaStack',
            name: 'LlamaStack',
            installCommand: 'pip install agentops llama-stack-client',
            icon: <LlamaStackIcon className="h-5 w-5" />,
            description: 'Meta\'s standardized LLM development stack',
        },
        {
            id: 'mem0',
            name: 'Mem0',
            installCommand: 'pip install agentops mem0ai',
            icon: <Mem0Icon className="h-5 w-5" />,
            description: 'Memory layer for AI applications',
        },
        {
            id: 'taskweaver',
            name: 'TaskWeaver',
            installCommand: 'pip install agentops taskweaver',
            icon: <MicrosoftIcon className="h-5 w-5" />,
            description: 'Code-first agent framework for complex tasks',
        },
        {
            id: 'custom',
            name: 'Custom Integration',
            installCommand: 'pip install agentops',
            icon: <Code2 className="h-5 w-5" />,
            description: 'Use AgentOps with any Python project',
        },
    ];

    const customStyle = {
        'pre[class*="language-"]': {
            color: 'white',
            background: '#0F1117',
        },
        keyword: {
            color: '#569cd6',
        },
        'class-name': {
            color: '#4ec9b0',
        },
        'maybe-class-name': {
            color: '#4ec9b0',
        },
        comment: {
            color: '#6a9955',
        },
        function: {
            color: '#dcdcaa',
        },
        string: {
            color: '#ce9178',
        },
        builtin: {
            color: '#ce9178',
        },
    };

    function copyInstallCommand() {
        const command =
            packageManager === 'pip'
                ? selectedFramework?.installCommand || 'pip install agentops'
                : selectedFramework?.installCommand?.replace('pip', 'uv pip') || 'uv pip install agentops';

        navigator.clipboard
            .writeText(command)
            .then(() =>
                toast({
                    title: 'Install Command Copied',
                    description: command,
                }),
            )
            .catch(() => {
                toast({
                    title: '❌ Could Not Copy - Manually copy the command below:',
                    description: command,
                });
            });
    }

    function copyApiKey() {
        if (selectedProject) {
            const frameworkName = selectedFramework?.name?.toLowerCase() || 'default';
            const apiKeyText = `import agentops\n\nagentops.init(\n    api_key='${selectedProject?.api_key || 'your_api_key_here'}',\n    default_tags=['${frameworkName}']\n)`;

            navigator.clipboard
                .writeText(apiKeyText)
                .then(() =>
                    toast({
                        title: 'Code Snippet Copied',
                        description: 'Initialization code copied to clipboard',
                    }),
                )
                .catch(() => {
                    toast({
                        title: '❌ Could Not Copy - Manually copy the code below:',
                        description: apiKeyText,
                    });
                });
        }
    }

    // If no framework selected yet, show framework selection grid
    if (!hasSelectedFramework) {
        return (
            <div className="flex-1 p-8">
                <div className="mx-auto max-w-6xl">
                    {/* Toggle between frameworks and LLM providers */}
                    <div className="mb-8 flex justify-center">
                        <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-800">
                            <button
                                onClick={() => setFrameworkType('framework')}
                                className={cn(
                                    "rounded-md px-4 py-2 text-sm font-medium transition-colors",
                                    frameworkType === 'framework'
                                        ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                                        : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                )}
                            >
                                Frameworks
                            </button>
                            <button
                                onClick={() => setFrameworkType('llm')}
                                className={cn(
                                    "rounded-md px-4 py-2 text-sm font-medium transition-colors",
                                    frameworkType === 'llm'
                                        ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                                        : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                )}
                            >
                                LLM Providers
                            </button>
                        </div>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                        {(frameworkType === 'llm' ? llmProviders : frameworks).map((item) => (
                            <button
                                key={item.id}
                                onClick={() => {
                                    setSelectedFramework(item);
                                    setHasSelectedFramework(true);
                                }}
                                className="group relative overflow-hidden rounded-2xl border-2 border-gray-200 bg-white p-3 transition-all duration-300 hover:-translate-y-1 hover:border-gray-300 hover:shadow-2xl dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700"
                            >
                                {/* Subtle gradient background on hover */}
                                <div className="absolute inset-0 bg-gradient-to-br from-gray-50 to-gray-100 opacity-0 transition-opacity duration-300 group-hover:opacity-100 dark:from-gray-800 dark:to-gray-900" />

                                {/* Icon container with subtle gray gradient */}
                                <div className="relative mb-3 mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200 shadow-lg transition-transform duration-300 group-hover:scale-110 dark:from-gray-700 dark:to-gray-800">
                                    <div className="scale-[2.5] text-gray-700 dark:text-gray-300">{item.icon}</div>
                                </div>

                                {/* Item name */}
                                <h3 className="relative mb-1 text-base font-semibold text-gray-900 transition-colors group-hover:text-gray-950 dark:text-gray-100 dark:group-hover:text-white">
                                    {item.name}
                                </h3>

                                {/* Description */}
                                <p className="relative text-xs text-gray-500 transition-colors group-hover:text-gray-600 dark:text-gray-400 dark:group-hover:text-gray-300">
                                    {item.description || 'Integrate with AgentOps'}
                                </p>

                                {/* Hover indicator */}
                                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-gray-300 to-gray-400 opacity-0 transition-opacity duration-300 group-hover:opacity-100 dark:from-gray-600 dark:to-gray-700" />
                            </button>
                        ))}
                    </div>

                    <div className="mt-16 flex justify-center">
                        <Button
                            variant="outline"
                            onClick={onBack}
                            size="lg"
                            className="gap-2"
                        >
                            <ChevronRight className="h-4 w-4 rotate-180" />
                            Back to framework selection
                        </Button>
                    </div>
                </div>
            </div>
        );
    }

    // Default view with VibeKit (after framework selection)
    return (
        <div className="flex flex-1 flex-col">
            {/* Main content with sidebar */}
            <div className="flex flex-1">
                {/* Left Sidebar - always visible */}
                <div className="w-64 border-r border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                    <Select
                        value={frameworkType}
                        onValueChange={(value: FrameworkType) => setFrameworkType(value)}
                    >
                        <SelectTrigger className="mb-4 w-full">
                            <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="framework">Framework</SelectItem>
                            <SelectItem value="llm">LLM Provider</SelectItem>
                        </SelectContent>
                    </Select>
                    <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {frameworkType === 'llm' ? 'Select an LLM provider' : 'Select a framework'}
                    </h2>

                    <div className="space-y-2">
                        {(frameworkType === 'llm' ? llmProviders : frameworks).map((item) => (
                            <button
                                key={item.id}
                                onClick={() => setSelectedFramework(item)}
                                className={cn(
                                    'w-full rounded-lg p-3 text-left transition-colors',
                                    selectedFramework?.id === item.id
                                        ? 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
                                        : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800/50',
                                )}
                            >
                                <div className="flex items-center gap-2">
                                    {item.icon}
                                    <div className="font-medium">{item.name}</div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Right content area */}
                <div className="flex-1 p-8">
                    <h1 className="mb-8 text-3xl font-bold">
                        Integrate AgentOps with {selectedFramework?.name || 'your project'}
                    </h1>

                    <div className="space-y-6">
                        <div className="mb-6 flex max-w-3xl items-center justify-between">
                            {/* Install mode toggle */}
                            <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-800">
                                <button
                                    onClick={() => setInstallMode('ai')}
                                    className={cn(
                                        "rounded-md px-6 py-2 text-sm font-medium transition-colors",
                                        installMode === 'ai'
                                            ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                                            : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                    )}
                                >
                                    Install with AI
                                </button>
                                <button
                                    onClick={() => setInstallMode('manual')}
                                    className={cn(
                                        "rounded-md px-6 py-2 text-sm font-medium transition-colors",
                                        installMode === 'manual'
                                            ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                                            : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                    )}
                                >
                                    Install manually
                                </button>
                            </div>

                            <Button onClick={() => onNavigateToStep(2)} className="px-4">
                                Verify installation
                                <ChevronRight className="ml-2 h-4 w-4" />
                            </Button>
                        </div>

                        {/* API Key Section - shown in both modes */}
                        <ApiKeySection selectedProject={selectedProject} />

                        {/* Content based on install mode */}
                        {installMode === 'ai' ? (
                            // AI mode - only show VibeKit button
                            <div className="max-w-3xl">
                                <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-10 text-center dark:border-gray-700 dark:bg-gray-900/50">
                                    <div className="space-y-4">
                                        <VibeKitButton
                                            token="k175npb4nsvdza67sy7gy0745d7kdw6f"
                                            buttonText="Install with VibeKit"
                                        />

                                        <div className="flex items-center justify-center gap-6 text-sm text-gray-600 dark:text-gray-400">
                                            <div className="flex items-center gap-1.5">
                                                <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                </svg>
                                                <span>Analyzes your code</span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                </svg>
                                                <span>Installs dependencies</span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                </svg>
                                                <span>Sets up tracking</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            // Manual mode - show install and initialize code blocks
                            <>
                                <div>
                                    <h2 className="mb-2 text-xl font-semibold">1. Install</h2>
                                    <div className="not-prose dark:bg-codeblock relative max-w-3xl overflow-x-auto rounded-xl bg-[#0F1117] dark:ring-1 dark:ring-gray-800/50">
                                        <div className="rounded-t-xl border-b border-gray-900/80 bg-black/40 text-xs leading-6">
                                            <div className="flex justify-between">
                                                <div className="flex">
                                                    <button
                                                        onClick={() => setPackageManager('pip')}
                                                        className={cn(
                                                            'relative px-4 pb-2 pt-2.5 font-medium transition-colors',
                                                            packageManager === 'pip'
                                                                ? 'text-gray-100'
                                                                : 'text-gray-400 hover:text-gray-300',
                                                        )}
                                                    >
                                                        pip
                                                    </button>
                                                    <button
                                                        onClick={() => setPackageManager('uv')}
                                                        className={cn(
                                                            'relative px-4 pb-2 pt-2.5 font-medium transition-colors',
                                                            packageManager === 'uv'
                                                                ? 'text-gray-100'
                                                                : 'text-gray-400 hover:text-gray-300',
                                                        )}
                                                    >
                                                        uv
                                                    </button>
                                                </div>
                                                <button
                                                    className="group px-2 text-gray-400 outline-none"
                                                    onClick={copyInstallCommand}
                                                >
                                                    <div className="group-hover:text-primary-light rounded-md px-2 group-hover:bg-gray-700/60">
                                                        <div className="h-6 w-4">
                                                            <CopyIcon className="h-4 w-4" />
                                                        </div>
                                                    </div>
                                                </button>
                                            </div>
                                        </div>
                                        <div className="overflow-x-auto p-4">
                                            <SyntaxHighlighter
                                                language="bash"
                                                style={customStyle}
                                                className="!m-0 !p-0"
                                                customStyle={{
                                                    background: 'transparent',
                                                    padding: 0,
                                                    margin: 0,
                                                    whiteSpace: 'pre-wrap',
                                                }}
                                            >
                                                {packageManager === 'pip'
                                                    ? selectedFramework?.installCommand || 'pip install agentops'
                                                    : selectedFramework?.installCommand?.replace('pip', 'uv pip') || 'uv pip install agentops'}
                                            </SyntaxHighlighter>
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <h2 className="mb-2 text-xl font-semibold">2. Initialize</h2>
                                    <div className="not-prose dark:bg-codeblock relative max-w-3xl overflow-x-auto rounded-xl bg-[#0F1117] dark:ring-1 dark:ring-gray-800/50">
                                        <div className="rounded-t-xl border-b border-gray-900/80 bg-black/40 text-xs leading-6">
                                            <div className="flex justify-between">
                                                <div className="text-primary-light relative px-2 pb-2 pt-2.5 font-medium text-gray-400">
                                                    <div className="rounded-md px-2">
                                                        <div className="z-10">python</div>
                                                    </div>
                                                </div>
                                                <button
                                                    className="group px-2 text-gray-400 outline-none"
                                                    onClick={copyApiKey}
                                                >
                                                    <div className="group-hover:text-primary-light rounded-md px-2 group-hover:bg-gray-700/60">
                                                        <div className="h-6 w-4">
                                                            <CopyIcon className="h-4 w-4" />
                                                        </div>
                                                    </div>
                                                </button>
                                            </div>
                                        </div>
                                        <div className="overflow-x-auto p-4">
                                            <SyntaxHighlighter
                                                language="python"
                                                style={customStyle}
                                                className="!m-0 !p-0"
                                                customStyle={{
                                                    background: 'transparent',
                                                    padding: 0,
                                                    margin: 0,
                                                    whiteSpace: 'pre-wrap',
                                                }}
                                            >
                                                {`import os
import agentops
from dotenv import load_dotenv

load_dotenv()

# Set OpenAI API key if not already in environment
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "<your_openai_api_key>"

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or '${selectedProject?.api_key || 'your_api_key_here'}'
agentops.init(
    api_key=AGENTOPS_API_KEY,
    default_tags=['${selectedFramework?.name?.toLowerCase() || 'default'}']
)`}
                                            </SyntaxHighlighter>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
} 