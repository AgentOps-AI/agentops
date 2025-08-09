import { HelpCircle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { formatTokens } from '@/lib/number_formatting_utils';

interface FormattedTokenDisplayProps {
  value: number | string | undefined;
  className?: string;
}

export function FormattedTokenDisplay({ value, className = '' }: FormattedTokenDisplayProps) {
  const formatted = formatTokens(typeof value === 'string' ? parseFloat(value) : value);

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      <span>{formatted.display}</span>
      {formatted.display !== formatted.full && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <HelpCircle className="h-4 w-4 cursor-help text-muted-foreground" />
            </TooltipTrigger>
            <TooltipContent>
              <p>Full value: {formatted.full}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}
