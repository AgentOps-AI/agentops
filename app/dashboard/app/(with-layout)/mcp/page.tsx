'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    Copy01Icon as CopyIcon,
    CheckmarkCircle01Icon as Check,
} from 'hugeicons-react';
import { useEffect, useMemo, useState } from 'react';
import { useHeaderContext } from '@/app/providers/header-provider';
import { useToast } from '@/components/ui/use-toast';
import { Prism, SyntaxHighlighterProps } from 'react-syntax-highlighter';
import Image from 'next/image';
import { useProject } from '@/app/providers/project-provider';
import CollapsibleSection from '@/app/(with-layout)/traces/_components/crewai/collapsible-section';
const SyntaxHighlighter = Prism as any as React.FC<SyntaxHighlighterProps>;

export default function MCPPage() {
    const { setHeaderTitle, setHeaderContent } = useHeaderContext();
    const { toast } = useToast();
    const { selectedProject } = useProject();
    const [copiedConfig, setCopiedConfig] = useState(false);
    const [copiedSmithery, setCopiedSmithery] = useState(false);
    const [copiedIde, setCopiedIde] = useState<string | null>(null);

    useEffect(() => {
        setHeaderTitle('MCP Server');
        setHeaderContent(null);
    }, [setHeaderTitle, setHeaderContent]);

    const mcpConfig = useMemo(() => {
        const apiKey = selectedProject?.api_key || 'YOUR_API_KEY';
        return `{
  "mcpServers": {
    "agentops": {
      "command": "npx",
      "args": [
        "agentops-mcp"
      ],
      "env": {
        "AGENTOPS_API_KEY": "${apiKey}"
      }
    }
  }
}`;
    }, [selectedProject]);

    const smitheryCommand = 'npx -y @smithery/cli install @AgentOps-AI/agentops-mcp --client claude';

    const cursorDeeplink = useMemo(() => {
        const apiKey = selectedProject?.api_key || '';
        // The config object needs to be stringified, then base64 encoded for the deeplink.
        const configObject = {
            "command": "npx agentops-mcp",
            "env": {
                "AGENTOPS_API_KEY": apiKey
            }
        };
        const encodedConfig = btoa(JSON.stringify(configObject));
        return `https://cursor.com/install-mcp?name=agentops&config=${encodedConfig}`;
    }, [selectedProject]);

    const customStyle = {
        'pre[class*="language-"]': {
            color: 'white',
            background: 'transparent',
            margin: 0,
            padding: 0,
            whiteSpace: 'pre-wrap',
            cursor: 'text',
        },
        'code[class*="language-"]': {
            cursor: 'text',
        },
        keyword: {
            color: '#569cd6',
        },
        string: {
            color: '#ce9178',
        },
        number: {
            color: '#b5cea8',
        },
        boolean: {
            color: '#569cd6',
        },
        null: {
            color: '#569cd6',
        },
        punctuation: {
            color: '#d4d4d4',
        },
        property: {
            color: '#9cdcfe',
        },
    };

    const handleCopy = async (text: string, type: 'config' | 'smithery' | 'ide') => {
        try {
            await navigator.clipboard.writeText(text);
            const toastMessage = {
                title: 'Copied to clipboard',
                description: text.length > 100 ? 'Configuration copied' : text,
            };

            if (type === 'config') {
                setCopiedConfig(true);
                setTimeout(() => setCopiedConfig(false), 2000);
            } else if (type === 'smithery') {
                setCopiedSmithery(true);
                setTimeout(() => setCopiedSmithery(false), 2000);
            } else {
                setCopiedIde(text);
                setTimeout(() => setCopiedIde(null), 2000);
            }

            toast(toastMessage);

        } catch (error) {
            toast({
                title: 'Failed to copy',
                description: 'Please manually copy the configuration.',
                variant: 'destructive',
            });
        }
    };

    return (
        <div className="mx-auto max-w-4xl space-y-12 px-4 py-8 sm:px-6 lg:px-8">

            {/* Tutorial Video */}
            <section className="space-y-4">
                <h2 className="text-xl font-semibold tracking-tight text-primary">Overview Video</h2>
                <div className="aspect-video overflow-hidden rounded-lg border">
                    <iframe
                        width="100%"
                        height="100%"
                        src="https://www.youtube.com/embed/lTa3Sk8C4f0"
                        title="AgentOps MCP Setup Tutorial"
                        frameBorder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                        allowFullScreen
                    />
                </div>
            </section>
            {/* Beta Notice */}
            <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30 p-4">
                <div className="flex items-start space-x-3">
                    <div className="flex-1">
                        <p className="mt-1 text-sm text-blue-700 dark:text-blue-200">
                            The AgentOps MCP Server is currently in beta. We&apos;d love to hear your feedback!{' '}
                            <a
                                href="https://cal.com/team/agency-ai/agentops-feedback"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium underline hover:text-blue-800 dark:hover:text-blue-100"
                            >
                                Share your thoughts here
                            </a>
                        </p>
                    </div>
                </div>
            </div>

            {/* Installation */}
            <section className="space-y-4">
                <h2 className="text-xl font-semibold tracking-tight text-primary">Installation</h2>
                <p className="text-muted-foreground">
                    Choose your IDE or tool to get started with the AgentOps MCP server.
                </p>

                <div className="space-y-4">
                    {/* Cursor */}
                    <CollapsibleSection title="Cursor" defaultExpanded={false}>
                        <div className="space-y-4 pt-4">
                            <div>
                                <a href={cursorDeeplink} target="_blank" rel="noopener noreferrer">
                                    <Image src="https://cursor.com/deeplink/mcp-install-dark.svg" alt="Install MCP Server in Cursor" width={180} height={40} />
                                </a>
                            </div>
                            <p className="text-muted-foreground">
                                Add the AgentOps MCP server to Cursor with one click.
                            </p>
                        </div>
                    </CollapsibleSection>

                    {/* Claude Desktop */}
                    <CollapsibleSection title="Claude Desktop" defaultExpanded={false}>
                        <div className="space-y-4 pt-4">
                            <p className="text-muted-foreground">
                                Add to your Claude Desktop configuration file.
                            </p>

                            <div className="space-y-2 text-sm text-muted-foreground">
                                <p><strong>macOS:</strong> <code className="text-xs">~/Library/Application Support/Claude/claude_desktop_config.json</code></p>
                                <p><strong>Windows:</strong> <code className="text-xs">%APPDATA%\Claude\claude_desktop_config.json</code></p>
                            </div>

                            <div className="not-prose dark:bg-codeblock relative max-w-3xl overflow-x-auto rounded-xl bg-[#0F1117] dark:ring-1 dark:ring-gray-800/50">
                                <div className="rounded-t-xl border-b border-gray-900/80 bg-black/40 text-xs leading-6">
                                    <div className="flex justify-between">
                                        <div className="text-primary-light relative px-2 pb-2 pt-2.5 font-medium text-gray-400">
                                            <div className="rounded-md px-2">
                                                <div className="z-10">claude_desktop_config.json</div>
                                            </div>
                                        </div>
                                        <button
                                            className="group px-2 text-gray-400 outline-none"
                                            onClick={() => handleCopy(mcpConfig, 'config')}
                                        >
                                            <div className="group-hover:text-primary-light rounded-md px-2 group-hover:bg-gray-700/60">
                                                <div className="h-6 w-4">
                                                    {copiedConfig ? (
                                                        <Check className="h-4 w-4 text-green-500" />
                                                    ) : (
                                                        <CopyIcon className="h-4 w-4" />
                                                    )}
                                                </div>
                                            </div>
                                        </button>
                                    </div>
                                </div>
                                <div className="overflow-x-auto p-4 cursor-text">
                                    <SyntaxHighlighter language="json" style={customStyle}>
                                        {mcpConfig}
                                    </SyntaxHighlighter>
                                </div>
                            </div>
                        </div>
                    </CollapsibleSection>

                    {/* Other IDEs */}
                    <CollapsibleSection title="VSCode, Windsurf, and Zed" defaultExpanded={false}>
                        <div className="space-y-4 pt-4">
                            <p className="text-muted-foreground">
                                For VSCode, Windsurf, and Zed, manually add the following configuration:
                            </p>

                            <div className="space-y-2 text-sm text-muted-foreground">
                                <p><strong>VSCode:</strong> Edit <code className="text-xs">~/.vscode/mcp.json</code> in your project root</p>
                                <p><strong>Windsurf:</strong> Edit <code className="text-xs">~/.codeium/windsurf/mcp_config.json</code> (global only)</p>
                                <p><strong>Zed:</strong> Edit <code className="text-xs">settings.json</code> (open via cmd+, or zed: open settings)</p>
                            </div>

                            <Tabs defaultValue="macos" className="w-full">
                                <TabsList className="grid w-full grid-cols-2">
                                    <TabsTrigger value="macos">macOS/Linux</TabsTrigger>
                                    <TabsTrigger value="windows">Windows</TabsTrigger>
                                </TabsList>

                                <TabsContent value="macos" className="mt-4">
                                    <div className="not-prose dark:bg-codeblock relative max-w-3xl overflow-x-auto rounded-xl bg-[#0F1117] dark:ring-1 dark:ring-gray-800/50">
                                        <div className="rounded-t-xl border-b border-gray-900/80 bg-black/40 text-xs leading-6">
                                            <div className="flex justify-between">
                                                <div className="text-primary-light relative px-2 pb-2 pt-2.5 font-medium text-gray-400">
                                                    <div className="rounded-md px-2">
                                                        <div className="z-10">mcp.json</div>
                                                    </div>
                                                </div>
                                                <button
                                                    className="group px-2 text-gray-400 outline-none"
                                                    onClick={() => handleCopy(mcpConfig, 'ide')}
                                                >
                                                    <div className="group-hover:text-primary-light rounded-md px-2 group-hover:bg-gray-700/60">
                                                        <div className="h-6 w-4">
                                                            {copiedIde === mcpConfig ? (
                                                                <Check className="h-4 w-4 text-green-500" />
                                                            ) : (
                                                                <CopyIcon className="h-4 w-4" />
                                                            )}
                                                        </div>
                                                    </div>
                                                </button>
                                            </div>
                                        </div>
                                        <div className="overflow-x-auto p-4 cursor-text">
                                            <SyntaxHighlighter language="json" style={customStyle}>
                                                {mcpConfig}
                                            </SyntaxHighlighter>
                                        </div>
                                    </div>
                                </TabsContent>

                                <TabsContent value="windows" className="mt-4">
                                    <div className="not-prose dark:bg-codeblock relative max-w-3xl overflow-x-auto rounded-xl bg-[#0F1117] dark:ring-1 dark:ring-gray-800/50">
                                        <div className="rounded-t-xl border-b border-gray-900/80 bg-black/40 text-xs leading-6">
                                            <div className="flex justify-between">
                                                <div className="text-primary-light relative px-2 pb-2 pt-2.5 font-medium text-gray-400">
                                                    <div className="rounded-md px-2">
                                                        <div className="z-10">mcp.json</div>
                                                    </div>
                                                </div>
                                                <button
                                                    className="group px-2 text-gray-400 outline-none"
                                                    onClick={() => handleCopy(mcpConfig, 'ide')}
                                                >
                                                    <div className="group-hover:text-primary-light rounded-md px-2 group-hover:bg-gray-700/60">
                                                        <div className="h-6 w-4">
                                                            {copiedIde === mcpConfig ? (
                                                                <Check className="h-4 w-4 text-green-500" />
                                                            ) : (
                                                                <CopyIcon className="h-4 w-4" />
                                                            )}
                                                        </div>
                                                    </div>
                                                </button>
                                            </div>
                                        </div>
                                        <div className="overflow-x-auto p-4 cursor-text">
                                            <SyntaxHighlighter language="json" style={customStyle}>
                                                {mcpConfig}
                                            </SyntaxHighlighter>
                                        </div>
                                    </div>
                                </TabsContent>
                            </Tabs>
                        </div>
                    </CollapsibleSection>

                    {/* Smithery */}
                    <CollapsibleSection title="Smithery" defaultExpanded={false}>
                        <div className="space-y-4 pt-4">
                            <p className="text-muted-foreground">
                                To install automatically for Claude Desktop via Smithery, run this command.
                            </p>
                            <div className="not-prose dark:bg-codeblock relative max-w-3xl overflow-x-auto rounded-xl bg-[#0F1117] dark:ring-1 dark:ring-gray-800/50">
                                <div className="rounded-t-xl border-b border-gray-900/80 bg-black/40 text-xs leading-6">
                                    <div className="flex justify-between">
                                        <div className="text-primary-light relative px-2 pb-2 pt-2.5 font-medium text-gray-400">
                                            <div className="rounded-md px-2">
                                                <div className="z-10">bash</div>
                                            </div>
                                        </div>
                                        <button
                                            className="group px-2 text-gray-400 outline-none"
                                            onClick={() => handleCopy(smitheryCommand, 'smithery')}
                                        >
                                            <div className="group-hover:text-primary-light rounded-md px-2 group-hover:bg-gray-700/60">
                                                <div className="h-6 w-4">
                                                    {copiedSmithery ? (
                                                        <Check className="h-4 w-4 text-green-500" />
                                                    ) : (
                                                        <CopyIcon className="h-4 w-4" />
                                                    )}
                                                </div>
                                            </div>
                                        </button>
                                    </div>
                                </div>
                                <div className="overflow-x-auto p-4 cursor-text">
                                    <SyntaxHighlighter language="bash" style={customStyle}>
                                        {smitheryCommand}
                                    </SyntaxHighlighter>
                                </div>
                            </div>
                        </div>
                    </CollapsibleSection>
                </div>
            </section>


            {/* Available Tools */}
            <section className="space-y-6">
                <h2 className="text-xl font-semibold tracking-tight text-primary">Available Tools</h2>
                <div className="space-y-5">
                    <div>
                        <code className="font-mono text-base font-semibold">auth</code>
                        <p className="mt-1 text-muted-foreground">Authorize using an AgentOps project API key. The server will automatically prompt for this when needed.</p>
                        <ul className="mt-2 ml-4 list-disc space-y-1 text-sm text-muted-foreground">
                            <li><span className="font-semibold">Parameters:</span> <code className="text-xs">api_key</code> (string)</li>
                        </ul>
                    </div>
                    <div>
                        <code className="font-mono text-base font-semibold">get_project</code>
                        <p className="mt-1 text-muted-foreground">Get details about the current project.</p>
                        <ul className="mt-2 ml-4 list-disc space-y-1 text-sm text-muted-foreground">
                            <li><span className="font-semibold">Parameters:</span> None</li>
                            <li><span className="font-semibold">Returns:</span> Project information including ID, name, and environment</li>
                        </ul>
                    </div>
                    <div>
                        <code className="font-mono text-base font-semibold">get_trace</code>
                        <p className="mt-1 text-muted-foreground">Get trace information by ID.</p>
                        <ul className="mt-2 ml-4 list-disc space-y-1 text-sm text-muted-foreground">
                            <li><span className="font-semibold">Parameters:</span> <code className="text-xs">trace_id</code> (string)</li>
                            <li><span className="font-semibold">Returns:</span> Trace details and metrics</li>
                        </ul>
                    </div>
                    <div>
                        <code className="font-mono text-base font-semibold">get_span</code>
                        <p className="mt-1 text-muted-foreground">Get span information by ID.</p>
                        <ul className="mt-2 ml-4 list-disc space-y-1 text-sm text-muted-foreground">
                            <li><span className="font-semibold">Parameters:</span> <code className="text-xs">span_id</code> (string)</li>
                            <li><span className="font-semibold">Returns:</span> Span attributes and metrics</li>
                        </ul>
                    </div>
                    <div>
                        <code className="font-mono text-base font-semibold">get_complete_trace</code>
                        <p className="mt-1 text-muted-foreground">Get complete trace information by ID.</p>
                        <ul className="mt-2 ml-4 list-disc space-y-1 text-sm text-muted-foreground">
                            <li><span className="font-semibold">Parameters:</span> <code className="text-xs">trace_id</code> (string)</li>
                            <li><span className="font-semibold">Returns:</span> Complete trace and associated span details</li>
                        </ul>
                    </div>
                </div>
            </section>
        </div>
    );
} 