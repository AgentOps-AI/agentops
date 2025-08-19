export interface IUser {
  id: string;
  email?: string | null;
  full_name?: string | null;
  avatar_url?: string | null;
  billing_address?: Record<string, any> | null;
  payment_method?: Record<string, any> | null;
  survey_is_complete?: boolean | null;
}
