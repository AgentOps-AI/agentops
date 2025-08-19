import { cn } from '@/lib/utils';
import { ArrowLeft01Icon as ArrowLeft } from 'hugeicons-react';

interface StepperProps {
  steps: string[];
  currentStep: number;
  onBackClicked: () => void;
}

export function Stepper({ steps, currentStep, onBackClicked }: StepperProps) {
  return (
    <div className="mb-8 flex items-center gap-4">
      {currentStep > 0 && (
        <button
          onClick={onBackClicked}
          className="rounded-full p-2 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
      )}
      <div className="flex-1">
        <div className="flex justify-between">
          {steps.map((step, index) => (
            <div
              key={step}
              className={cn('flex items-center', index !== steps.length - 1 && 'flex-1')}
            >
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium',
                  index <= currentStep
                    ? 'bg-black text-white dark:bg-white dark:text-black'
                    : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
                )}
              >
                {index + 1}
              </div>
              {index !== steps.length - 1 && (
                <div
                  className={cn(
                    'mx-2 h-0.5 flex-1',
                    index < currentStep ? 'bg-black dark:bg-white' : 'bg-gray-100 dark:bg-gray-800',
                  )}
                />
              )}
            </div>
          ))}
        </div>
        <div className="mt-2 flex justify-between">
          {steps.map((step, index) => (
            <div
              key={step}
              className={cn(
                'text-sm font-medium',
                index <= currentStep
                  ? 'text-black dark:text-white'
                  : 'text-gray-500 dark:text-gray-400',
              )}
            >
              {step}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
