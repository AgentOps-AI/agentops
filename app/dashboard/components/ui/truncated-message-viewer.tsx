'use client';

import React, { useState, useMemo } from 'react';
import { ChatViewerRuntimeProvider } from '@/app/chat-viewer-runtime-provider';
import { Thread } from '@/components/assistant-ui/thread';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, Expand } from 'lucide-react';
import { LargeContentViewerDialog } from './large-content-viewer-dialog';

interface TruncatedMessageViewerProps {
    data: any[];
    type: string;
    role?: 'assistant' | 'system' | 'tool';
    maxLength?: number;
}

const CHARACTER_LIMIT = 5000; // Characters to show before truncation
const TRUNCATION_THRESHOLD = 10000; // Only truncate if message exceeds this
const LARGE_CONTENT_THRESHOLD = 100000; // Prevent inline expansion for content larger than this

export function TruncatedMessageViewer({
    data,
    type,
    role,
    maxLength = CHARACTER_LIMIT,
}: TruncatedMessageViewerProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isDialogOpen, setIsDialogOpen] = useState(false);

    // Calculate total content length and prepare truncated data
    const { truncatedData, totalLength, needsTruncation, fullContent } = useMemo(() => {
        let totalChars = 0;
        let shouldTruncate = false;
        let fullContentStr = '';

        // First pass: calculate total length and build full content string
        const processedData = data.map((item) => {
            let content = '';
            if (typeof item === 'string') {
                content = item;
            } else if (item && typeof item === 'object' && 'content' in item) {
                content = item.content || '';
            }
            totalChars += content.length;
            fullContentStr += content + '\n';
            return item;
        });

        shouldTruncate = totalChars > TRUNCATION_THRESHOLD;
        const isVeryLarge = totalChars > LARGE_CONTENT_THRESHOLD;

        // For very large content, never expand inline
        if (!shouldTruncate || (isExpanded && !isVeryLarge)) {
            return {
                truncatedData: data,
                totalLength: totalChars,
                needsTruncation: shouldTruncate,
                fullContent: fullContentStr.trim()
            };
        }

        // Second pass: truncate if needed
        let charCount = 0;
        const truncated = processedData.map((item) => {
            if (charCount >= maxLength) {
                return null;
            }

            let content = '';
            if (typeof item === 'string') {
                content = item;
            } else if (item && typeof item === 'object' && 'content' in item) {
                content = item.content || '';
            }

            const remainingChars = maxLength - charCount;
            if (content.length > remainingChars) {
                // Truncate this item
                const truncatedContent = content.slice(0, remainingChars) + '...';
                charCount = maxLength;

                if (typeof item === 'string') {
                    return truncatedContent;
                } else {
                    return { ...item, content: truncatedContent };
                }
            }

            charCount += content.length;
            return item;
        }).filter(Boolean);

        return {
            truncatedData: truncated,
            totalLength: totalChars,
            needsTruncation: shouldTruncate,
            fullContent: fullContentStr.trim()
        };
    }, [data, maxLength, isExpanded]);

    const displayData = needsTruncation && !isExpanded ? truncatedData : data;
    const isVeryLarge = totalLength > LARGE_CONTENT_THRESHOLD;

    return (
        <div className="relative">
            <ChatViewerRuntimeProvider data={displayData} type={type}>
                <Thread role={type === 'user' ? undefined : role} />
            </ChatViewerRuntimeProvider>

            {needsTruncation && (
                <div className="mt-2 flex items-center justify-center gap-2">
                    {(!isVeryLarge || !isExpanded) && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="text-xs text-muted-foreground hover:text-foreground"
                        >
                            {isExpanded ? (
                                <>
                                    <ChevronUp className="mr-1 h-3 w-3" />
                                    Show less
                                </>
                            ) : (
                                <>
                                    <ChevronDown className="mr-1 h-3 w-3" />
                                    Show more ({(totalLength / 1000).toFixed(0)}k characters)
                                </>
                            )}
                        </Button>
                    )}

                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsDialogOpen(true)}
                        className="text-xs text-muted-foreground hover:text-foreground"
                    >
                        <Expand className="mr-1 h-3 w-3" />
                        View full content
                    </Button>
                </div>
            )}

            <LargeContentViewerDialog
                isOpen={isDialogOpen}
                onClose={() => setIsDialogOpen(false)}
                content={fullContent}
                title={`Full Message Content (${type})`}
            />
        </div>
    );
} 