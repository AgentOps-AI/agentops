import { cn } from '@/lib/utils';
import { CSSProperties, ReactNode, useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './tabs';

interface CustomTabsProps {
  tabs: {
    value: string;
    label: string;
    labelClassName?: string;
    content: ReactNode;
    contentClassName?: string;
    contentStyles?: CSSProperties;
    'data-testid'?: string;
  }[];
  onTabClick?: (value: string) => void;
  generalTabsContainerClassNames?: string;
  defaultValue: string;
  activeTabId?: string;
}

export default function CustomTabs({
  tabs,
  defaultValue,
  activeTabId,
  generalTabsContainerClassNames,
  onTabClick,
}: CustomTabsProps) {
  const [activeTab, setActiveTab] = useState(activeTabId);

  useEffect(() => {
    setActiveTab(activeTabId);
  }, [activeTabId]);

  return (
    <Tabs
      defaultValue={defaultValue}
      value={activeTab ?? defaultValue}
      onValueChange={setActiveTab}
      className="flex h-full flex-col"
    >
      <TabsList className="dark:bg-slate-850 h-10 w-full justify-start rounded-none border-b border-[#DEE0F4] bg-transparent">
        {tabs.map((tab) => (
          <TabsTrigger
            key={tab.value}
            value={tab.value}
            onClick={() => onTabClick?.(tab.value)}
            className={cn(
              'ml-3 mr-3 h-10 min-w-[80px] max-w-[25%] flex-1 rounded-none data-[state=active]:border-b-4 data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none data-[state=active]:drop-shadow-xl dark:data-[state=active]:bg-transparent',
              tab.labelClassName,
            )}
            data-testid={tab['data-testid']}
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>

      {tabs.map((tab) => (
        <TabsContent
          key={tab.value}
          value={tab.value}
          className={cn(tab.contentClassName, generalTabsContainerClassNames)}
          style={tab.contentStyles}
        >
          {tab.content}
        </TabsContent>
      ))}
    </Tabs>
  );
}
