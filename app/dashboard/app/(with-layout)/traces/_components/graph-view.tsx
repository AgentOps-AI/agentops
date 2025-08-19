'use client';

import React, { useMemo, useCallback, useState } from 'react';
import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    MiniMap,
    useNodesState,
    useEdgesState,
    Position,
    MarkerType,
    NodeTypes,
    Handle,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ISpan } from '@/types/ISpan';
import { spanTypeColors } from '@/app/lib/span-colors';
import { getSpanDisplayInfo } from '@/utils/span-display.utils';
import { cn } from '@/lib/utils';
import { getIconForModel } from '@/lib/modelUtils';
import { determineSpanType } from '@/components/charts/bar-chart/span-processing';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import CustomTabs from '@/components/ui/custom-tabs';
import { SpanPretty } from './span-pretty';
import { LlmSpanRaw } from './llm-span-raw';
import { isEmpty } from 'lodash';
import CrewAITaskVisualizer from './crewai/crew-ai-task-span-visualizer';
import CrewAIAgentSpanVisualizer from './crewai/crew-ai-agent-span-visualizer';
import ADKAgentSpanVisualizer from './agents/adk-agent-span-visualizer';
import ADKWorkflowSpanVisualizer from './agents/adk-workflow-span-visualizer';
import CrewAIWorkflowSpanVisualizer from './crewai/crew-ai-workflow-span-visualizer';
import AgnoAgentSpanVisualizer from './agents/agno-agent-span-visualizer';
import AgnoWorkflowSpanVisualizer from './agents/agno-workflow-span-visualizer';
import AG2AgentSpanVisualizer from './agents/ag2-agent-span-visualizer';
import { UnifiedToolSpanViewer } from './event-visualizers/tool-span';

interface GraphViewProps {
    spans: ISpan[];
    selectedSpan: ISpan | null;
    setSelectedSpan: (span: ISpan | null) => void;
    traceStartTimeMs: number;
    renderMetadata: () => React.ReactNode;
    processedCompletions: any[];
    isLlmSpan: boolean;
    prompts: any;
}

interface SpanNode {
    span: ISpan;
    children: SpanNode[];
    level: number;
    isLeaf: boolean;
    siblings: SpanNode[];
}

