import {
  Search01Icon as Search,
  PenTool01Icon as PenTool,
  FileSearchIcon as FileSearch,
  Folder01Icon as FolderTree,
  CodeIcon as Code2,
  CodeFolderIcon,
  Brain02Icon as Brain,
  UserMultiple02Icon as UserMultiple,
  Database01Icon as Database,
  AiChat01Icon as AiChat,
  GridIcon as Vector,
  SearchAreaIcon as SearchArea,
  CProgrammingIcon as Programming,
  MessageQuestionIcon as MessageChatbot,
  AiImageIcon as AiImage,
  WorkflowSquare08Icon as Workflow,
  ChartHistogramIcon as Chart,
  CustomerServiceIcon as CustomerService,
  ArrowDataTransferHorizontalIcon as DataTransfer,
  FileValidationIcon as DocumentValidation,
  SqlIcon as Sql,
  Shield01Icon as ShieldCheck,
} from 'hugeicons-react';
import { AgentTemplate } from '../types';
import PerplexityIcon from '@/components/icons/PerplexityIcon';
import OpenAIAgentsSdk from '@/components/icons/OpenAIAgentsSdk';
import CrewIcon from '@/components/icons/CrewIcon';
import LangchainIcon from '@/components/icons/LangchainIcon';
import AgnoIcon from '@/components/icons/AgnoIcon/AgnoIcon';
import LlamaIndexIcon from '@/components/icons/LlamaIndexIcon';
import LitellmIcon from '@/components/icons/LitellmIcon';
import AnthropicIcon from '@/components/icons/AnthropicIcon';
import GoogleIcon from '@/components/icons/GoogleIcon';
import HuggingFaceIcon from '@/components/icons/HuggingFaceIcon';
import XAIIcon from '@/components/icons/XAIIcon';
import Mem0Icon from '@/components/icons/Mem0Icon';
import AG2Icon from '@/components/icons/AG2Icon';

// OpenAI Agents SDK Examples
export const agentsSdkTemplates: Omit<AgentTemplate, 'tools'>[] = [
  {
    id: 'openai-tools-demo',
    name: 'Tools Demonstration',
    description: 'Comprehensive demo of Code Interpreter, File Search, Image Generation, and Web Search tools',
    icon: <Code2 className="h-5 w-5" />,
  },
  {
    id: 'openai-customer-service',
    name: 'Customer Service System',
    description: 'Multi-agent airline customer service with handoffs between FAQ, seat booking, and triage agents',
    icon: <CustomerService className="h-5 w-5" />,
  },
  {
    id: 'openai-agent-guardrails',
    name: 'Agent Guardrails',
    description: 'Implementing safety guardrails and constraints for AI agents',
    icon: <ShieldCheck className="h-5 w-5" />,
  },
  {
    id: 'openai-agent-patterns',
    name: 'Agent Patterns',
    description: 'Common patterns and best practices for building AI agents',
    icon: <Workflow className="h-5 w-5" />,
  },
];

