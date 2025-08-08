'use client';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from '@/components/ui/use-toast';
import { fetchAuthenticatedApi } from '@/lib/api-client';
import { useUser, userQueryKey } from '@/hooks/queries/useUser';
import { useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export default function AccountForm() {
  const { data: userData, isLoading: userDataLoading } = useUser();
  const queryClient = useQueryClient();
  const [name, setName] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (userData) {
      setName(userData.full_name ?? '');
    }
  }, [userData]);

  async function handleUpdateAccount() {
    setLoading(true);
    try {
      await fetchAuthenticatedApi('/opsboard/users/update', {
        method: 'POST',
        body: JSON.stringify({ full_name: name }),
      });
      queryClient.invalidateQueries({ queryKey: userQueryKey });
      toast({ title: '✅ Account Updated Successfully' });
    } catch (error: any) {
      console.error('Update Account Error:', error);
      toast({ title: '❌ Update Failed', description: error.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }

  if (userDataLoading) {
    return <div>Loading account details...</div>;
  }

  return (
    <div className="grid gap-2">
      <Label htmlFor="name" className="text-sm font-normal text-gray-500">
        Username
      </Label>
      <Input
        id="name"
        type="text"
        data-testid="account-form-input-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Your name"
        disabled={loading}
      />
      <Button
        className="mt-2 w-fit"
        data-testid="account-form-button-update"
        disabled={loading || name === (userData?.full_name ?? '')}
        onClick={handleUpdateAccount}
      >
        {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        Update Account
      </Button>
    </div>
  );
}
