import { OpenAIIcon, CrewAIIcon, LangChainIcon, LlamaIndexIcon } from '@/components/icons';
import { Framework } from '../types';

export const newProjectFrameworks: Framework[] = [
  {
    id: 'openaiagentssdk',
    name: 'OpenAI Agents SDK',
    description: 'Multi-agent conversation framework',
    icon: <OpenAIIcon className="h-6 w-6" />,
    benefit: 'Recommended',
    installCommand: 'pip install agentops autogen',
  },
  {
    id: 'crewai',
    name: 'CrewAI',
    description: 'Role-based agent orchestration framework',
    icon: <CrewAIIcon className="h-6 w-6" />,
    installCommand: 'pip install -U agentops crewai',
  },
  {
    id: 'llamaindex',
    name: 'LlamaIndex',
    description: 'Data-aware agent framework',
    icon: <LlamaIndexIcon className="h-6 w-6" />,
    installCommand: 'pip install agentops llama-index',
  },
  {
    id: 'langgraph',
    name: 'LangGraph',
    description: 'Graph-based agent orchestration',
    icon: <LangChainIcon className="h-6 w-6" />,
    installCommand: 'pip install agentops langgraph',
  },
];

export const frameworkToCLI: Record<string, string> = {
  crewai: 'crewai',
  openaiagentssdk: 'openai_agents_sdk',
  llamaindex: 'llama_index',
  langgraph: 'langgraph',
};

export const templateToCLI: Record<string, string> = {
  researcher: 'research',
  'content-creator': 'content_creator',
  'system-analyzer': 'system_analyzer',
  scratch: 'basic',
};

export const templateToAgentName: Record<string, string> = {
  researcher: 'research_agent',
  'content-creator': 'content_creator',
  'system-analyzer': 'system_analyzer',
  scratch: 'my_agent',
};
