'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useOrgUsers } from '@/hooks/queries/useOrgUsers';
import { useOrgPendingInvites } from '@/hooks/queries/useOrgInvites';
import {
  inviteOrgMemberAPI,
  revokeOrgInviteAPI,
  removeOrgMemberAPI,
  previewMemberAddCostAPI,
} from '@/lib/api/orgs';
import { toast } from '@/components/ui/use-toast';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { orgPendingInvitesQueryKey } from '@/hooks/queries/useOrgInvites';
import { orgUsersQueryKey } from '@/hooks/queries/useOrgUsers';
import { useOrgDetail, orgDetailQueryKey } from '@/hooks/queries/useOrgDetail';
import { useUser } from '@/hooks/queries/useUser';
import { UserPlus, Mail, X, Crown, Shield, User, Loader2, UserMinus } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { format } from 'date-fns';
import type { IOrgInviteWithEmails } from '@/lib/api/orgs';

interface MembersListProps {
  orgId: string;
  canManage: boolean;
  onLicenseChange?: () => void;
  seatCount?: number;
  pricePerSeat?: number;
  billingInterval?: string;
  currentPeriodStart?: string;
  currentPeriodEnd?: string;
}

export function MembersList({
  orgId,
  canManage,
  onLicenseChange,
  seatCount,
  pricePerSeat,
  billingInterval,
  currentPeriodStart,
  currentPeriodEnd,
}: MembersListProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: currentUser } = useUser();
  const { data: orgDetail, isLoading: isLoadingOrgDetail } = useOrgDetail(orgId);
  const { data: orgUsers, isLoading: isLoadingUsers } = useOrgUsers(orgId, orgDetail);
  const { data: pendingInvites, isLoading: isLoadingInvites } = useOrgPendingInvites(orgId);

  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [billingWarningOpen, setBillingWarningOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'developer' | 'admin'>('developer');

  const [memberToRemove, setMemberToRemove] = useState<{ id: string; email: string } | null>(null);

  const { data: previewCosts, isLoading: isLoadingPreviewCosts } = useQuery({
    queryKey: ['preview-member-cost', orgId],
    queryFn: () => previewMemberAddCostAPI(orgId),
    enabled: billingWarningOpen && !!orgDetail?.subscription_id,
    staleTime: 30000,
  });

  const inviteMutation = useMutation({
    mutationFn: (params: { email: string; role: 'developer' | 'admin' }) =>
      inviteOrgMemberAPI(orgId, params),
    onSuccess: (response) => {
      if (response?.success) {
        toast({
          title: 'Invitation sent',
          description: `Successfully invited ${inviteEmail} to the organization`,
        });
        setInviteEmail('');
        setInviteRole('developer');
        setInviteDialogOpen(false);
        queryClient.invalidateQueries({ queryKey: orgPendingInvitesQueryKey(orgId) });
      } else {
        toast({
          title: 'Failed to send invitation',
          description: response?.message || 'An error occurred',
          variant: 'destructive',
        });
      }
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to send invitation',
        description: error.message || 'An error occurred',
        variant: 'destructive',
      });
    },
  });

  const revokeInviteMutation = useMutation({
    mutationFn: (email: string) => revokeOrgInviteAPI(orgId, email),
    onSuccess: () => {
      toast({
        title: 'Invitation revoked',
        description: 'The invitation has been successfully revoked',
      });
      queryClient.invalidateQueries({ queryKey: orgPendingInvitesQueryKey(orgId) });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to revoke invitation',
        description: error.message || 'An error occurred',
        variant: 'destructive',
      });
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: async (userId: string) => {
      const userToRemove = orgUsers?.find((user) => user.user_id === userId);
      const wasLicensed = userToRemove?.is_paid || false;

      const response = await removeOrgMemberAPI(orgId, { user_id: userId });

      return { response, wasLicensed, userId };
    },
    onMutate: async (userId: string) => {
      await queryClient.cancelQueries({ queryKey: orgUsersQueryKey(orgId) });
      await queryClient.cancelQueries({ queryKey: orgDetailQueryKey(orgId) });

      const previousOrgUsers = queryClient.getQueryData(orgUsersQueryKey(orgId));
      const previousOrgDetail = queryClient.getQueryData(orgDetailQueryKey(orgId));

      if (previousOrgUsers) {
        queryClient.setQueryData(
          orgUsersQueryKey(orgId),
          (old: any[]) => old?.filter((user) => user.user_id !== userId) || [],
        );
      }

      if (previousOrgDetail) {
        queryClient.setQueryData(orgDetailQueryKey(orgId), (old: any) => {
          if (!old) return old;
          return {
            ...old,
            member_count: Math.max((old.member_count || 1) - 1, 0),
          };
        });
      }

      return { previousOrgUsers, previousOrgDetail };
    },
    onSuccess: async ({ response, wasLicensed }, userId, context) => {
      if (response?.success) {
        toast({
          title: 'Member removed',
          description: 'Successfully removed member from the organization',
        });

        await new Promise((resolve) => setTimeout(resolve, 500));

        await Promise.all([
          queryClient.refetchQueries({ queryKey: orgDetailQueryKey(orgId) }),
          queryClient.refetchQueries({ queryKey: orgUsersQueryKey(orgId) }),
          queryClient.refetchQueries({ queryKey: orgPendingInvitesQueryKey(orgId) }),
        ]);

        if (wasLicensed && orgDetail?.subscription_id) {
          toast({
            title: 'Updating subscription',
            description: 'Adjusting your billing for the removed member...',
          });
        }

        onLicenseChange?.();
      } else {
        if (context?.previousOrgUsers) {
          queryClient.setQueryData(orgUsersQueryKey(orgId), context.previousOrgUsers);
        }
        if (context?.previousOrgDetail) {
          queryClient.setQueryData(orgDetailQueryKey(orgId), context.previousOrgDetail);
        }

        toast({
          title: 'Failed to remove member',
          description: response?.message || 'An error occurred',
          variant: 'destructive',
        });
      }
      setMemberToRemove(null);
    },
    onError: (error: any, userId, context) => {
      if (context?.previousOrgUsers) {
        queryClient.setQueryData(orgUsersQueryKey(orgId), context.previousOrgUsers);
      }
      if (context?.previousOrgDetail) {
        queryClient.setQueryData(orgDetailQueryKey(orgId), context.previousOrgDetail);
      }

      toast({
        title: 'Failed to remove member',
        description: error.message || 'An error occurred',
        variant: 'destructive',
      });
      setMemberToRemove(null);
    },
  });

  const handleInviteUser = () => {
    if (!inviteEmail.trim()) {
      toast({
        title: 'Email required',
        description: 'Please enter an email address',
        variant: 'destructive',
      });
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(inviteEmail)) {
      toast({
        title: 'Invalid email',
        description: 'Please enter a valid email address',
        variant: 'destructive',
      });
      return;
    }

    setBillingWarningOpen(true);
  };

  const handleConfirmInvite = () => {
    setBillingWarningOpen(false);
    inviteMutation.mutate({ email: inviteEmail, role: inviteRole });
  };

  const handleDialogClose = (open: boolean) => {
    setInviteDialogOpen(open);
    if (!open) {
      setInviteEmail('');
      setInviteRole('developer');
    }
  };

  const handleRemoveMember = (userId: string, userEmail: string) => {
    setMemberToRemove({ id: userId, email: userEmail });
  };

  const handleConfirmRemove = () => {
    if (memberToRemove) {
      removeMemberMutation.mutate(memberToRemove.id);
    }
  };

  const getRemainingBillingPeriod = () => {
    if (!currentPeriodEnd) return 'the remainder of the subscription period';

    const endDate = new Date(currentPeriodEnd);
    endDate.setHours(0, 0, 0, 0);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const timeDiff = endDate.getTime() - today.getTime();
    const daysRemaining = Math.floor(timeDiff / (1000 * 60 * 60 * 24));

    if (daysRemaining <= 0) return 'the next billing period';
    if (daysRemaining === 1) return '1 day';
    return `${daysRemaining} days`;
  };

  const getProratedAmount = () => {
    if (!pricePerSeat || !currentPeriodEnd) return pricePerSeat || 0;

    const endDate = new Date(currentPeriodEnd);
    endDate.setHours(0, 0, 0, 0);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let totalDays = 30;

    if (currentPeriodStart) {
      const startDate = new Date(currentPeriodStart);
      startDate.setHours(0, 0, 0, 0);
      totalDays = Math.floor((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    } else {
      if (billingInterval === 'year' || billingInterval === 'yr') {
        totalDays = 365;
      }
    }

    const timeDiff = endDate.getTime() - today.getTime();
    const daysRemaining = Math.max(0, Math.floor(timeDiff / (1000 * 60 * 60 * 24)));

    const proratedAmount = (pricePerSeat * daysRemaining) / totalDays;

    return Math.round(proratedAmount * 100) / 100;
  };

  const handleRevokeInvite = (email: string) => {
    revokeInviteMutation.mutate(email);
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'owner':
        return <Crown className="h-4 w-4 text-amber-500" />;
      case 'admin':
        return <Shield className="h-4 w-4 text-blue-500" />;
      default:
        return <User className="h-4 w-4 text-gray-500" />;
    }
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'owner':
        return 'default';
      case 'admin':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  if (isLoadingOrgDetail || isLoadingUsers || isLoadingInvites) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-1">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
                <Skeleton className="h-8 w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">Team Members</CardTitle>
            {seatCount !== undefined && pricePerSeat !== undefined && (
              <div className="pt-2 text-sm text-muted-foreground">
                {seatCount} seat{seatCount !== 1 ? 's' : ''} @ ${pricePerSeat}/
                {billingInterval || 'mo'} each
              </div>
            )}
          </div>
          {canManage && (
            <Dialog open={inviteDialogOpen} onOpenChange={handleDialogClose}>
              <DialogTrigger asChild>
                <Button size="sm" className="flex items-center gap-2">
                  <UserPlus className="h-4 w-4" />
                  Invite Member
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite Team Member</DialogTitle>
                  <DialogDescription>
                    Send an invitation to join this organization
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="colleague@company.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleInviteUser();
                        }
                      }}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="role">Role</Label>
                    <Select
                      value={inviteRole}
                      defaultValue="developer"
                      onValueChange={(value: 'developer' | 'admin') => setInviteRole(value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="developer">Developer</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button onClick={handleInviteUser} disabled={inviteMutation.isPending}>
                    {inviteMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      'Send Invitation'
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          {pendingInvites && pendingInvites.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-muted-foreground">Pending Invitations</h4>
              <div className="space-y-2">
                {pendingInvites.map((invite, index) => (
                  <div
                    key={`${invite.invitee_email}-${index}`}
                    className="flex items-center justify-between rounded-lg bg-muted/50 p-3"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-100">
                        <Mail className="h-4 w-4 text-orange-600" />
                      </div>
                      <div>
                        <div className="font-medium">{invite.invitee_email}</div>
                        <div className="text-sm text-muted-foreground">
                          Invited{' '}
                          {invite.created_at
                            ? new Date(invite.created_at).toLocaleDateString()
                            : 'Recently'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="border-orange-200 text-orange-600">
                        Pending
                      </Badge>
                      {canManage && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRevokeInvite(invite.invitee_email)}
                          disabled={revokeInviteMutation.isPending}
                        >
                          {revokeInviteMutation.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <X className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Current Members</h4>
            <div className="space-y-2">
              {orgUsers?.map((user) => {
                const isCurrentUser = currentUser?.id === user.user_id;
                const canRemove = canManage && user.role !== 'owner' && !isCurrentUser;

                return (
                  <div
                    key={user.user_id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100">
                        {getRoleIcon(user.role)}
                      </div>
                      <div>
                        <div className="font-medium">
                          {user.user_email}
                          {isCurrentUser && (
                            <span className="text-sm text-muted-foreground"> (You)</span>
                          )}
                        </div>
                        <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                          <Badge variant={getRoleBadgeVariant(user.role)} className="text-xs">
                            {user.role}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    {canRemove && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveMember(user.user_id, user.user_email)}
                        className="text-destructive hover:text-destructive"
                      >
                        <UserMinus className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>
      <AlertDialog open={billingWarningOpen} onOpenChange={setBillingWarningOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Billing Notice</AlertDialogTitle>
            <AlertDialogDescription>
              Review the billing impact before adding this new team member to your organization.
            </AlertDialogDescription>
            <div className="text-sm text-slate-500 dark:text-slate-400">
              {isLoadingPreviewCosts ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span className="ml-2">Calculating costs...</span>
                </div>
              ) : previewCosts ? (
                <div className="space-y-3">
                  <p>When this user accepts the invite, you will be charged:</p>
                  <div className="space-y-2 rounded-lg bg-blue-50 p-4 dark:bg-blue-950/20">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Immediate charge:</span>
                      <span className="font-semibold">
                        {previewCosts.currency.toUpperCase() === 'USD'
                          ? '$'
                          : previewCosts.currency.toUpperCase()}
                        {previewCosts.immediate_charge.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {previewCosts.immediate_charge > 0 ? (
                        <>
                          For the remainder of this billing period{' '}
                          {previewCosts.period_end &&
                            `(until ${format(new Date(previewCosts.period_end), 'MMM d, yyyy')})`}
                        </>
                      ) : (
                        'No immediate charge for this billing period'
                      )}
                    </div>
                  </div>
                  <div className="space-y-2 rounded-lg bg-gray-50 p-4 dark:bg-gray-950/20">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">At renewal:</span>
                      <span className="font-semibold">
                        {previewCosts.currency.toUpperCase() === 'USD'
                          ? '$'
                          : previewCosts.currency.toUpperCase()}
                        {previewCosts.next_period_charge.toFixed(2)}/{previewCosts.billing_interval}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Full seat price starting next billing period
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <p>When this user accepts the invite, you will be charged:</p>
                  <div className="space-y-2 rounded-lg bg-blue-50 p-4 dark:bg-blue-950/20">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Immediate charge:</span>
                      <span className="font-semibold">${getProratedAmount().toFixed(2)}</span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      For {getRemainingBillingPeriod()} (until{' '}
                      {currentPeriodEnd
                        ? format(new Date(currentPeriodEnd), 'MMM d, yyyy')
                        : 'period end'}
                      )
                    </div>
                  </div>
                  <div className="space-y-2 rounded-lg bg-gray-50 p-4 dark:bg-gray-950/20">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">At renewal:</span>
                      <span className="font-semibold">
                        ${pricePerSeat || 40}/{billingInterval || 'mo'}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Full seat price starting next billing period
                    </div>
                  </div>
                </div>
              )}
            </div>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmInvite} disabled={isLoadingPreviewCosts}>
              Confirm & Send Invite
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog
        open={!!memberToRemove}
        onOpenChange={(open) => !open && setMemberToRemove(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Team Member</AlertDialogTitle>
            <AlertDialogDescription>
              This action will permanently remove the team member from your organization and cannot
              be undone.
            </AlertDialogDescription>
            <div className="text-sm text-slate-500 dark:text-slate-400">
              {(() => {
                const userToRemove = orgUsers?.find((user) => user.user_id === memberToRemove?.id);
                const isLicensed = userToRemove?.is_paid || false;

                return (
                  <div className="space-y-3">
                    <p>
                      Are you sure you want to remove <strong>{memberToRemove?.email}</strong> from
                      this organization? They will lose access immediately.
                    </p>
                    {isLicensed && pricePerSeat && (
                      <div className="space-y-2 rounded-lg bg-blue-50 p-4 dark:bg-blue-950/20">
                        <p className="text-sm font-medium">Billing Impact:</p>
                        <ul className="space-y-1 text-sm text-muted-foreground">
                          <li>
                            • You'll stop being charged ${pricePerSeat}/{billingInterval || 'mo'}{' '}
                            for this seat
                          </li>
                          <li>• The change takes effect at your next billing period</li>
                          <li>• No refund for the current billing period</li>
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmRemove}
              disabled={removeMemberMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {removeMemberMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Removing...
                </>
              ) : (
                'Remove Member'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
