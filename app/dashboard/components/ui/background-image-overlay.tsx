import { CSSProperties } from 'react';

interface BackgroundImageOverlayProps {
  opacity?: number;
  backgroundImageUrl?: string;
  additionalStyles?: CSSProperties;
}

export const BackgroundImageOverlay = ({
  opacity = 0.15,
  backgroundImageUrl = 'url(/image/grainy.png)',
  additionalStyles = {},
}: BackgroundImageOverlayProps) => {
  return (
    <div
      className="absolute inset-0 dark:hidden"
      style={{
        backgroundImage: backgroundImageUrl,
        opacity,
        ...additionalStyles,
      }}
    />
  );
};
