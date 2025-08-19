import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

interface InstrumentationWarningProps {
  className?: string;
}

export const InstrumentationWarning = ({ className }: InstrumentationWarningProps) => {
  return (
    <Alert className={`border-yellow-200 bg-yellow-50 mx-4 mb-4 ${className} dark:border-yellow-800 dark:bg-yellow-900/20`}>
      <div className="flex items-start gap-3">
        <div className="text-yellow-600 dark:text-yellow-400 font-bold text-lg">⚠️</div>
        <AlertDescription className="text-yellow-800 dark:text-yellow-200">
          <div className="flex flex-col gap-3">
            <div>
              <p className="font-medium">It looks like AgentOps may not be fully instrumented</p>
              <p className="text-sm mt-1">
                You&apos;re only seeing a single session span, which typically means AgentOps isn&apos;t properly tracking your LLM calls, tools, and agents.
                This limits visibility into your application&apos;s behavior.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <Button
                variant="outline"
                size="sm"
                className="text-yellow-800 border-yellow-300 bg-yellow-100 hover:bg-yellow-200 dark:text-yellow-200 dark:border-yellow-600 dark:bg-yellow-900/40 dark:hover:bg-yellow-900/60"
                asChild
              >
                <a
                  href="https://docs.agentops.ai/v2/usage/sdk-reference"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1"
                >
                  SDK Setup Guide
                  <span className="text-xs">↗</span>
                </a>
              </Button>
            </div>
          </div>
        </AlertDescription>
      </div>
    </Alert>
  );
};