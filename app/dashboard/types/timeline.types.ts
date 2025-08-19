export type ActivityType = 'LLM' | 'Action' | 'Tool' | 'Error';

export interface TimelineActivity {
  start: number; // Start time in seconds
  end: number; // End time in seconds
  type: ActivityType; // Type of activity
  label?: string; // Optional label to show on activity
  details?: string; // Optional additional details for tooltip
  id?: string; // ID of the activity (agent_id)
  rawData?: any; // Original raw data object
}

export interface TimelineLane {
  id: string; // Unique identifier for the lane
  name: string; // Display name of the lane
  color?: string; // Optional background color for the lane
  activities: TimelineActivity[]; // Activities in this lane
}

export interface TimelineData {
  lanes: TimelineLane[];
  maxTime?: number; // Optional maximum time in seconds for the chart
}

// New types for the provided data format
export interface AgentActivityData {
  agent_id: string;
  type: string;
  Agent: string;
  Start: number;
  End: number;
  Duration: number;
  Name?: string;
  Model?: string;
  Cost?: string;
  'Prompt Tokens'?: number;
  'Completion Tokens'?: number;
  'Promptarmor Flag'?: string | null;
  Thread?: string | null;
  Prompt?: any;
  Completion?: any;
  Params?: any;
  Returns?: any;
}

export interface AgentData {
  id: string;
  data: AgentActivityData[];
}

export type AgentsTimelineData = AgentData[];
