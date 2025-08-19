import AnthropicIcon from '@/components/icons/AnthropicIcon';
import AgentstackIcon from '@/components/icons/AgentstackIcon';
import ChatgptIcon from '@/components/icons/ChatgptIcon';
import CohereIcon from '@/components/icons/CohereIcon';
import CrewIcon from '@/components/icons/CrewIcon';
import GeminiIcon from '@/components/icons/GeminiIcon';
import GroqIcon from '@/components/icons/GroqIcon';
import LangchainIcon from '@/components/icons/LangchainIcon';
import LitellmIcon from '@/components/icons/LitellmIcon';
import LlamaIndexIcon from '@/components/icons/LlamaIndexIcon';
import MicrosoftIcon from '@/components/icons/MicrosoftIcon';
import MistralAiIcon from '@/components/icons/MistralAiIcon';
import MultionIcon from '@/components/icons/MultionIcon';
import OllamaIcon from '@/components/icons/OllamaIcon';
import DeepseekIcon from '@/components/icons/DeepseekIcon';
import QwenIcon from '@/components/icons/QwenIcon';
import AG2Icon from '@/components/icons/AG2Icon';
import XAIIcon from '@/components/icons/XAIIcon';
import Logo from '@/components/icons/Logo';
import PerplexityIcon from '@/components/icons/PerplexityIcon';
import AgnoIcon from '@/components/icons/AgnoIcon/AgnoIcon';
import XpanderIcon from '@/components/icons/XpanderIcon';
import IBMIcon from '@/components/icons/IBMIcon';
import Mem0Icon from '@/components/icons/Mem0Icon';

const iconMap = {
  agentstack: <AgentstackIcon />,
  crewai: <CrewIcon />,
  openai: <ChatgptIcon />,
  swarm: <ChatgptIcon />,
  gpt: <ChatgptIcon />,
  cohere: <CohereIcon />,
  langchain: <LangchainIcon />,
  ollama: <OllamaIcon />,
  deepseek: <DeepseekIcon />,
  qwen: <QwenIcon />,
  groq: <GroqIcon />,
  mistralai: <MistralAiIcon />,
  mixtral: <MistralAiIcon />,
  anthropic: <AnthropicIcon />,
  claude: <AnthropicIcon />,
  multion: <MultionIcon />,
  llama: <LlamaIndexIcon />,
  autogen: <MicrosoftIcon />,
  ag2: <AG2Icon />,
  litellm: <LitellmIcon />,
  gemini: <GeminiIcon />,
  xai: <XAIIcon />,
  perplexity: <PerplexityIcon />,
  agno: <AgnoIcon />,
  xpander: <XpanderIcon />,
  watson: <IBMIcon />,
  mem0: <Mem0Icon />,
};

export const getIconForModel = (model: string): React.ReactNode | null => {
  if (!model || typeof model !== 'string') {
    return <Logo />;
  }
  const lowerModel = model.toLowerCase();

  // Check for specific model name patterns
  if (lowerModel.includes('grok')) {
    return iconMap.xai || <XAIIcon />;
  }

  // Check for o1, o2, o3, etc. pattern (GPT models)
  if (/o[0-9]/.test(lowerModel)) {
    return iconMap.gpt || <ChatgptIcon />;
  }

  // Check for -ada pattern (GPT models)
  if (lowerModel.includes('-ada')) {
    return iconMap.gpt || <ChatgptIcon />;
  }

  // Check for gemma pattern (Gemini models)
  if (lowerModel.includes('gemma')) {
    return iconMap.gemini || <GeminiIcon />;
  }

  // Check for mixtral pattern (Mistral models)
  if (lowerModel.includes('mixtral') || lowerModel.includes('mistral')) {
    return iconMap.mistralai || <MistralAiIcon />;
  }

  if (lowerModel.includes('perplexity')) {
    return iconMap.perplexity || <PerplexityIcon />;
  }
  if (lowerModel.includes('sonar')) {
    return iconMap.perplexity || <PerplexityIcon />;
  }

  // Check for GCP/Vertex/ADK patterns (Gemini models)
  if (
    lowerModel.includes('gcp') ||
    lowerModel.includes('google') ||
    lowerModel.includes('gemini') ||
    lowerModel.includes('vertex') ||
    lowerModel.includes('adk')
  ) {
    return iconMap.gemini || <GeminiIcon />;
  }

  // String includes matching for other models
  const match = Object.keys(iconMap).find((key) => lowerModel.includes(key));
  return match ? iconMap[match as keyof typeof iconMap] : <Logo />;
};
