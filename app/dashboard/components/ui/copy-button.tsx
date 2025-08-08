import { cn } from '@/lib/utils';
import { ReactNode } from 'react';
import { Copy01Icon as CopyIcon } from 'hugeicons-react';
import { Button, ButtonProps } from './button';
import { CommonTooltip } from './common-tooltip';

interface CopyButtonProps extends ButtonProps {
  iconClassName?: string;
  children?: ReactNode;
  className?: string;
  noAnimation?: boolean;
  withTooltip?: string;
  iconSize?: number;
  iconStrokeWidth?: number;
  iconStrokeOpacity?: string | number;
}

export const CopyButton = ({
  className,
  iconClassName,
  children,
  noAnimation,
  withTooltip,
  iconSize,
  iconStrokeWidth,
  iconStrokeOpacity,
  ...props
}: CopyButtonProps) => {
  const buttonContent = (
    <Button
      variant="ghost"
      size="sm"
      {...props}
      className={cn(
        'group cursor-pointer px-0 hover:bg-[bg-[#F5F6FD]/40] dark:hover:bg-[bg-[#E1E3F21A]]',
        className,
      )}
    >
      {children}
      <CopyIcon
        size={iconSize}
        strokeWidth={iconStrokeWidth}
        strokeOpacity={iconStrokeOpacity}
        className={cn(
          'cursor-pointer',
          iconClassName,
          !noAnimation && 'duration-300 ease-in-out group-hover:scale-125 group-active:mt-1.5',
        )}
      />
    </Button>
  );

  return withTooltip ? (
    <CommonTooltip
      content={withTooltip}
      toolTipContentProps={{
        sideOffset: 8,
      }}
    >
      {buttonContent}
    </CommonTooltip>
  ) : (
    buttonContent
  );
};
