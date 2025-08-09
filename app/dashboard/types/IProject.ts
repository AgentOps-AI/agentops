import { IOrg } from './IOrg';

export interface IProject {
  id: string;
  name: string;
  api_key: string;
  org_id: string;
  environment: 'production' | 'staging' | 'development' | 'community';
  org: IOrg;
  trace_count: number;
}

// HostingProject extends Project with deploy-specific fields
export interface IHostingProject extends IProject {
  git_url?: string;
  git_branch?: string;
  entrypoint?: string;
  watch_path?: string;
  user_callback_url?: string;
  github_oath_access_token?: string;
  pack_name?: string;
}
