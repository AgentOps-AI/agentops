'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loading03Icon as Loader } from 'hugeicons-react';
import { Copy01Icon as Copy } from 'hugeicons-react';
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
import { toast } from '@/components/ui/use-toast';
import { ILlms } from '@/lib/interfaces';
import { useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';

type BranchModalProps = {
  llmEvents: ILlms[];
  setBranchModalOpen: (open: boolean) => void;
  project_id: string;
  session_id: string;
};

enum BranchState {
  EnterBranchName,
  Loading,
  BranchSucceeded,
  BranchFailed,
}

const TTD_QUERY_KEY = 'ttds';

export const BranchModal: React.FC<BranchModalProps> = ({
  // llmEvents,
  setBranchModalOpen,
  project_id,
  session_id,
}) => {
  const [branchState, setBranchState] = useState<BranchState>(BranchState.EnterBranchName);
  const [cliCommand, _] = useState<string>(``);
  // const [showBranchModal, setShowBranchModal] = useState<boolean>(false);
  const [branchName, setBranchName] = useState('');
  const queryClient = useQueryClient();

  const handleSaveBranch = async () => {
    if (!branchName.trim()) {
      toast({
        title: 'Error',
        description: 'Branch name cannot be empty.',
        variant: 'destructive',
      });
      return;
    }
    setBranchState(BranchState.Loading);
    try {
      await fetchAuthenticatedApi('/timetravel', {
        method: 'POST',
        body: JSON.stringify({
          name: branchName,
          projectId: project_id,
          sessionId: session_id,
        }),
      });
      toast({ title: '✅ Branch Created', description: `Snapshot "${branchName}" saved.` });
      queryClient.invalidateQueries({ queryKey: [TTD_QUERY_KEY] });
      setBranchModalOpen(false);
    } catch (error: any) {
      console.error('Error saving branch:', error);
      toast({
        title: '❌ Error Saving Branch',
        description: error.message,
        variant: 'destructive',
      });
    } finally {
      setBranchState(BranchState.BranchSucceeded);
    }
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline">Create Branch</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Create Branch</AlertDialogTitle>
          <AlertDialogDescription>
            Enter a name for your branch to save your changes.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex flex-col gap-4">
          <Input
            placeholder="Branch name"
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
          />
          {branchState === BranchState.Loading && (
            <div className="flex items-center gap-2">
              <Loader className="h-4 w-4 animate-spin" />
              <span>Creating branch...</span>
            </div>
          )}
          {branchState === BranchState.BranchSucceeded && (
            <div className="flex flex-col gap-2">
              <span>Branch created successfully!</span>
              <div className="flex items-center gap-2">
                <Input value={cliCommand} readOnly />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => {
                    navigator.clipboard.writeText(cliCommand);
                    toast({
                      title: 'Copied to clipboard',
                      description: 'The command has been copied to your clipboard.',
                    });
                  }}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
          {branchState === BranchState.BranchFailed && (
            <div className="text-red-500">Failed to create branch. Please try again.</div>
          )}
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleSaveBranch}
            disabled={branchState === BranchState.Loading || !branchName.trim()}
          >
            {branchState === BranchState.Loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Save Snapshot
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
