import { PremStatus } from './IPermissions';

export interface IOrg {
  id: string;
  name: string;
  prem_status: PremStatus | null;
  subscription_id: string | null;
  subscription_end_date: number | null;
  subscription_start_date: number | null;
  subscription_cancel_at_period_end: boolean | null;
  current_user_role: string | null;
  current_member_count: number | null;
  max_member_count: number | null;
  current_project_count: number | null;
  max_project_count: number | null;
  paid_member_count?: number | null;
  feature_flags?: {
    [key: string]: boolean;
  };
}
