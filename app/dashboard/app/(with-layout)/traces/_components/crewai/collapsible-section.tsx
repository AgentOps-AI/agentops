import { ChevronDown, ChevronRight } from 'lucide-react';
import { ReactNode, useState } from 'react';

interface CollapsibleSectionProps {
  title: string;
  defaultExpanded?: boolean;
  icon?: ReactNode;
  children: ReactNode;
}

export const OutputViewer = ({ outputData }: { outputData: string }) => {
  return (
    <p className="mb-3 whitespace-pre-wrap rounded border border-gray-200 p-3 text-sm shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
      {outputData}
    </p>
  );
};

export const CollapsibleSection = ({
  title,
  defaultExpanded = true,
  icon,
  children,
}: CollapsibleSectionProps) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div>
      <h4
        className="mb-1 flex cursor-pointer items-center font-bold"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? (
          <ChevronDown size={16} className="mr-1" />
        ) : (
          <ChevronRight size={16} className="mr-1" />
        )}
        {icon && <span className="mr-1">{icon}</span>}
        {title}
      </h4>
      {isExpanded && children}
    </div>
  );
};

export default CollapsibleSection;
