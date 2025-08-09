import { ISpan } from '@/types/ISpan';
import { Card, CardContent } from '@/components/ui/card';
import CollapsibleSection from '../crewai/collapsible-section';
import { Container } from '@/components/ui/container';
import { isAG2Span, extractAG2ToolName, deserializeAG2ToolResult, formatAG2ToolArguments } from '@/utils/ag2.utils';

interface ParsedInput {
    args: any[];
    kwargs: Record<string, any>;
}

interface ToolData {
    name: string;
    parameters?: any;
    args?: any[];
    kwargs?: Record<string, any>;
    result?: string;
    output?: string;
    error?: string;
    status: 'succeeded' | 'failed';
    duration: number;
    // Agno-specific fields
    description?: string;
    functionName?: string;
    functionModule?: string;
    functionQualname?: string;
    formattedArgs?: string;
    resultType?: string;
    isGenerator?: boolean;
    executionSummary?: string;
    requiresConfirmation?: string;
    showResult?: boolean;
}

// Custom code viewer component for displaying code content
const CodeViewer = ({ code }: { code: string }) => {
    return (
        <pre className="mb-3 overflow-x-hidden overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-gray-200 bg-gray-50 p-3 text-sm shadow-sm dark:border-slate-700/80 dark:bg-slate-900">
            <code className="language-json">{code}</code>
        </pre>
    );
};

export const UnifiedToolSpanViewer = ({ toolSpan }: { toolSpan: ISpan }) => {
    const toolData = extractUnifiedToolData(toolSpan);

    return (
        <Container className="rounded-2xl bg-[#F7F8FF] dark:bg-transparent">
            <Card className="rounded-xl border-white bg-transparent p-5 shadow-xl transition-all duration-300">
                {toolData ? (
                    <CardContent className="space-y-3">
                        {toolData.name && (
                            <CollapsibleSection title="Tool Name" defaultExpanded={true}>
                                <CodeViewer code={String(toolData.name)} />
                            </CollapsibleSection>
                        )}

                        {/* Agno-specific description */}
                        {toolData.description && (
                            <CollapsibleSection title="Description" defaultExpanded={true}>
                                <CodeViewer code={toolData.description} />
                            </CollapsibleSection>
                        )}

                        {/* Handle both parameters (CrewAI) and formattedArgs (Agno) formats */}
                        {toolData.formattedArgs && (
                            <CollapsibleSection title="Arguments" defaultExpanded={true}>
                                <CodeViewer code={toolData.formattedArgs} />
                            </CollapsibleSection>
                        )}

                        {toolData.parameters && !toolData.formattedArgs && (
                            <CollapsibleSection title="Parameters" defaultExpanded={true}>
                                <CodeViewer code={
                                    typeof toolData.parameters === 'string'
                                        ? toolData.parameters
                                        : JSON.stringify(toolData.parameters, null, 2)
                                } />
                            </CollapsibleSection>
                        )}

                        {toolData.args && toolData.args.length > 0 && (
                            <CollapsibleSection title="Arguments Array" defaultExpanded={true}>
                                <CodeViewer code={JSON.stringify(toolData.args, null, 2)} />
                            </CollapsibleSection>
                        )}

                        {toolData.kwargs && Object.keys(toolData.kwargs).length > 0 && (
                            <CollapsibleSection title="Keyword Arguments" defaultExpanded={true}>
                                <CodeViewer code={JSON.stringify(toolData.kwargs, null, 2)} />
                            </CollapsibleSection>
                        )}

                        {/* Handle both result (CrewAI) and output (generic) formats */}
                        {(toolData.result || toolData.output) && (
                            <CollapsibleSection title="Result" defaultExpanded={true}>
                                <CodeViewer code={String(toolData.result || toolData.output)} />
                            </CollapsibleSection>
                        )}

                        {toolData.isGenerator && toolData.resultType && (
                            <CollapsibleSection title="Result Type" defaultExpanded={false}>
                                <CodeViewer code={JSON.stringify({
                                    type: toolData.resultType,
                                    isGenerator: toolData.isGenerator
                                }, null, 2)} />
                            </CollapsibleSection>
                        )}

                        {toolData.executionSummary && (
                            <CollapsibleSection title="Execution Summary" defaultExpanded={false}>
                                <CodeViewer code={toolData.executionSummary} />
                            </CollapsibleSection>
                        )}

                        {toolData.error && (
                            <CollapsibleSection title="Error" defaultExpanded={false}>
                                <CodeViewer code={String(toolData.error)} />
                            </CollapsibleSection>
                        )}
                    </CardContent>
                ) : (
                    <CardContent className="space-y-3">
                        <p>No tool data available</p>
                    </CardContent>
                )}
            </Card>
        </Container>
    );
};

