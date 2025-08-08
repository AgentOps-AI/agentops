'use client';
import React, { useState, useEffect } from 'react';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

type Direction = 'TOP' | 'LEFT' | 'BOTTOM' | 'RIGHT';

export const HoverBorderGradient = React.forwardRef<
  HTMLElement,
  React.PropsWithChildren<
    {
      as?: 'button' | 'div' | 'span';
      containerClassName?: string;
      className?: string;
      duration?: number;
      clockwise?: boolean;
    } & React.HTMLAttributes<HTMLElement>
  >
>(function HoverBorderGradient(
  {
    children,
    containerClassName,
    className,
    as: Tag = 'button',
    duration = 1,
    clockwise = true,
    ...props
  },
  ref,
) {
  const [hovered, setHovered] = useState<boolean>(false);
  const [direction, setDirection] = useState<Direction>('TOP');

  const rotateDirection = (currentDirection: Direction): Direction => {
    const directions: Direction[] = ['TOP', 'LEFT', 'BOTTOM', 'RIGHT'];
    const currentIndex = directions.indexOf(currentDirection);
    const nextIndex = clockwise
      ? (currentIndex - 1 + directions.length) % directions.length
      : (currentIndex + 1) % directions.length;
    return directions[nextIndex];
  };

  const movingMap: Record<Direction, string> = {
    TOP: 'radial-gradient(20.7% 50% at 50% 0%, #3275F8 0%, rgba(255, 255, 255, 0) 100%)',
    LEFT: 'radial-gradient(16.6% 43.1% at 0% 50%, #3275F8 0%, rgba(255, 255, 255, 0) 100%)',
    BOTTOM: 'radial-gradient(20.7% 50% at 50% 100%, #3275F8 0%, rgba(0, 0, 139, 0) 100%)',
    RIGHT:
      'radial-gradient(16.2% 41.199999999999996% at 100% 50%, #3275F8 0%, rgba(255, 255, 255, 0) 100%)',
  };

  const highlight =
    'radial-gradient(75% 181.15942028985506% at 50% 50%, #3275F8 0%, rgba(255, 255, 255, 0) 100%)';

  useEffect(() => {
    if (!hovered) {
      const interval = setInterval(() => {
        setDirection((prevState) => rotateDirection(prevState));
      }, duration * 1000);
      return () => clearInterval(interval);
    }
  }, [hovered]);
  return React.createElement(
    Tag,
    {
      ref,
      onMouseEnter: () => setHovered(true),
      onMouseLeave: () => setHovered(false),
      className: cn(
        'relative flex h-min w-fit  flex-col flex-nowrap content-center items-center justify-center gap-10 overflow-visible rounded-full border bg-black/20 decoration-clone p-px transition duration-500 hover:bg-black/10 dark:bg-white/20',
        containerClassName,
      ),
      ...props,
    },
    [
      <div
        key="content"
        className={cn('z-10 w-auto rounded-[inherit] bg-black px-4 py-2 text-white', className)}
      >
        {children}
      </div>,
      <motion.div
        key="gradient"
        className={cn('absolute inset-0 z-0 flex-none overflow-hidden rounded-[inherit]')}
        style={{
          filter: 'blur(2px)',
          position: 'absolute',
          width: '100%',
          height: '100%',
        }}
        initial={{ background: movingMap[direction] }}
        animate={{
          background: hovered ? [movingMap[direction], highlight] : movingMap[direction],
        }}
        transition={{ ease: 'linear', duration: duration ?? 1 }}
      />,
      <div
        key="background"
        className="z-1 absolute inset-[2px] flex-none rounded-[100px] bg-black"
      />,
    ],
  );
});
