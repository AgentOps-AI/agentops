'use client';

import { ColumnDef } from '@tanstack/react-table';
import { Copy01Icon as Copy } from 'hugeicons-react';

import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import Link from 'next/link';

export type TimeTravelData = {
  branch_name: string;
  ttd_id: string;
  session_id: string;
  created_at: string;
};

export const columns: ColumnDef<TimeTravelData>[] = [
  {
    accessorKey: 'branch_name',
    header: 'Branch Name',
    cell: ({ row }) => {
      return <>{row.original.branch_name}</>;
    },
  },
  {
    accessorKey: 'session_id',
    header: 'Branched from Session',
    cell: ({ row }) => {
      const sessionId = row.original.session_id;
      return (
        <Link
          href={`https://app.agentops.ai/sessions/${sessionId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="underline"
        >
          {sessionId}
        </Link>
      );
    },
  },
  {
    accessorKey: 'created_at',
    header: 'Created At',
    cell: ({ row }) => {
      return new Date(row.original.created_at).toLocaleString([], {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      });
    },
    sortingFn: (rowA, rowB, _columnId) => {
      const dateA = new Date(rowA.original.created_at).getTime();
      const dateB = new Date(rowB.original.created_at).getTime();
      return dateB - dateA; // Descending order
    },
  },
  {
    id: 'CLI Command',
    header: () => <div className="text-center">CLI Command</div>,
    cell: ({ row }) => {
      return (
        <div className="flex justify-center">
          <Button
            className="flex flex-row items-center gap-1 text-blue-500"
            variant="ghost"
            onClick={() =>
              navigator.clipboard
                .writeText('agentops timetravel ' + row.original.ttd_id)
                .then(() => {
                  toast({
                    title: 'CLI command copied to clipboard',
                    description: 'agentops timetravel ' + row.original.ttd_id,
                  });
                })
                .catch(() => {
                  toast({
                    title: '❌ Could Not Access Clipboard - Manually copy the CLI command below:',
                    description: 'agentops timetravel ' + row.original.ttd_id,
                  });
                })
            }
          >
            <Copy className="h-4 w-4" />
            <div>CLI</div>
          </Button>
        </div>
      );
    },
  },
  {
    id: 'delete',
    header: () => <div className="text-center">Delete</div>,
    cell: () => (
      <div className="flex justify-center">{/* Add your delete button or icon here */}</div>
    ),
  },
];
