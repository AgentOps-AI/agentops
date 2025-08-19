'use client';
import { cn } from '@/lib/utils';
import {
  InformationCircleIcon as Info,
  Triangle01Icon as TriangleAlert,
  OctagonIcon as OctagonAlert,
} from 'hugeicons-react';
import React, { useEffect, useState } from 'react';
import { Cancel01Icon as CloseIcon } from 'hugeicons-react';

type BannerTypes = 'info' | 'warning' | 'error';
interface BannerProps {
  message: string | React.ReactNode;
  visible: boolean;
  type?: BannerTypes;
  onClick?: () => void;
  onClosed?: () => void;
}

export const Banner: React.FC<BannerProps> = ({
  message,
  visible,
  type = 'info',
  onClick,
  onClosed,
}) => {
  const [isVisible, setIsVisible] = useState(visible);

  const handleClose = () => {
    setIsVisible(false);
    onClosed?.();
  };

  const getBackgroundColor = (type: string) => {
    switch (type) {
      case 'info':
        return 'bg-[#F4F5FF]';
      case 'warning':
        return 'bg-amber-400';
      case 'error':
        return 'bg-red-600';
    }
  };

  const getIcon = (type: BannerTypes) => {
    const iconMap = {
      info: Info,
      warning: TriangleAlert,
      error: OctagonAlert,
    };
    const IconComponent = iconMap[type];
    return <IconComponent />;
  };

  useEffect(() => {
    setIsVisible(visible);
  }, [visible]);

  return (
    <div
      className={cn(
        'duration-400 fixed left-0 right-0 top-0 z-50 flex transform items-center justify-between p-4 shadow-md transition-all ease-in-out',
        isVisible ? 'opacity-1 max-h-20' : 'pointer-events-none max-h-0 opacity-0',
        getBackgroundColor(type),
      )}
    >
      <div
        className={cn(
          'flex items-center gap-2',
          type === 'error' && 'text-white',
          onClick && 'cursor-pointer hover:underline',
        )}
        onClick={onClick}
      >
        {getIcon(type)}
        {message}
      </div>
      <button onClick={handleClose} aria-label="Close notification" className="relative">
        <CloseIcon className="h-5 w-5" />
      </button>
    </div>
  );
};
