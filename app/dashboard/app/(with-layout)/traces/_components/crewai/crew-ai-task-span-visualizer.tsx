import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Container } from '@/components/ui/container';
import CollapsibleSection, { OutputViewer } from './collapsible-section';

interface CrewAITaskVisualizerProps {
  spanAttributes: any;
}

const CrewAITaskVisualizer = ({ spanAttributes }: CrewAITaskVisualizerProps) => {
  const crewaiData = spanAttributes?.crewai;
  if (!crewaiData || !crewaiData.task) {
    return (
      <div className="max-w-2xl p-4">
        <p className="text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
          No CrewAI task data available.
        </p>
      </div>
    );
  }
  const taskData = crewaiData.task;
  const outputData = spanAttributes.agentops?.entity?.output;

  return (
    <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent">
      <Card className="rounded-xl border-white bg-transparent px-3 shadow-xl transition-all duration-300">
        <CardHeader>
          {/* Agent and ID Badge */}
          {taskData.agent && (
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-800 dark:bg-slate-700/80 dark:text-blue-400">
                  Agent: {taskData.agent}
                </span>
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent className="space-y-3">
          {/* Description */}
          {taskData.name && (
            <CollapsibleSection title="Task Name" defaultExpanded={true}>
              <OutputViewer outputData={taskData.name} />
            </CollapsibleSection>
          )}

          {/* Expected Output */}
          {taskData.expected_output && (
            <CollapsibleSection title="Expected Output" defaultExpanded={true}>
              <OutputViewer outputData={taskData.expected_output} />
            </CollapsibleSection>
          )}

          {/* Output */}
          {outputData && (
            <CollapsibleSection title="Output" defaultExpanded={true}>
              <OutputViewer outputData={outputData} />
            </CollapsibleSection>
          )}
        </CardContent>
      </Card>
    </Container>
  );
};

export default CrewAITaskVisualizer;
