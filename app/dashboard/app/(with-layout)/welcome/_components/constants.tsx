// Import icons from ./icons
import {
  OpenAIIcon,
  CrewAIIcon,
  AutogenIcon,
  AG2Icon,
  AgentStackIcon,
  CamelAIIcon,
  LangGraphIcon,
  LlamaIndexIcon,
  CohereIcon,
  HuggingFaceIcon,
  TaskweaverIcon,
  LlamaStackIcon,
  LiteLLMIcon,
  OllamaIcon,
  AnthropicIcon,
  GeminiIcon,
  GroqIcon,
  MistralIcon,
  CerebrasIcon,
  LlamaFSIcon,
  AgnoIcon,
  IBMIcon,
  TSIcon,
  XAIIcon,
  OpenRouterIcon,
  DeepseekIcon,
  QwenIcon
} from '@/components/icons';

import { CodeIcon as Code2 } from 'hugeicons-react';

export const useCases = [
  'Agent Development',
  'Debugging & Monitoring',
  'Evaluation & Testing',
  'Personal Project',
  'Just Curious',
];

export const jobTitles = [
  'Engineer',
  'Data Scientist',
  'Product Manager',
  'Director/Executive',
  'Student',
  'Non-technical',
  'Other',
];

export const companySizes = ['Just me', '2-5', '5-25', '25-100', '100+'];

export const stages = [
  'Just playing around',
  'Actively prototyping',
  'Deploying systems online',
  'Already in production',
];

export const referralSources = [
  'LinkedIn',
  'Google',
  'Youtube',
  'Twitter',
  'External docs',
  'Hackathon events',
  'Friend',
  'Other',
];

export const frameworks = [
  {
    id: 'crewai',
    title: 'CrewAI',
    docLink: 'https://docs.crewai.com',
    ytLink: 'https://www.youtube.com/watch?v=X1tH1LKs9M0',
    logo: <CrewAIIcon className="h-4 w-4" />,
  },
  {
    id: 'openai_agents_sdk',
    title: 'OpenAI Agents SDK',
    docLink: 'https://docs.agentops.ai/v1/integrations/agentssdk',
    ytLink: '',
    logo: <OpenAIIcon className="h-4 w-4" />,
  },
  {
    id: 'langgraph',
    title: 'LangGraph',
    docLink: 'https://python.langchain.com/docs/langgraph',
    ytLink: '',
    logo: <LangGraphIcon className="h-4 w-4" />,
  },
  {
    id: 'autogen',
    title: 'Autogen',
    docLink: 'https://docs.agentops.ai/v2/integrations/autogen',
    ytLink: 'https://www.youtube.com/watch?v=W8RiKA8QckU',
    logo: <AutogenIcon className="h-4 w-4" />,
  },
  {
    id: 'ag2',
    title: 'AG2',
    docLink: 'https://docs.agentops.ai/v2/integrations/ag2',
    ytLink: 'https://www.youtube.com/watch?v=W8RiKA8QckU',
    logo: <AG2Icon className="h-4 w-4" />,
  },
  {
    id: 'agno',
    title: 'Agno',
    docLink: 'https://docs.agentops.ai/v2/integrations/agno',
    ytLink: '',
    logo: <AgnoIcon className="h-4 w-4" />,
  },
  {
    id: 'adk',
    title: 'Google ADK',
    docLink: 'https://docs.agentops.ai/v2/integrations/adk',
    ytLink: '',
    logo: <GeminiIcon className="h-4 w-4" />,
  },
  {
    id: 'ts',
    title: 'Typescript',
    docLink: 'https://docs.agentops.ai/v2/usage/typescript-sdk',
    ytLink: '',
    logo: <TSIcon className="h-4 w-4" />,
  },
  {
    id: 'llamaindex',
    title: 'LlamaIndex',
    docLink: 'https://docs.llamaindex.ai/en/stable/',
    ytLink: 'https://www.youtube.com/watch?v=9wDq_9d0kbM',
    logo: <LlamaIndexIcon className="h-4 w-4" />,
  },
  {
    id: 'smolagents',
    title: 'SmolAgents',
    docLink: 'https://docs.agentops.ai/v1/integrations/smolagents',
    ytLink: '',
    logo: <HuggingFaceIcon className="h-4 w-4" />,
  },
  {
    id: 'camelai',
    title: 'Camel AI',
    docLink: 'https://docs.camel-ai.org/',
    ytLink: 'https://www.youtube.com/@CamelAI',
    logo: <CamelAIIcon className="h-4 w-4" />,
  },
  {
    id: 'Taskweaver',
    title: 'TaskWeaver',
    docLink: 'https://docs.agentops.ai/v1/integrations/taskweaver',
    ytLink: '',
    logo: <TaskweaverIcon className="h-4 w-4" />,
  },
  {
    id: 'llamastack',
    title: 'LlamaStack',
    docLink: 'https://docs.agentops.ai/v1/integrations/llama_stack',
    ytLink: '',
    logo: <LlamaStackIcon className="h-4 w-4" />,
  },
  {
    id: 'ibm',
    title: 'IBM WatsonX',
    docLink: 'https://docs.agentops.ai/v2/integrations/ibm',
    ytLink: '',
    logo: <IBMIcon className="h-4 w-4" />,
  },
  {
    id: 'llamafs',
    title: 'LlamaFS',
    docLink: 'https://github.com/iyaja/llama-fs',
    ytLink: '',
    logo: <LlamaFSIcon className="h-4 w-4" />,
  },
  {
    id: 'agentstack',
    title: 'AgentStack',
    docLink: 'https://github.com/AgentOps-AI/AgentStack',
    ytLink:
      'https://www.loom.com/share/68d796b13cd94647bd1d7fae12b2358e?sid=7fdf595b-de84-4d51-9a81-ef1e9c8ac71c',
    logo: <AgentStackIcon className="h-4 w-4" />,
  },
  {
    id: 'other',
    title: 'Other',
    docLink: '',
    ytLink: '',
    logo: <Code2 className="h-4 w-4" />,
  },
];

