import { TooltipContentProps, TooltipProviderProps } from '@radix-ui/react-tooltip';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './tooltip';

type CommonTooltipProps = {
  content: string;
  children: React.ReactNode;
  toolTipProviderProps?: TooltipProviderProps;
  toolTipContentProps?: TooltipContentProps;
};

export const CommonTooltip: React.FC<CommonTooltipProps> = ({
  content,
  children,
  toolTipContentProps,
  toolTipProviderProps,
}) => {
  return (
    <TooltipProvider delayDuration={200} {...toolTipProviderProps}>
      <Tooltip>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent {...toolTipContentProps}>
          <p>{content}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
