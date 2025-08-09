interface ToolItemProps {
  tool: any;
}

const SubItem = ({ label, value }: { label: string; value: any }) => {
  const displayValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : value;

  return (
    <div className="whitespace-pre-wrap p-2 text-sm text-[rgba(20,27,52,1)] dark:bg-slate-800 dark:text-[rgba(225,226,242,1)]">
      <span className="font-bold">{label}: </span>
      <span>{displayValue}</span>
    </div>
  );
};
export const ToolItem = ({ tool }: ToolItemProps) => {
  // Check if tool is already a simple object with name/description
  if (tool.name || tool.description) {
    return (
      <div className="mb-3 whitespace-pre-wrap rounded border border-gray-200 p-2 text-sm shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
        <SubItem label="Name" value={tool.name || 'Unnamed Tool'} />
        {tool.description && <SubItem label="Description" value={tool.description} />}
      </div>
    );
  }

  // Handle nested tool structure
  const toolKey = Object.keys(tool)[0];
  const toolObj = tool[toolKey];

  // If toolObj is a string, use it as the name
  if (typeof toolObj === 'string') {
    // If the key is 'description', use the value as the name
    const displayName = toolKey === 'description' ? toolObj : toolKey;
    return (
      <div className="mb-3 whitespace-pre-wrap rounded border border-gray-200 p-2 text-sm shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
        <SubItem label="Name" value={displayName} />
        {toolKey === 'description' && <SubItem label="Description" value={toolObj} />}
      </div>
    );
  }

  return (
    <div className="mb-3 whitespace-pre-wrap rounded border border-gray-200 p-2 text-sm shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
      <SubItem label="Name" value={toolObj?.name || toolKey || 'Unnamed Tool'} />
      {toolObj?.description && <SubItem label="Description" value={toolObj.description} />}
    </div>
  );
};

interface ToolsContainerProps {
  tools: any[];
  defaultExpanded?: boolean;
}

export const ToolsContainer = ({ tools, defaultExpanded = true }: ToolsContainerProps) => {
  // Ensure tools is an array
  if (!tools || !Array.isArray(tools) || tools.length === 0) {
    return null;
  }

  return tools.map((tool: any, index: number) => <ToolItem key={index} tool={tool} />);
};

export default ToolsContainer;