// Custom node component for span visualization
const SpanNodeComponent = ({ data, selected }: { data: any; selected: boolean }) => {
    const { span, isGroupNode, leafSpans = [], onSpanClick, groupTitle } = data;

    // Add custom scrollbar styles
    React.useEffect(() => {
        const style = document.createElement('style');
        style.textContent = `
            .graph-view-scroll::-webkit-scrollbar {
                width: 6px;
            }
            .graph-view-scroll::-webkit-scrollbar-track {
                background: rgba(229, 231, 235, 0.5);
                border-radius: 3px;
            }
            .graph-view-scroll::-webkit-scrollbar-thumb {
                background: #9CA3AF;
                border-radius: 3px;
            }
            .graph-view-scroll::-webkit-scrollbar-thumb:hover {
                background: #6B7280;
            }
            .dark .graph-view-scroll::-webkit-scrollbar-track {
                background: rgba(31, 41, 55, 0.5);
            }
            .dark .graph-view-scroll::-webkit-scrollbar-thumb {
                background: #4B5563;
            }
            .dark .graph-view-scroll::-webkit-scrollbar-thumb:hover {
                background: #6B7280;
            }
        `;
        document.head.appendChild(style);
        return () => {
            document.head.removeChild(style);
        };
    }, []);

    if (isGroupNode) {
        // This is a container node for grouped operations
        return (
            <div
                className={cn(
                    'rounded-lg border-dashed p-4 transition-all min-w-[300px] max-w-[500px] relative',
                    'bg-gray-50/50 dark:bg-gray-800/20'
                )}
                style={{
                    border: '2px dashed #9CA3AF',
                    boxShadow: selected ? '0 0 0 3px #E1E3F2' : undefined,
                    filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.2))',
                }}
            >
                <Handle type="target" position={Position.Top} className="invisible" />
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
                    {groupTitle || 'Operations'} ({leafSpans.length})
                </div>
                <div
                    className="graph-view-scroll space-y-2 max-h-[500px] overflow-y-auto pr-2 pb-4"
                    style={{
                        scrollbarWidth: 'thin',
                        scrollbarColor: '#9CA3AF #E5E7EB',
                    }}
                >
                    {leafSpans.map((leafSpan: ISpan) => {
                        const { displayName, shortType } = getSpanDisplayInfo(leafSpan);
                        const { visualType } = determineSpanType(leafSpan);
                        const hasError = leafSpan.status_code === 'ERROR';
                        const typeColors = hasError
                            ? spanTypeColors.error
                            : spanTypeColors[visualType as keyof typeof spanTypeColors] || spanTypeColors.default;
                        const isSelected = selected && data.selectedSpanId === leafSpan.span_id;

                        return (
                            <div
                                key={leafSpan.span_id}
                                className={cn(
                                    'p-2 rounded cursor-pointer transition-all',
                                    'hover:shadow-md'
                                )}
                                style={{
                                    backgroundColor: typeColors.bg,
                                    border: `1px solid ${typeColors.border}`,
                                    boxShadow: isSelected ? `0 0 0 2px ${typeColors.selectedBorder}` : undefined,
                                    filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.2))',
                                }}
                                onClick={() => onSpanClick(leafSpan)}
                            >
                                <div className="flex items-center justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span
                                                className="text-xs font-medium px-2 py-0.5 rounded text-white inline-block min-w-[3rem] text-center"
                                                style={{
                                                    backgroundColor: typeColors.bg,
                                                    border: `1px solid ${typeColors.border}`,
                                                    filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.3))',
                                                }}
                                            >
                                                {shortType.toUpperCase()}
                                            </span>
                                            <div className="text-xs font-medium truncate text-gray-800 dark:text-gray-200" title={displayName}>
                                                {displayName}
                                            </div>
                                        </div>

                                    </div>
                                    {hasError && (
                                        <div className="flex-shrink-0 text-red-500">
                                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                            </svg>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
                {leafSpans.length > 5 && (
                    <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-gray-50/90 dark:from-gray-800/50 via-gray-50/50 dark:via-gray-800/20 to-transparent pointer-events-none rounded-b-lg" />
                )}
                <Handle type="source" position={Position.Bottom} className="invisible" />
            </div>
        );
    }

    const { displayName, shortType } = getSpanDisplayInfo(span);
    const { visualType } = determineSpanType(span);
    const hasError = span.status_code === 'ERROR';

    // Get colors from the shared color map
    const typeColors = hasError
        ? spanTypeColors.error
        : spanTypeColors[visualType as keyof typeof spanTypeColors] || spanTypeColors.default;

    // Get model icon for LLM spans
    const modelName = visualType === 'llm'
        ? span.span_attributes?.gen_ai?.response?.model ||
        span.span_attributes?.gen_ai?.request?.model ||
        span.span_attributes?.gen_ai?.system ||
        null
        : null;

    const modelIcon = modelName ? getIconForModel(modelName) : null;

    return (
        <div
            className={cn(
                'rounded-lg p-3 transition-all cursor-pointer min-w-[200px]',
                'hover:shadow-lg'
            )}
            style={{
                backgroundColor: typeColors.bg,
                border: `2px solid ${typeColors.border}`,
                boxShadow: selected ? `0 0 0 3px ${typeColors.selectedBorder}` : undefined,
                filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.3))',
            }}
        >
            <Handle
                type="target"
                position={Position.Top}
                className="invisible"
            />

            <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        {modelIcon && (
                            <div className="flex-shrink-0 w-4 h-4">
                                {modelIcon}
                            </div>
                        )}
                        <span
                            className="text-xs font-medium px-2 py-0.5 rounded text-white inline-block min-w-[3rem] text-center"
                            style={{
                                backgroundColor: typeColors.bg,
                                border: `1px solid ${typeColors.border}`,
                                filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.3))',
                            }}
                        >
                            {shortType.toUpperCase()}
                        </span>
                    </div>

                    <div className="mt-1 font-medium text-sm truncate text-gray-800 dark:text-gray-200" title={displayName}>
                        {displayName}
                    </div>
                </div>

                {hasError && (
                    <div className="flex-shrink-0 text-red-500">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                    </div>
                )}
            </div>

            <Handle
                type="source"
                position={Position.Bottom}
                className="invisible"
            />
        </div>
    );
};