export const extractUnifiedToolData = (span: ISpan | null): ToolData | null => {
    if (!span) return null;

    const spanAttributes = span.span_attributes || {};

    // ===== AGNO Framework Tool Processing =====
    // Agno has its own specific format with detailed function metadata
    if (spanAttributes.gen_ai?.system === 'agno' && spanAttributes.tool) {
        const tool = spanAttributes.tool;

        return {
            name: tool.name || tool.function_name || span.span_name || 'Unknown Tool',
            parameters: tool.parameters || '',
            formattedArgs: tool.formatted_args || '',
            result: tool.result || '',
            error: span.status_message || '',
            status: (tool.status === 'success' || tool.execution_status === 'success') ? 'succeeded' : 'failed',
            duration: span.durationMs || span.duration ? span.duration / 1000000 : 0,
            // Agno-specific fields
            description: tool.description || tool.function_description || '',
            functionName: tool.function_name || '',
            functionModule: tool.function_module || '',
            functionQualname: tool.function_qualname || '',
            resultType: tool.actual_result_type || '',
            isGenerator: tool.result_is_generator === 'true',
            executionSummary: tool.execution_summary || '',
            requiresConfirmation: tool.requires_confirmation || '',
            showResult: tool.show_result === 'True',
        };
    }

    // ===== AG2 (AutoGen2) Framework Tool Processing =====
    // AG2 stores tool names in gen_ai.request.tools and results as JSON strings
    if (isAG2Span(span.span_name) && span.span_name?.includes('.tool.') && spanAttributes.tool) {
        const tool = spanAttributes.tool;
        const genAiTools = spanAttributes.gen_ai?.request?.tools || [];
        
        // Extract tool name using AG2-specific logic
        let toolName = extractAG2ToolName(span) || tool.name || 'function';
        
        // Extract and format tool arguments
        let parameters = '';
        if (genAiTools.length > 0 && genAiTools[0].arguments) {
            parameters = formatAG2ToolArguments(genAiTools[0].arguments);
        }

        // Deserialize the result using AG2-specific logic
        let result = tool.result || '';
        const deserializedResult = deserializeAG2ToolResult(result);
        if (deserializedResult) {
            if (deserializedResult.content) {
                result = deserializedResult.content;
            } else if (deserializedResult.raw !== result) {
                // The result was successfully parsed, show the formatted JSON
                result = JSON.stringify({
                    name: deserializedResult.name,
                    role: deserializedResult.role,
                    content: deserializedResult.content
                }, null, 2);
            }
            // Update tool name if available in the result
            if (deserializedResult.name && deserializedResult.name !== 'function') {
                toolName = deserializedResult.name;
            }
        }

        return {
            name: toolName,
            parameters: parameters,
            result: result,
            error: span.status_message || '',
            status: tool.status === 'success' ? 'succeeded' : 'failed',
            duration: span.durationMs || span.duration ? span.duration / 1000000 : 0,
        };
    }

    // ===== CrewAI Framework Tool Processing =====
    // CrewAI tools have standard tool attributes without a specific system identifier
    if (spanAttributes.tool && spanAttributes.gen_ai?.system !== 'agno') {
        const tool = spanAttributes.tool;
        const error = spanAttributes.error || {};

        return {
            name: tool.name || span.span_name || 'Unknown Tool',
            parameters: tool.parameters || '',
            result: tool.result || '',
            error: error.message || span.status_message || '',
            status: span.status_code === 'Error' ? 'failed' : 'succeeded',
            duration: span.durationMs || span.duration ? span.duration / 1000000 : 0,
        };
    }

    // ===== Generic/AgentOps Tool Processing =====
    // Fallback for tools using the standard AgentOps structure
    const agentopsEntity = spanAttributes.agentops?.entity || {};
    const operation = spanAttributes.operation || {};

    // Parse the input string to extract args and kwargs
    let parsedInput: ParsedInput = { args: [], kwargs: {} };
    if (agentopsEntity.input) {
        try {
            const input = JSON.parse(agentopsEntity.input);
            parsedInput = {
                args: input.args || [],
                kwargs: input.kwargs || {},
            };
        } catch (e) {
            // If parsing fails, treat as parameters string
            console.error('Failed to parse tool input:', e);
        }
    }

    // Parse the output if it's a string
    let output = agentopsEntity.output;
    if (output && typeof output === 'string') {
        // Remove extra quotes if the output is double-quoted
        if (output.startsWith('"') && output.endsWith('"')) {
            output = output.slice(1, -1);
        }
        // Replace escaped characters
        output = output.replace(/\\n/g, '\n').replace(/\\"/g, '"');
    }

    return {
        name: operation.name || span.span_name || 'Unknown Tool',
        args: parsedInput.args.length > 0 ? parsedInput.args : undefined,
        kwargs: Object.keys(parsedInput.kwargs).length > 0 ? parsedInput.kwargs : undefined,
        parameters: agentopsEntity.input && !parsedInput.args.length && !Object.keys(parsedInput.kwargs).length
            ? agentopsEntity.input
            : undefined,
        output: output || '',
        error: span.status_message || '',
        status: span.status_code === 'Error' ? 'failed' : 'succeeded',
        duration: span.duration ? span.duration / 1000000 : 0, // Convert nanoseconds to milliseconds
    };
};

// Legacy exports for backward compatibility
export const ToolSpanViewer = UnifiedToolSpanViewer;
export const extractGenericToolData = extractUnifiedToolData;
