// Define type for span color definitions
export type SpanColorDefinition = {
  bg: string;
  border: string;
  text: string;
  selectedBorder: string;
};

export type SpanTypeColorMap = {
  [key: string]: SpanColorDefinition;
  session: SpanColorDefinition;
  agent: SpanColorDefinition;
  operation: SpanColorDefinition;
  task: SpanColorDefinition;
  workflow: SpanColorDefinition;
  llm: SpanColorDefinition;
  tool: SpanColorDefinition;
  tool_usage: SpanColorDefinition;
  error: SpanColorDefinition;
  other: SpanColorDefinition;
  default: SpanColorDefinition;
};

// Shared color definitions for span types used across the application
export const spanTypeColors: SpanTypeColorMap = {
  session: {
    bg: 'rgba(20, 27, 52, 0.4)',
    border: 'rgba(222, 224, 244, 1)',
    text: 'text-slate-800', // Dark blue/slate for session
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  agent: {
    bg: 'rgba(36, 0, 255, 0.6)',
    border: 'rgba(222, 224, 244, 0.1)',
    text: 'text-blue-600', // Deeper blue for agent
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  operation: {
    bg: 'rgba(75, 196, 152, 1)',
    border: 'rgba(75, 196, 152, 1)',
    text: 'text-emerald-500', // Green for operation
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  task: {
    bg: 'rgba(75, 196, 152, 1)',
    border: 'rgba(75, 196, 152, 1)',
    text: 'text-emerald-500', // Green for task
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  workflow: {
    bg: 'rgba(222, 224, 244, 0.7)',
    border: 'rgba(222, 224, 244, 1)',
    text: 'text-slate-400', // Light slate for workflow
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  llm: {
    bg: 'rgba(1, 178, 255, 1)',
    border: 'rgba(01, 178, 255, 0.7)',
    text: 'text-sky-500', // Bright blue for LLM
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  tool: {
    bg: 'rgba(237, 216, 103, 0.9)',
    border: 'rgba(237, 216, 103, 1)',
    text: 'text-yellow-500', // Yellow for tool usage
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  tool_usage: {
    bg: 'rgba(237, 216, 103, 0.9)',
    border: 'rgba(237, 216, 103, 1)',
    text: 'text-yellow-500', // Yellow for tool usage
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  error: {
    bg: 'rgba(230, 90, 126, 1)',
    border: 'rgba(230, 90, 126, 0.7)',
    text: 'text-red-500', // Red for error
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  other: {
    bg: 'rgba(20, 27, 52, 0.5)',
    border: 'rgba(20, 27, 52, 0.7)',
    text: 'text-slate-600', // Darker slate for other
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
  default: {
    bg: '#94A3B8',
    border: '#94A3B8',
    text: 'text-slate-400', // Light slate for default
    selectedBorder: 'rgba(225, 227, 242, 1)',
  },
};