const nodeTypes: NodeTypes = {
    spanNode: SpanNodeComponent,
};

// Build hierarchical tree structure from spans
const buildSpanTree = (spans: ISpan[]): SpanNode[] => {
    const spanMap = new Map<string, SpanNode>();
    const rootNodes: SpanNode[] = [];

    // First pass: create all nodes
    spans.forEach(span => {
        spanMap.set(span.span_id, {
            span,
            children: [],
            level: 0,
            isLeaf: true,
            siblings: [],
        });
    });

    // Second pass: build hierarchy
    spans.forEach(span => {
        const node = spanMap.get(span.span_id)!;

        if (span.parent_span_id && spanMap.has(span.parent_span_id)) {
            const parent = spanMap.get(span.parent_span_id)!;
            parent.children.push(node);
            parent.isLeaf = false;
            node.level = parent.level + 1;
        } else {
            rootNodes.push(node);
        }
    });

    // Third pass: identify siblings (children of the same parent)
    spanMap.forEach(node => {
        if (node.children.length > 0) {
            node.children.forEach(child => {
                child.siblings = node.children.filter(c => c !== child);
            });
        }
    });

    // Sort by start time
    const sortByStartTime = (nodes: SpanNode[]) => {
        nodes.sort((a, b) =>
            new Date(a.span.start_time).getTime() - new Date(b.span.start_time).getTime()
        );
        nodes.forEach(node => sortByStartTime(node.children));
    };

    sortByStartTime(rootNodes);

    return rootNodes;
};

// Helper function to collect all descendants of a node
const collectAllDescendants = (node: SpanNode): ISpan[] => {
    const descendants: ISpan[] = [];

    const traverse = (currentNode: SpanNode) => {
        currentNode.children.forEach(child => {
            descendants.push(child.span);
            traverse(child);
        });
    };

    traverse(node);
    return descendants;
};

