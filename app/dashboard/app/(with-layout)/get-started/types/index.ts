export interface Tool {
  name: string;
  icon: React.ReactNode;
}

export interface Framework {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  benefit?: string;
  installCommand: string;
}

export interface LLMProvider {
  id: string;
  name: string;
  installCommand: string;
  icon: React.ReactNode;
  gradient?: string;
  description?: string;
}

export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  tools: Tool[];
  icon: React.ReactNode;
  benefit?: string;
}

export interface StepProps {
  label: string;
  isActive: boolean;
  isComplete: boolean;
  onClick?: () => void;
}

export type FrameworkType = 'framework' | 'llm';
export type PackageManager = 'uv' | 'pip';
export type OsType = 'unix' | 'windows';
