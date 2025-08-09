import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { IOrg } from '@/types/IOrg';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';
import { cn } from '@/lib/utils';

interface OrganizationSelectorProps {
  orgs: IOrg[];
  selectedOrgId: string | null;
  onOrgChange: (orgId: string) => void;
  className?: string;
}

export function OrganizationSelector({
  orgs,
  selectedOrgId,
  onOrgChange,
  className,
}: OrganizationSelectorProps) {
  const selectedOrg = orgs.find((org) => org.id === selectedOrgId);

  return (
    <div className={cn('flex items-center justify-between gap-4', className)}>
      <div className="flex items-center gap-3">
        <Select value={selectedOrgId || ''} onValueChange={onOrgChange}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Select organization">
              {selectedOrg && (
                <div className="flex items-center gap-2">
                  <span className="font-medium">{selectedOrg.name}</span>
                  <SubscriptionBadge
                    tier={selectedOrg.prem_status}
                    showUpgrade={false}
                    isCancelling={!!selectedOrg.subscription_cancel_at_period_end}
                    cancelDate={selectedOrg.subscription_end_date || undefined}
                    expanded={false}
                  />
                </div>
              )}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {orgs.map((org) => (
              <SelectItem key={org.id} value={org.id}>
                <div className="flex items-center gap-2 py-1">
                  <span className="font-medium">{org.name}</span>
                  <SubscriptionBadge
                    tier={org.prem_status}
                    showUpgrade={false}
                    isCancelling={!!org.subscription_cancel_at_period_end}
                    cancelDate={org.subscription_end_date || undefined}
                    expanded={false}
                  />
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