// Convert span tree to ReactFlow nodes and edges
const convertToFlowElements = (
    spanTree: SpanNode[],
    selectedSpanId: string | null,
    setSelectedSpan: (span: ISpan | null) => void
): { nodes: Node[]; edges: Edge[] } => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    let nodeId = 0;

    // Track positions by level
    const levelPositions = new Map<number, number>();
    const xSpacing = 450;
    const ySpacing = 150;

    const processNode = (
        spanNode: SpanNode,
        parentId?: string,
        xOffset: number = 0,
        skipDescendants: boolean = false
    ): string => {
        const currentNodeId = `node-${nodeId++}`;

        // Calculate position
        const level = spanNode.level;
        const levelX = levelPositions.get(level) || 0;

        // Check if this is an Agent node using the same logic as the gantt chart
        const { visualType } = determineSpanType(spanNode.span);
        const isAgentNode = visualType === 'agent';

        // Create node for this span
        nodes.push({
            id: currentNodeId,
            type: 'spanNode',
            position: {
                x: xOffset + levelX * xSpacing,
                y: level * ySpacing,
            },
            data: {
                span: spanNode.span,
                isGroupNode: false,
                leafSpans: [],
                onSpanClick: setSelectedSpan,
                selectedSpanId: selectedSpanId,
            },
            selected: spanNode.span.span_id === selectedSpanId,
        });

        // Update level position
        levelPositions.set(level, levelX + 1);

        // Create edge from parent
        if (parentId) {
            edges.push({
                id: `edge-${parentId}-${currentNodeId}`,
                source: parentId,
                target: currentNodeId,
                type: 'smoothstep',
                animated: false,
                style: {
                    stroke: '#9CA3AF',
                    strokeWidth: 2,
                },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 20,
                    height: 20,
                    color: '#9CA3AF',
                },
            });
        }

        // Process children
        if (spanNode.children.length > 0 && !skipDescendants) {
            // If this is an Agent node, group all descendants
            if (isAgentNode) {
                const allDescendants = collectAllDescendants(spanNode);

                if (allDescendants.length > 0) {
                    const groupNodeId = `group-${nodeId++}`;
                    const groupLevel = level + 1;
                    const groupLevelX = levelPositions.get(groupLevel) || 0;

                    // Sort descendants by start time
                    allDescendants.sort((a, b) =>
                        new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
                    );

                    // Create container node for all agent operations
                    nodes.push({
                        id: groupNodeId,
                        type: 'spanNode',
                        position: {
                            x: xOffset + groupLevelX * xSpacing,
                            y: groupLevel * ySpacing,
                        },
                        data: {
                            isGroupNode: true,
                            leafSpans: allDescendants,
                            onSpanClick: setSelectedSpan,
                            selectedSpanId: selectedSpanId,
                            groupTitle: 'Agent Operations',
                        },
                        selected: allDescendants.some(span => span.span_id === selectedSpanId),
                    });

                    // Connect agent to group node
                    edges.push({
                        id: `edge-${currentNodeId}-${groupNodeId}`,
                        source: currentNodeId,
                        target: groupNodeId,
                        type: 'smoothstep',
                        animated: false,
                        style: {
                            stroke: '#9CA3AF',
                            strokeWidth: 2,
                            strokeDasharray: '5,5',
                        },
                        markerEnd: {
                            type: MarkerType.ArrowClosed,
                            width: 20,
                            height: 20,
                            color: '#9CA3AF',
                        },
                    });

                    // Update level position
                    levelPositions.set(groupLevel, groupLevelX + 1);
                }
            } else {
                // For non-agent nodes, use the original logic
                // Separate leaf and non-leaf children
                const leafChildren = spanNode.children.filter(child => child.isLeaf);
                const nonLeafChildren = spanNode.children.filter(child => !child.isLeaf);

                // Process non-leaf children normally
                nonLeafChildren.forEach((child, index) => {
                    processNode(child, currentNodeId, xOffset + index * 100);
                });

                // Group leaf children in a single container node
                if (leafChildren.length > 0) {
                    const groupNodeId = `group-${nodeId++}`;
                    const groupLevel = level + 1;
                    const groupLevelX = levelPositions.get(groupLevel) || 0;

                    // Sort leaf children by start time
                    leafChildren.sort((a, b) =>
                        new Date(a.span.start_time).getTime() - new Date(b.span.start_time).getTime()
                    );

                    // Create container node for all leaf operations
                    nodes.push({
                        id: groupNodeId,
                        type: 'spanNode',
                        position: {
                            x: xOffset + groupLevelX * xSpacing,
                            y: groupLevel * ySpacing,
                        },
                        data: {
                            isGroupNode: true,
                            leafSpans: leafChildren.map(child => child.span),
                            onSpanClick: setSelectedSpan,
                            selectedSpanId: selectedSpanId,
                            groupTitle: 'Leaf Operations',
                        },
                        selected: leafChildren.some(child => child.span.span_id === selectedSpanId),
                    });

                    // Connect parent to group node
                    edges.push({
                        id: `edge-${currentNodeId}-${groupNodeId}`,
                        source: currentNodeId,
                        target: groupNodeId,
                        type: 'smoothstep',
                        animated: false,
                        style: {
                            stroke: '#9CA3AF',
                            strokeWidth: 2,
                            strokeDasharray: '5,5',
                        },
                        markerEnd: {
                            type: MarkerType.ArrowClosed,
                            width: 20,
                            height: 20,
                            color: '#9CA3AF',
                        },
                    });

                    // Update level position
                    levelPositions.set(groupLevel, groupLevelX + 1);
                }
            }
        }

        return currentNodeId;
    };

    // Process all root nodes
    spanTree.forEach((rootNode, index) => {
        processNode(rootNode, undefined, index * 700);
    });

    return { nodes, edges };
};

