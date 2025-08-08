import { useMemo } from 'react';
import { ISpan } from '@/types/ISpan';
import CrewAITaskVisualizer from './crewai/crew-ai-task-span-visualizer';

interface TasksViewerProps {
  spans: ISpan[];
}

interface TaskInfo {
  id: string;
  spanAttributes: any;
}

export const TasksViewer = ({ spans }: TasksViewerProps) => {
  // Extract task data from spans
  const taskData = useMemo(() => {
    const tasks: TaskInfo[] = [];

    spans.forEach((span) => {
      // Check if the span has CrewAI task data
      if (span.span_attributes?.crewai?.task) {
        tasks.push({
          id: span.span_id,
          spanAttributes: span.span_attributes,
        });
      }
    });

    return tasks;
  }, [spans]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6">
        {taskData.length === 0 ? (
          <div className="p-4 text-center">No task data found</div>
        ) : (
          <div className="space-y-6">
            {taskData.map((task) => (
              <CrewAITaskVisualizer key={task.id} spanAttributes={task.spanAttributes} />
            ))}
          </div>
        )}
        <div className="h-10"></div>
      </div>
    </div>
  );
};
