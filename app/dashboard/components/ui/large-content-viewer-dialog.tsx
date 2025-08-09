'use client';

import React, { useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Download, ExternalLink, Copy, Check } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';
import MonacoEditor from '@monaco-editor/react';

interface LargeContentViewerDialogProps {
    isOpen: boolean;
    onClose: () => void;
    content: string;
    title?: string;
}

export function LargeContentViewerDialog({
    isOpen,
    onClose,
    content,
    title = 'Large Message Content',
}: LargeContentViewerDialogProps) {
    const [isCopied, setIsCopied] = React.useState(false);

    // Format file size
    const fileSize = useMemo(() => {
        const bytes = new Blob([content]).size;
        if (bytes < 1024) return bytes + ' bytes';
        if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / 1048576).toFixed(2) + ' MB';
    }, [content]);

    // Character count
    const charCount = content.length;

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(content);
            setIsCopied(true);
            toast({ title: 'Copied to clipboard!' });
            setTimeout(() => setIsCopied(false), 2000);
        } catch (error) {
            toast({
                title: 'Failed to copy',
                description: 'Content may be too large for clipboard',
                variant: 'destructive'
            });
        }
    };

    const handleDownload = () => {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `message-content-${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast({ title: 'Downloaded successfully!' });
    };

    const handleOpenInNewTab = () => {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
        // Clean up after a delay
        setTimeout(() => URL.revokeObjectURL(url), 60000);
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-[95vw] sm:max-w-[90vw] w-full sm:w-[90vw] h-[95vh] sm:h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">
                <DialogHeader className="px-4 sm:px-6 py-4 sm:py-5 border-b bg-background shadow-sm relative z-10">
                    <div className="space-y-3 sm:space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4">
                            <div className="space-y-1 sm:space-y-1.5">
                                <DialogTitle className="text-base sm:text-lg font-semibold leading-tight">
                                    {title}
                                </DialogTitle>
                                <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs sm:text-sm text-muted-foreground">
                                    <span className="font-medium">{charCount.toLocaleString()} characters</span>
                                    <span className="text-muted-foreground/50">•</span>
                                    <span className="font-medium">{fileSize}</span>
                                </div>
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={handleCopy}
                                className="gap-1.5 h-8 sm:h-9 px-3 sm:px-4 text-xs sm:text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                            >
                                {isCopied ? (
                                    <Check className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                                ) : (
                                    <Copy className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                                )}
                                <span>{isCopied ? 'Copied!' : 'Copy'}</span>
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={handleDownload}
                                className="gap-1.5 h-8 sm:h-9 px-3 sm:px-4 text-xs sm:text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                            >
                                <Download className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                                <span>Download</span>
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={handleOpenInNewTab}
                                className="gap-1.5 h-8 sm:h-9 px-3 sm:px-4 text-xs sm:text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                            >
                                <ExternalLink className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                                <span>Open in New Tab</span>
                            </Button>
                        </div>
                    </div>
                </DialogHeader>

                <div className="flex-1 min-h-0 overflow-hidden bg-[#1e1e1e]">
                    <MonacoEditor
                        value={content}
                        language="markdown"
                        theme="vs-dark"
                        options={{
                            readOnly: true,
                            minimap: {
                                enabled: true,
                                side: 'right',
                                size: 'fill',
                                showSlider: 'mouseover',
                            },
                            wordWrap: 'on',
                            scrollBeyondLastLine: false,
                            fontSize: 14,
                            lineNumbers: 'on',
                            renderWhitespace: 'none',
                            scrollbar: {
                                vertical: 'visible',
                                horizontal: 'visible',
                                verticalScrollbarSize: 10,
                                horizontalScrollbarSize: 10,
                            },
                            padding: {
                                top: 16,
                                bottom: 16,
                            },
                            smoothScrolling: true,
                            cursorBlinking: 'solid',
                            lineHeight: 21,
                            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                        }}
                    />
                </div>
            </DialogContent>
        </Dialog>
    );
} 