export const GraphView: React.FC<GraphViewProps> = ({
    spans,
    selectedSpan,
    setSelectedSpan,
    traceStartTimeMs,
    renderMetadata,
    processedCompletions,
    isLlmSpan,
    prompts,
}) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [initialFitView, setInitialFitView] = useState(true);

    // Build graph structure
    useMemo(() => {
        const spanTree = buildSpanTree(spans);
        const { nodes: flowNodes, edges: flowEdges } = convertToFlowElements(
            spanTree,
            selectedSpan?.span_id || null,
            setSelectedSpan
        );

        // Update nodes without changing positions to prevent repositioning
        setNodes((prevNodes) => {
            // If we have previous nodes, preserve their positions
            if (prevNodes.length > 0) {
                const positionMap = new Map(prevNodes.map(node => [node.id, node.position]));
                return flowNodes.map(node => ({
                    ...node,
                    position: positionMap.get(node.id) || node.position,
                    selected: node.data.span && node.data.span.span_id === selectedSpan?.span_id ||
                        node.data.isGroupNode && node.data.leafSpans.some((s: ISpan) => s.span_id === selectedSpan?.span_id)
                }));
            }
            return flowNodes;
        });

        setEdges(flowEdges);
    }, [spans, selectedSpan, setSelectedSpan]);

    // Handle node click
    const onNodeClick = useCallback(
        (event: React.MouseEvent, node: Node) => {
            if (!node.data.isGroupNode && node.data.span) {
                setSelectedSpan(node.data.span);
            }
            // For group nodes, clicks on individual leaf spans are handled by the onClick in the component
        },
        [setSelectedSpan]
    );

    // Check for special span types for tabs
    const isCrewAISpan = !!selectedSpan?.span_attributes?.crewai;
    const isADKAgentSpan = !!(
        selectedSpan?.span_attributes?.adk &&
        selectedSpan?.span_attributes?.agent &&
        selectedSpan?.span_type === 'agent'
    );
    const isADKWorkflowSpan = !!(
        selectedSpan?.span_attributes?.adk &&
        selectedSpan?.span_attributes?.agent &&
        selectedSpan?.span_attributes?.agent?.sub_agents &&
        selectedSpan?.span_attributes?.agent?.sub_agents.length > 0
    );
    const isAgnoAgentSpan = !!(
        selectedSpan?.span_attributes?.agent &&
        selectedSpan?.span_attributes?.gen_ai?.system === 'agno' &&
        selectedSpan?.span_type === 'agent'
    );
    const isAgnoWorkflowSpan = !!(
        selectedSpan?.span_attributes?.team &&
        selectedSpan?.span_attributes?.gen_ai?.system === 'agno' &&
        selectedSpan?.span_attributes?.agentops?.span?.kind === 'workflow'
    );
    const isAG2AgentSpan = !!(
        selectedSpan?.span_name?.startsWith('ag2.agent.') &&
        selectedSpan?.span_attributes?.agentops?.span?.kind === 'agent'
    );
    const isCrewAIWorkflowSpan = !!(
        selectedSpan?.span_attributes?.crewai &&
        (selectedSpan?.span_attributes?.crewai?.crew ||
            (selectedSpan?.span_attributes?.crewai?.agents && selectedSpan?.span_attributes?.crewai?.agents.length > 0))
    );
    const hasCompletionsToShow = processedCompletions.length > 0;
    const shouldShowCrewAITaskTab = isCrewAISpan && !!selectedSpan?.span_attributes?.crewai?.task && !isCrewAIWorkflowSpan;
    const shouldShowCrewAIAgentTab = isCrewAISpan && !!selectedSpan?.span_attributes?.crewai?.agent && !isCrewAIWorkflowSpan;
    const shouldShowADKAgentTab = isADKAgentSpan && !isADKWorkflowSpan;
    const shouldShowAgnoAgentTab = isAgnoAgentSpan;
    const shouldShowAG2AgentTab = isAG2AgentSpan;
    const shouldShowADKWorkflowTab = isADKWorkflowSpan;
    const shouldShowAgnoWorkflowTab = isAgnoWorkflowSpan;
    const shouldShowCrewAIWorkflowTab = isCrewAIWorkflowSpan;
    const shouldShowAgentView = shouldShowCrewAIAgentTab || shouldShowADKAgentTab || shouldShowAgnoAgentTab || shouldShowAG2AgentTab;
    const shouldShowWorkflowView = shouldShowADKWorkflowTab || shouldShowAgnoWorkflowTab || shouldShowCrewAIWorkflowTab;
    const shouldShowCrewAIToolTab = !!selectedSpan?.span_attributes?.tool;
    const isGenericToolSpan = !!(
        selectedSpan?.span_attributes?.agentops?.span?.kind === 'tool' ||
        (selectedSpan?.span_type === 'tool' && !isCrewAISpan) ||
        (selectedSpan?.span_name?.endsWith('.tool') &&
            selectedSpan?.span_attributes?.agentops?.entity?.input &&
            selectedSpan?.span_attributes?.operation?.name) ||
        selectedSpan?.span_name?.startsWith('ag2.tool.')
    );
    const shouldShowToolTab =
        (shouldShowCrewAIToolTab || (isGenericToolSpan && !shouldShowCrewAITaskTab)) &&
        !isADKAgentSpan &&
        !isADKWorkflowSpan &&
        !isAgnoAgentSpan &&
        !isAgnoWorkflowSpan;

    return (
        <ResizablePanelGroup direction="horizontal" className="flex h-full w-full gap-4">
            <ResizablePanel defaultSize={1} minSize={20} className="overflow-hidden">
                <div className="h-full w-full">
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onNodeClick={onNodeClick}
                        nodeTypes={nodeTypes}
                        fitView={initialFitView}
                        fitViewOptions={{
                            padding: 0.2,
                            includeHiddenNodes: false,
                        }}
                        onInit={() => setInitialFitView(false)}
                        minZoom={0.1}
                        maxZoom={1.5}
                        defaultViewport={{ x: 0, y: 0, zoom: 0.6 }}
                    >
                        <Background variant={"dots" as any} gap={12} size={1} />
                        <Controls />
                        <MiniMap
                            pannable
                            zoomable
                            className="!bg-gray-100 dark:!bg-gray-800"
                            nodeColor={(node) => {
                                if (node.data?.isGroupNode) return '#9CA3AF';
                                const span = node.data?.span;
                                if (!span) return '#E5E7EB';
                                const hasError = span.status_code === 'ERROR';
                                if (hasError) return '#EF4444';
                                const { visualType } = determineSpanType(span);
                                const colors = spanTypeColors[visualType as keyof typeof spanTypeColors] || spanTypeColors.default;
                                return colors.border;
                            }}
                        />
                    </ReactFlow>
                </div>
            </ResizablePanel>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={1} minSize={20} className="flex flex-col overflow-hidden">
                <div className="flex-1 overflow-y-auto">
                    {!selectedSpan ? (
                        <div
                            className="flex h-full items-center justify-center rounded-md border border-dashed text-gray-500 dark:border-slate-700"
                        >
                            Select a node in the graph to view details.
                        </div>
                    ) : (
                        <>
                            <div
                                className="flex h-full w-full flex-col gap-4 p-4"
                            >
                                <div className="w-full">
                                    {renderMetadata()}
                                </div>
                                <CustomTabs
                                    generalTabsContainerClassNames="h-full w-full"
                                    tabs={[
                                        ...((isLlmSpan && hasCompletionsToShow) || !isEmpty(prompts)
                                            ? [
                                                {
                                                    value: 'span-pretty',
                                                    label: 'Prettify',
                                                    content: (
                                                        <div className="w-full">
                                                            <SpanPretty selectedSpan={selectedSpan} />
                                                        </div>
                                                    ),
                                                },
                                            ]
                                            : []),
                                        ...(shouldShowCrewAITaskTab
                                            ? [
                                                {
                                                    value: 'crew-ai-task-visualizer',
                                                    label: 'Task View',
                                                    content: (
                                                        <div className="h-[450px] w-full">
                                                            <CrewAITaskVisualizer
                                                                spanAttributes={selectedSpan.span_attributes}
                                                            />
                                                        </div>
                                                    ),
                                                },
                                            ]
                                            : []),
                                        ...(shouldShowAgentView
                                            ? [
                                                {
                                                    value: 'agent-visualizer',
                                                    label: 'Agent View',
                                                    content: (
                                                        <div className="h-[450px] w-full">
                                                            {shouldShowCrewAIAgentTab && (
                                                                <CrewAIAgentSpanVisualizer
                                                                    spanAttributes={selectedSpan.span_attributes}
                                                                />
                                                            )}
                                                            {shouldShowADKAgentTab && (
                                                                <ADKAgentSpanVisualizer
                                                                    spanAttributes={selectedSpan.span_attributes}
                                                                />
                                                            )}
                                                            {shouldShowAgnoAgentTab && (
                                                                <AgnoAgentSpanVisualizer
                                                                    spanAttributes={selectedSpan.span_attributes}
                                                                />
                                                            )}
                                                            {shouldShowAG2AgentTab && (
                                                                <AG2AgentSpanVisualizer
                                                                    spanAttributes={selectedSpan.span_attributes}
                                                                />
                                                            )}
                                                        </div>
                                                    ),
                                                },
                                            ]
                                            : []),
                                        ...(shouldShowWorkflowView
                                            ? [
                                                {
                                                    value: 'workflow-visualizer',
                                                    label: 'Workflow View',
                                                    content: (
                                                        <div className="h-[450px] w-full">
                                                            {shouldShowADKWorkflowTab && (
                                                                <ADKWorkflowSpanVisualizer
                                                                    spanAttributes={selectedSpan.span_attributes}
                                                                />
                                                            )}
                                                            {shouldShowAgnoWorkflowTab && (
                                                                <AgnoWorkflowSpanVisualizer
                                                                    spanAttributes={selectedSpan.span_attributes}
                                                                />
                                                            )}
                                                            {shouldShowCrewAIWorkflowTab && (
                                                                <CrewAIWorkflowSpanVisualizer
                                                                    spanAttributes={selectedSpan.span_attributes}
                                                                />
                                                            )}
                                                        </div>
                                                    ),
                                                },
                                            ]
                                            : []),
                                        ...(shouldShowToolTab
                                            ? [
                                                {
                                                    value: 'tool-visualizer',
                                                    label: 'Tool View',
                                                    content: (
                                                        <div className="h-[450px] w-full">
                                                            <UnifiedToolSpanViewer toolSpan={selectedSpan} />
                                                        </div>
                                                    ),
                                                },
                                            ]
                                            : []),
                                        {
                                            value: 'llm-span-raw',
                                            label: 'Raw JSON',
                                            content: (
                                                <div className="h-[450px] w-full">
                                                    <LlmSpanRaw selectedSpan={selectedSpan} />
                                                </div>
                                            ),
                                        },
                                    ]}
                                    defaultValue={'llm-span-raw'}
                                    activeTabId={
                                        (isLlmSpan && hasCompletionsToShow) || !isEmpty(prompts)
                                            ? 'span-pretty'
                                            : shouldShowCrewAITaskTab
                                                ? 'crew-ai-task-visualizer'
                                                : shouldShowWorkflowView
                                                    ? 'workflow-visualizer'
                                                    : shouldShowAgentView
                                                        ? 'agent-visualizer'
                                                        : shouldShowToolTab
                                                            ? 'tool-visualizer'
                                                            : 'llm-span-raw'
                                    }
                                />
                            </div>
                        </>
                    )}
                </div>
            </ResizablePanel>
        </ResizablePanelGroup>
    );
}; 