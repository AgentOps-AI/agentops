import { AG2Icon, AgnoIcon, OpenAIIcon, XAIIcon } from '@/components/icons';
import CrewIcon from '@/components/icons/CrewIcon';
import MicrosoftIcon from '@/components/icons/MicrosoftIcon';
import ChatgptIcon from '@/components/icons/ChatgptIcon';
import LlamaIndexIcon from '@/components/icons/LlamaIndexIcon';
import LangchainIcon from '@/components/icons/LangchainIcon';
import LitellmIcon from '@/components/icons/LitellmIcon';
import HuggingFaceIcon from '@/components/icons/HuggingFaceIcon';
import GoogleIcon from '@/components/icons/GoogleIcon';
import GeminiIcon from '@/components/icons/GeminiIcon';
import AnthropicIcon from '@/components/icons/AnthropicIcon';
import Mem0Icon from '@/components/icons/Mem0Icon';
import IBMIcon from '@/components/icons/IBMIcon';

export const exampleNotebooks = [
    // CrewAI Examples
    {
        id: 'crewai-job-posting',
        name: 'Job Posting Generator',
        framework: 'CrewAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/crewai/job_posting.ipynb',
        description: [
            '• Multi-agent system for creating job postings',
            '• Research Analyst for company culture insights',
            '• Writer Agent for compelling descriptions',
            '• Review Specialist for polish and accuracy'
        ],
        icon: <CrewIcon className="h-5 w-5" />,
    },
    // OpenAI Agents SDK Examples
    // Additional OpenAI Examples
    {
        id: 'openai-agents-customer-service',
        name: 'Customer Service System',
        framework: 'OpenAI Agents SDK',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai_agents/customer_service_agent.ipynb',
        description: [
            '• Multi-agent airline customer service system',
            '• FAQ Agent for common questions',
            '• Seat Booking Agent for reservations',
            '• Triage Agent for routing requests'
        ],
        icon: <ChatgptIcon className="h-5 w-5" />,
    },

    // Google ADK Example
    {
        id: 'google-adk-approval',
        name: 'Human Approval Workflow',
        framework: 'Google ADK',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/google_adk/human_approval.ipynb',
        description: [
            '• Implement human-in-the-loop workflows',
            '• Add approval steps for critical decisions',
            '• Build safe and controlled AI systems'
        ],
        icon: <GoogleIcon className="h-5 w-5" />,
    },

    // Agno Examples
    {
        id: 'agno-research-team',
        name: 'Research Team Collaboration',
        framework: 'Agno',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/agno/agno_research_team.ipynb',
        description: [
            '• Four specialized research agents working together',
            '• Reddit, HackerNews, Academic, and Twitter researchers',
            '• Collaborative discussion and consensus building',
            '• Multi-perspective comprehensive research'
        ],
        icon: <AgnoIcon className="h-5 w-5" />,
    },

    // AG2 Examples
    {
        id: 'ag2-async-human-input',
        name: 'Agent Chat with Async Human Inputs',
        framework: 'AG2',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/ag2/async_human_input.ipynb',
        description: [
            '• Build interactive agents that handle asynchronous human inputs',
            '• Create interview question generators with real-time feedback loops',
            '• Implement human-in-the-loop interactions'
        ],
        icon: <AG2Icon className="h-5 w-5" />,
    },

    // AutoGen Examples
    {
        id: 'autogen-agent-chat',
        name: 'Multi-Agent Chat',
        framework: 'AutoGen',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/autogen/AgentChat.ipynb',
        description: [
            '• Create conversations between multiple AI agents',
            '• Implement different agent roles and capabilities',
            '• Build collaborative agent systems'
        ],
        icon: <MicrosoftIcon className="h-5 w-5" />,
    },

    // LangGraph Example
    {
        id: 'langgraph-example',
        name: 'LangGraph Agent Workflows',
        framework: 'LangGraph',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/langgraph/langgraph_example.ipynb',
        description: [
            '• Build stateful multi-agent workflows',
            '• Create complex agent orchestrations',
            '• Implement conditional logic and cycles'
        ],
        icon: <LangchainIcon className="h-5 w-5" />,
    },
    // SmolAgents Examples
    {
        id: 'smolagents-text-to-sql',
        name: 'Text-to-SQL Agent',
        framework: 'SmolAgents',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/smolagents/text_to_sql.ipynb',
        description: [
            '• Natural language to SQL query generation',
            '• Database interaction through conversation',
            '• Support for complex query building'
        ],
        icon: <HuggingFaceIcon className="h-5 w-5" />,
    },

    // LlamaIndex Example
    {
        id: 'llamaindex-example',
        name: 'RAG Application',
        framework: 'LlamaIndex',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/llamaindex/llamaindex_example.ipynb',
        description: [
            '• Build intelligent document Q&A systems',
            '• Implement vector stores and retrieval augmentation',
            '• Create context-aware responses with full observability'
        ],
        icon: <LlamaIndexIcon className="h-5 w-5" />,
    },

    // LiteLLM Example
    {
        id: 'litellm-example',
        name: 'Unified LLM Interface',
        framework: 'LiteLLM',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/litellm/litellm_example.ipynb',
        description: [
            '• Use 100+ LLMs with a unified interface',
            '• Work with OpenAI, Anthropic, Cohere, and more',
            '• Maintain consistent AgentOps tracking across all models'
        ],
        icon: <LitellmIcon className="h-5 w-5" />,
    },

    // Mem0 Examples
    {
        id: 'mem0-memory',
        name: 'Memory System',
        framework: 'Mem0',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/mem0/mem0_memory_example.ipynb',
        description: [
            '• Build agents with persistent memory',
            '• Store and retrieve user preferences',
            '• Create personalized AI experiences'
        ],
        icon: <Mem0Icon className="h-5 w-5" />,
    },
    {
        id: 'mem0-memoryclient',
        name: 'Memory Client Example',
        framework: 'Mem0',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/mem0/mem0_memoryclient_example.ipynb',
        description: [
            '• Advanced memory client implementation',
            '• Cross-session memory management',
            '• Build stateful conversational agents'
        ],
        icon: <Mem0Icon className="h-5 w-5" />,
    },

    // Anthropic Examples
    {
        id: 'anthropic-sync',
        name: 'Claude Integration (Sync)',
        framework: 'Anthropic',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/anthropic/anthropic-example-sync.ipynb',
        description: [
            '• Get started with Anthropic\'s Claude models',
            '• Implement synchronous API calls',
            '• Monitor conversational AI with AgentOps tracking'
        ],
        icon: <AnthropicIcon className="h-5 w-5" />,
    },
    {
        id: 'anthropic-async',
        name: 'Claude Integration (Async)',
        framework: 'Anthropic',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/anthropic/anthropic-example-async.ipynb',
        description: [
            '• Asynchronous Claude API implementation',
            '• Improved performance and scalability',
            '• Handle concurrent requests efficiently'
        ],
        icon: <AnthropicIcon className="h-5 w-5" />,
    },
    {
        id: 'anthropic-tools',
        name: 'Understanding Tools with Claude',
        framework: 'Anthropic',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/anthropic/agentops-anthropic-understanding-tools.ipynb',
        description: [
            '• Explore Claude\'s tool-use capabilities',
            '• Implement function calling and API integrations',
            '• Extract structured data with comprehensive examples'
        ],
        icon: <AnthropicIcon className="h-5 w-5" />,
    },
    {
        id: 'smolagents-multi-system',
        name: 'Multi-Agent System',
        framework: 'SmolAgents',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/smolagents/multi_smolagents_system.ipynb',
        description: [
            '• Orchestrate multiple SmolAgents',
            '• Complex task decomposition',
            '• Collaborative problem solving'
        ],
        icon: <HuggingFaceIcon className="h-5 w-5" />,
    },

    // XAI Examples
    {
        id: 'xai-grok',
        name: 'Grok Integration',
        framework: 'xAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/xai/grok_examples.ipynb',
        description: [
            '• Integrate xAI\'s Grok models',
            '• Advanced language understanding',
            '• Monitor performance with AgentOps'
        ],
        icon: <XAIIcon className="h-5 w-5" />,
    },
    {
        id: 'xai-grok-vision',
        name: 'Grok Vision',
        framework: 'xAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/xai/grok_vision_examples.ipynb',
        description: [
            '• Multimodal AI with Grok Vision',
            '• Process images and text together',
            '• Build vision-enabled applications'
        ],
        icon: <XAIIcon className="h-5 w-5" />,
    },

    // Agno Examples

    {
        id: 'agno-workflow-setup',
        name: 'Workflow Automation',
        framework: 'Agno',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/agno/agno_workflow_setup.ipynb',
        description: [
            '• Complex agent workflows with dependencies',
            '• Task orchestration and automation',
            '• Build scalable agent systems'
        ],
        icon: <AgnoIcon className="h-5 w-5" />,
    },
    {
        id: 'agno-basic-agents',
        name: 'Basic Agent Setup',
        framework: 'Agno',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/agno/agno_basic_agents.ipynb',
        description: [
            '• Introduction to Agno agent framework',
            '• Create and configure basic agents',
            '• Understand core concepts and patterns'
        ],
        icon: <AgnoIcon className="h-5 w-5" />,
    },
    {
        id: 'agno-async-operations',
        name: 'Async Agent Operations',
        framework: 'Agno',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/agno/agno_async_operations.ipynb',
        description: [
            '• Asynchronous agent operations',
            '• Concurrent task execution',
            '• Performance optimization techniques'
        ],
        icon: <AgnoIcon className="h-5 w-5" />,
    },
    {
        id: 'openai-agents-tools',
        name: 'Tools Demonstration',
        framework: 'OpenAI Agents SDK',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai_agents/agents_tools.ipynb',
        description: [
            '• Code Interpreter for calculations and data analysis',
            '• File Search through vector stores and documents',
            '• Image Generation with AI models',
            '• Web Search for real-time information'
        ],
        icon: <ChatgptIcon className="h-5 w-5" />,
    },
    {
        id: 'openai-agents-guardrails',
        name: 'Agent Guardrails',
        framework: 'OpenAI Agents SDK',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai_agents/agent_guardrails.ipynb',
        description: [
            '• Implement safety constraints for AI agents',
            '• Control agent behavior and responses',
            '• Ensure compliance with guidelines'
        ],
        icon: <ChatgptIcon className="h-5 w-5" />,
    },
    {
        id: 'openai-agents-patterns',
        name: 'Agent Patterns',
        framework: 'OpenAI Agents SDK',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai_agents/agent_patterns.ipynb',
        description: [
            '• Common patterns for building AI agents',
            '• Best practices and architectural approaches',
            '• Reusable templates for agent development'
        ],
        icon: <OpenAIIcon className="h-5 w-5" />,
    },
    {
        id: 'openai-sync',
        name: 'OpenAI Example (Sync)',
        framework: 'OpenAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai/openai_example_sync.ipynb',
        description: [
            '• Create story-generating chatbots using GPT models',
            '• Implement synchronous API calls with OpenAI',
            '• Track chat completions and streaming responses with AgentOps'
        ],
        icon: <OpenAIIcon className="h-5 w-5" />,
    },
    {
        id: 'openai-async',
        name: 'OpenAI Example (Async)',
        framework: 'OpenAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai/openai_example_async.ipynb',
        description: [
            '• Build asynchronous OpenAI applications',
            '• Improve performance and scalability',
            '• Handle multiple concurrent API requests efficiently'
        ],
        icon: <OpenAIIcon className="h-5 w-5" />,
    },
    {
        id: 'openai-web-search',
        name: 'Web Search with OpenAI',
        framework: 'OpenAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai/web_search.ipynb',
        description: [
            '• Use OpenAI\'s new Responses API with built-in web search',
            '• Create multimodal, tool-augmented interactions',
            '• Search the internet and analyze images in a single API call'
        ],
        icon: <OpenAIIcon className="h-5 w-5" />,
    },
    {
        id: 'openai-multi-tool',
        name: 'Multi Tool Orchestration',
        framework: 'OpenAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai/multi_tool_orchestration.ipynb',
        description: [
            '• Implement advanced RAG workflows with intelligent routing',
            '• Combine web search with vector databases (Pinecone)',
            '• Generate context-aware responses using real-time and stored knowledge'
        ],
        icon: <OpenAIIcon className="h-5 w-5" />,
    },
    // Google Gemini Example
    {
        id: 'google-genai-example',
        name: 'Google Gemini Example',
        framework: 'Google Gemini',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/google_genai/google_genai_example.ipynb',
        description: [
            '• Harness Google\'s Gemini models for multimodal AI',
            '• Process text, images, and code understanding',
            '• Track all capabilities with AgentOps'
        ],
        icon: <GeminiIcon className="h-5 w-5" />,
    },

    // WatsonX Examples
    {
        id: 'watsonx-text-chat',
        name: 'WatsonX Text & Chat',
        framework: 'WatsonX',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/watsonx/watsonx-text-chat.ipynb',
        description: [
            '• Integrate IBM WatsonX with conversational AI',
            '• Build enterprise-grade chat applications',
            '• Track and optimize WatsonX model performance'
        ],
        icon: <IBMIcon className="h-5 w-5" />,
    },
    {
        id: 'watsonx-streaming',
        name: 'WatsonX Streaming',
        framework: 'WatsonX',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/watsonx/watsonx-streaming.ipynb',
        description: [
            '• Implement streaming responses with WatsonX',
            '• Build real-time AI applications',
            '• Optimize for low-latency interactions'
        ],
        icon: <IBMIcon className="h-5 w-5" />,
    },
    {
        id: 'watsonx-tokenization',
        name: 'WatsonX Tokenization Model',
        framework: 'WatsonX',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/watsonx/watsonx-tokeniation-model.ipynb',
        description: [
            '• Understand token usage and optimization',
            '• Implement custom tokenization strategies',
            '• Monitor and control token costs'
        ],
        icon: <IBMIcon className="h-5 w-5" />,
    },
    {
        id: 'ag2-wikipedia-search',
        name: 'AG2 Wikipedia Search Tools',
        framework: 'AG2',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/ag2/tools_wikipedia_search.ipynb',
        description: [
            '• Integrate Wikipedia search capabilities into AG2 agents',
            '• Use WikipediaQueryRunTool for quick searches',
            '• Extract detailed content with WikipediaPageLoadTool'
        ],
        icon: <AG2Icon className="h-5 w-5" />,
    },
    {
        id: 'agno-tool-integrations',
        name: 'Tool Integration Suite',
        framework: 'Agno',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/agno/agno_tool_integrations.ipynb',
        description: [
            '• Comprehensive tool integration examples',
            '• Web search, file operations, and API calls',
            '• Build agents with multiple capabilities'
        ],
        icon: <AgnoIcon className="h-5 w-5" />,
    },
    {
        id: 'crewai-markdown-validator',
        name: 'Markdown Validator',
        framework: 'CrewAI',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/crewai/markdown_validator.ipynb',
        description: [
            '• Automated markdown document validation',
            '• Format checking and correction',
            '• Collaborative document processing'
        ],
        icon: <CrewIcon className="h-5 w-5" />,
    },
    {
        id: 'autogen-math-agent',
        name: 'Math Problem Solver',
        framework: 'AutoGen',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/autogen/MathAgent.ipynb',
        description: [
            '• Specialized agent for solving mathematical problems',
            '• Step-by-step solution explanations',
            '• Support for complex calculations'
        ],
        icon: <MicrosoftIcon className="h-5 w-5" />,
    },
    // LangChain Example
    {
        id: 'langchain-example',
        name: 'LangChain Agent Implementation',
        framework: 'LangChain',
        colabUrl: 'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/langchain/langchain_examples.ipynb',
        description: [
            '• Integrate AgentOps with LangChain agents',
            '• Use LangchainCallbackHandler for automatic tracking',
            '• Monitor tool usage and agent actions comprehensively'
        ],
        icon: <LangchainIcon className="h-5 w-5" />,
    },
]; 