// Framework-specific templates
export const agentTemplates: AgentTemplate[] = [
  // CrewAI Examples
  {
    id: 'crewai-job-posting',
    name: 'Job Posting Creator',
    description:
      'Multi-agent system with research, writing, and review agents collaborating to create comprehensive job postings',
    tools: [
      {
        name: 'Web Search',
        icon: <Search className="h-4 w-4" />,
      },
      {
        name: 'Serper',
        icon: <>🔍</>,
      },
    ],
    icon: <CrewIcon className="h-6 w-6" />,
    benefit: 'Complete hiring workflow',
  },
  {
    id: 'crewai-markdown-validator',
    name: 'Markdown Validator',
    description: 'Automated markdown document validation and formatting system',
    tools: [
      {
        name: 'Document Analysis',
        icon: <DocumentValidation className="h-4 w-4" />,
      },
    ],
    icon: <CrewIcon className="h-6 w-6" />,
    benefit: 'Document automation',
  },

  // Agno Examples
  {
    id: 'agno-research-team',
    name: 'Research Team Collaboration',
    description:
      'Four specialized agents (Reddit, HackerNews, Academic, Twitter) collaborating to provide comprehensive research insights',
    tools: [
      {
        name: 'Google Search',
        icon: <GoogleIcon className="h-4 w-4" />,
      },
      {
        name: 'HackerNews',
        icon: <>📰</>,
      },
      {
        name: 'Arxiv',
        icon: <>📚</>,
      },
      {
        name: 'DuckDuckGo',
        icon: <>🦆</>,
      },
    ],
    icon: <AgnoIcon className="h-6 w-6" />,
    benefit: 'Multi-perspective research',
  },
  {
    id: 'agno-tool-integrations',
    name: 'Tool Integration Suite',
    description: 'Comprehensive demonstration of various tool integrations including web search, file operations, and APIs',
    tools: [
      {
        name: 'Multiple Tools',
        icon: <Programming className="h-4 w-4" />,
      },
    ],
    icon: <AgnoIcon className="h-6 w-6" />,
    benefit: 'Tool orchestration',
  },
  {
    id: 'agno-workflow-setup',
    name: 'Workflow Automation',
    description: 'Setting up complex agent workflows with task dependencies and orchestration',
    tools: [
      {
        name: 'Workflow Engine',
        icon: <Workflow className="h-4 w-4" />,
      },
    ],
    icon: <AgnoIcon className="h-6 w-6" />,
    benefit: 'Process automation',
  },

  // LangChain Example
  {
    id: 'langchain-example',
    name: 'LangChain Integration',
    description: 'Building AI applications with LangChain\'s modular components and chains',
    tools: [
      {
        name: 'LangChain Tools',
        icon: <LangchainIcon className="h-4 w-4" />,
      },
    ],
    icon: <LangchainIcon className="h-6 w-6" />,
    benefit: 'Modular AI development',
  },

  // AutoGen/AG2 Examples
  {
    id: 'autogen-chat',
    name: 'AutoGen Agent Chat',
    description: 'Interactive conversations between multiple AI agents with different roles and capabilities',
    tools: [
      {
        name: 'Agent Chat',
        icon: <AiChat className="h-4 w-4" />,
      },
    ],
    icon: <UserMultiple className="h-6 w-6" />,
    benefit: 'Multi-agent dialogue',
  },
  {
    id: 'autogen-math',
    name: 'Math Problem Solver',
    description: 'Specialized agent for solving complex mathematical problems with step-by-step explanations',
    tools: [
      {
        name: 'Math Solver',
        icon: <Chart className="h-4 w-4" />,
      },
    ],
    icon: <Brain className="h-6 w-6" />,
    benefit: 'Educational assistant',
  },
  {
    id: 'ag2-wikipedia',
    name: 'Wikipedia Research Assistant',
    description: 'AG2 agent with Wikipedia search capabilities for comprehensive research',
    tools: [
      {
        name: 'Wikipedia',
        icon: <>📖</>,
      },
    ],
    icon: <AG2Icon className="h-6 w-6" />,
    benefit: 'Knowledge retrieval',
  },

  // LlamaIndex Example
  {
    id: 'llamaindex-rag',
    name: 'RAG Application',
    description: 'Building retrieval-augmented generation applications with LlamaIndex for enhanced context',
    tools: [
      {
        name: 'Vector Store',
        icon: <Vector className="h-4 w-4" />,
      },
    ],
    icon: <LlamaIndexIcon className="h-6 w-6" />,
    benefit: 'Context-aware AI',
  },

  // LiteLLM Example
  {
    id: 'litellm-unified',
    name: 'Unified LLM Interface',
    description: 'Use 100+ LLMs with a unified API interface for easy model switching and comparison',
    tools: [
      {
        name: 'Multi-LLM',
        icon: <DataTransfer className="h-4 w-4" />,
      },
    ],
    icon: <LitellmIcon className="h-6 w-6" />,
    benefit: 'Model flexibility',
  },

  // Mem0 Examples
  {
    id: 'mem0-memory',
    name: 'Persistent Memory System',
    description: 'Building agents with long-term memory capabilities for personalized interactions',
    tools: [
      {
        name: 'Memory Store',
        icon: <Database className="h-4 w-4" />,
      },
    ],
    icon: <Mem0Icon className="h-6 w-6" />,
    benefit: 'Stateful conversations',
  },

  // Anthropic Examples
  {
    id: 'anthropic-claude',
    name: 'Claude Integration',
    description: 'Building applications with Claude\'s advanced reasoning capabilities and tool use',
    tools: [
      {
        name: 'Claude Tools',
        icon: <AnthropicIcon className="h-4 w-4" />,
      },
    ],
    icon: <AnthropicIcon className="h-6 w-6" />,
    benefit: 'Advanced reasoning',
  },

  // Google ADK Example
  {
    id: 'google-adk-approval',
    name: 'Human-in-the-Loop System',
    description: 'Implementing human approval workflows for critical AI agent decisions',
    tools: [
      {
        name: 'Approval Flow',
        icon: <ShieldCheck className="h-4 w-4" />,
      },
    ],
    icon: <GoogleIcon className="h-6 w-6" />,
    benefit: 'Safe automation',
  },

  // SmolAgents Examples
  {
    id: 'smolagents-sql',
    name: 'Text-to-SQL Agent',
    description: 'Natural language to SQL query generation for database interactions',
    tools: [
      {
        name: 'SQL Generator',
        icon: <Sql className="h-4 w-4" />,
      },
    ],
    icon: <HuggingFaceIcon className="h-6 w-6" />,
    benefit: 'Database queries',
  },
  {
    id: 'smolagents-multi',
    name: 'Multi-Agent System',
    description: 'Orchestrating multiple SmolAgents for complex task decomposition',
    tools: [
      {
        name: 'Agent Network',
        icon: <UserMultiple className="h-4 w-4" />,
      },
    ],
    icon: <HuggingFaceIcon className="h-6 w-6" />,
    benefit: 'Task decomposition',
  },

  // XAI Examples
  {
    id: 'xai-grok',
    name: 'Grok Integration',
    description: 'Building applications with xAI\'s Grok model for advanced language understanding',
    tools: [
      {
        name: 'Grok API',
        icon: <XAIIcon className="h-4 w-4" />,
      },
    ],
    icon: <XAIIcon className="h-6 w-6" />,
    benefit: 'Cutting-edge AI',
  },
  {
    id: 'xai-vision',
    name: 'Grok Vision',
    description: 'Multimodal AI applications with Grok\'s vision capabilities',
    tools: [
      {
        name: 'Vision API',
        icon: <AiImage className="h-4 w-4" />,
      },
    ],
    icon: <XAIIcon className="h-6 w-6" />,
    benefit: 'Multimodal AI',
  },

  // Scratch option
  {
    id: 'scratch',
    name: 'Start from Scratch',
    description: 'Create a new agent system from scratch with a basic template',
    tools: [],
    icon: <Code2 className="h-6 w-6" />,
  },
];
