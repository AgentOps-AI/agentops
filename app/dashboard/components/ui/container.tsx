import * as React from 'react';
import { cn } from '@/lib/utils';

interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  backgroundImageUrl?: string;
  backgroundOpacity?: number;
  styleProps?: React.CSSProperties;
  imageProps?: string;
  containerClasses?: string;
}

export const Container = React.forwardRef<HTMLDivElement, React.PropsWithChildren<ContainerProps>>(
  (
    {
      className,
      children,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      imageProps,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      backgroundImageUrl = 'url(image/grainy.png)',
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      backgroundOpacity = 0.15,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      styleProps = {},
      containerClasses,
      ...props
    },
    ref,
  ) => (
    <div ref={ref} className={cn('relative', className)} {...props}>
      {/* <div
        style={{
          backgroundImage: backgroundImageUrl,
          opacity: backgroundOpacity,
          ...styleProps,
        }}
        className={cn(
          'absolute bottom-0 left-0 right-0 top-0 z-0 rounded-3xl dark:hidden',
          imageProps,
        )}
      /> */}
      <div className={cn('relative h-full', containerClasses)}>{children}</div>
    </div>
  ),
);

Container.displayName = 'Container';
