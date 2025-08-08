import { ReactNode } from 'react';

export interface MenuItemsProps<T extends string = string> {
  icon: ReactNode;
  label: T;
  href?: string;
}

export type TooltipType = 'line' | 'dot' | 'dashed';
