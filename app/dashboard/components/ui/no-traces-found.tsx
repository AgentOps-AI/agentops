'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { LineChart, ArrowRight } from 'lucide-react';

interface NoTracesFoundProps {
    message?: string;
}

export function NoTracesFound({
    message = "Seems like you don't have any traces. Create your first trace to see analytics and insights (or adjust your filters).",
}: NoTracesFoundProps) {
    const router = useRouter();

    return (
        <div className="flex flex-col items-center my-2 justify-center rounded-lg border border-dashed border-muted-foreground/30 py-20 text-center">
            <LineChart className="mb-4 h-16 w-16 text-primary/70" strokeWidth={1.5} />
            <div className="mb-3 text-2xl font-medium text-primary">No traces found</div>
            <p className="mb-6 max-w-md text-muted-foreground">{message}</p>
            <Button size="lg" onClick={() => router.push('/get-started')} className="gap-2">
                Get started <ArrowRight className="h-4 w-4" />
            </Button>
        </div>
    );
} 