'use client';

import { toast } from '@/components/ui/use-toast';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Tables } from '@/lib/types_db';
import { useMutation, useQueryClient } from '@tanstack/react-query';
const TTD_QUERY_KEY = 'ttds';
import { PencilIcon, Delete01Icon as TrashIcon } from 'hugeicons-react';
import { useRouter } from 'next/navigation';

export default function TimeTravelTable({ ttds }: { ttds: Tables<'ttd'>[] }) {
  const queryClient = useQueryClient();
  const router = useRouter();

  const deleteMutation = useMutation({
    mutationFn: async (ttdId: string) => {
      await fetchAuthenticatedApi(`/timetravel/${ttdId}`, { method: 'DELETE' });
      return ttdId;
    },
    onSuccess: () => {
      toast({ title: '✅ Snapshot Deleted' });
      queryClient.invalidateQueries({ queryKey: [TTD_QUERY_KEY] });
    },
    onError: (error: any) => {
      console.error('Delete TTD Error:', error);
      toast({ title: '❌ Delete Failed', description: error.message, variant: 'destructive' });
    },
  });

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
            >
              Name
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
            >
              Created At
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
          {ttds.map((ttd) => (
            <tr key={ttd.ttd_id}>
              <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                {ttd.branch_name}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                {ttd.created_at ? new Date(ttd.created_at).toLocaleString() : 'N/A'}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm font-medium">
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/timetravel/${ttd.ttd_id}`)}
                  >
                    <PencilIcon className="mr-1 h-4 w-4" /> Edit
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive" size="sm" disabled={deleteMutation.isPending}>
                        <TrashIcon className="mr-1 h-4 w-4" /> Delete
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This action cannot be undone. This will permanently delete the time travel
                          snapshot &quot;{ttd.branch_name}&quot;.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => deleteMutation.mutate(ttd.ttd_id)}>
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
