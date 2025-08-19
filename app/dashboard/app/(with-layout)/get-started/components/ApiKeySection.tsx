'use client';

import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { Copy01Icon as CopyIcon, ViewIcon as Eye, ViewOffIcon as EyeOff } from 'hugeicons-react';
import { useState } from 'react';

interface ApiKeySectionProps {
    selectedProject: any;
    title?: string;
    description?: string;
}

export default function ApiKeySection({
    selectedProject,
    title = 'Your AgentOps API Key',
    description = "You'll need this key to configure AgentOps in your project"
}: ApiKeySectionProps) {
    const { toast } = useToast();
    const [showApiKey, setShowApiKey] = useState(false);

    const apiKey = selectedProject?.api_key || 'your-api-key-here';
    const displayKey = showApiKey ? apiKey : `${'•'.repeat(28)}${apiKey.slice(-8)}`;

    const handleCopyApiKey = () => {
        if (selectedProject?.api_key) {
            navigator.clipboard.writeText(selectedProject.api_key)
                .then(() => {
                    toast({
                        title: 'API Key Copied',
                        description: 'Your API key has been copied to clipboard',
                    });
                })
                .catch(() => {
                    toast({
                        title: '❌ Could Not Copy',
                        description: 'Please manually copy the API key',
                    });
                });
        }
    };

    return (
        <div className="max-w-3xl">
            <h2 className="mb-2 text-xl font-semibold">{title}</h2>
            <div className="rounded-lg border bg-gray-50 p-4 dark:bg-gray-900">
                <div className="flex items-center justify-between rounded bg-gray-100 p-3 dark:bg-gray-800">
                    <code className="flex-1 break-all text-sm font-mono text-gray-700 dark:text-gray-300">
                        {displayKey}
                    </code>
                    <div className="flex items-center gap-1 ml-2">
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setShowApiKey(!showApiKey)}
                            className="p-2"
                        >
                            {showApiKey ? (
                                <EyeOff className="h-4 w-4" />
                            ) : (
                                <Eye className="h-4 w-4" />
                            )}
                        </Button>
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={handleCopyApiKey}
                            className="p-2"
                        >
                            <CopyIcon className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
                <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                    {description}
                </p>
            </div>
        </div>
    );
} 