export const providers = [
  {
    id: 'openai',
    title: 'OpenAI',
    docLink: 'https://docs.agentops.ai/v1/integrations/openai',
    ytLink: 'https://www.loom.com/share/0e0d2986f3d644a58d1e186dc81cd8b1',
    logo: <OpenAIIcon className="h-4 w-4" />,
  },
  {
    id: 'anthropic',
    title: 'Anthropic',
    docLink: 'https://docs.agentops.ai/v1/integrations/anthropic',
    ytLink: 'https://www.youtube.com/watch?v=t9kz9P6cEYM',
    logo: <AnthropicIcon className="h-4 w-4" />,
  },
  {
    id: 'gemini',
    title: 'Gemini',
    docLink:
      'https://developers.googleblog.com/en/bringing-ai-agents-to-production-with-gemini-api/',
    ytLink: '',
    logo: <GeminiIcon className="h-4 w-4" />,
  },
  {
    id: 'cohere',
    title: 'Cohere',
    docLink: 'https://docs.agentops.ai/v1/integrations/cohere',
    ytLink: '',
    logo: <CohereIcon className="h-4 w-4" />,
  },
  {
    id: 'groq',
    title: 'Groq',
    docLink: 'https://docs.agentops.ai/v1/integrations/groq',
    ytLink: 'https://www.youtube.com/watch?v=SFXlvPo-CEs',
    logo: <GroqIcon className="h-4 w-4" />,
  },
  {
    id: 'mistral',
    title: 'Mistral',
    docLink: 'https://docs.agentops.ai/v1/integrations/mistral',
    ytLink: '',
    logo: <MistralIcon className="h-4 w-4" />,
  },
  {
    id: 'deepseek',
    title: 'DeepSeek',
    docLink: 'https://docs.agentops.ai/v2/integrations/ollama',
    ytLink: '',
    logo: <DeepseekIcon className="h-4 w-4" />,
  },
  {
    id: 'qwen',
    title: 'Qwen',
    docLink: 'https://docs.agentops.ai/v2/integrations/ollama',
    ytLink: '',
    logo: <QwenIcon className="h-4 w-4" />,
  },
  {
    id: 'xai',
    title: 'Grok',
    docLink: 'https://docs.agentops.ai/v1/integrations/xai',
    ytLink: '',
    logo: <XAIIcon className="h-4 w-4" />,
  },
  {
    id: 'cerebras',
    title: 'Cerebras',
    docLink: 'https://docs.cerebras.ai/',
    ytLink: '',
    logo: <CerebrasIcon className="h-4 w-4" />,
  },
  {
    id: 'litellm',
    title: 'LiteLLM',
    docLink: 'https://docs.litellm.ai',
    ytLink: '',
    logo: <LiteLLMIcon className="h-4 w-4" />,
  },
  {
    id: 'openrouter',
    title: 'OpenRouter',
    docLink: 'https://docs.agentops.ai/v2/integrations/openai',
    ytLink: '',
    logo: <OpenRouterIcon className="h-4 w-4" />,
  },
  {
    id: 'ollama',
    title: 'Ollama',
    docLink: 'https://docs.agentops.ai/v1/integrations/ollama',
    ytLink: 'https://www.youtube.com/watch?v=9wDq_9d0kbM',
    logo: <OllamaIcon className="h-4 w-4" />,
  },
];

// Keep the original technologies array for backward compatibility
export const technologies = [...frameworks, ...providers];
