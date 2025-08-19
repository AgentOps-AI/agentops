export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  public: {
    Tables: {
      actions: {
        Row: {
          action_type: string | null;
          agent_id: string;
          end_timestamp: string;
          id: string;
          init_timestamp: string;
          logs: string | null;
          params: string | null;
          returns: string | null;
          screenshot: string | null;
          session_id: string;
        };
        Insert: {
          action_type?: string | null;
          agent_id: string;
          end_timestamp: string;
          id?: string;
          init_timestamp: string;
          logs?: string | null;
          params?: string | null;
          returns?: string | null;
          screenshot?: string | null;
          session_id: string;
        };
        Update: {
          action_type?: string | null;
          agent_id?: string;
          end_timestamp?: string;
          id?: string;
          init_timestamp?: string;
          logs?: string | null;
          params?: string | null;
          returns?: string | null;
          screenshot?: string | null;
          session_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'actions_agent_id_fkey';
            columns: ['agent_id'];
            isOneToOne: false;
            referencedRelation: 'agents';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'actions_session_id_fkey';
            columns: ['session_id'];
            isOneToOne: false;
            referencedRelation: 'sessions';
            referencedColumns: ['id'];
          },
        ];
      };
      agents: {
        Row: {
          id: string;
          logs: string | null;
          name: string | null;
          session_id: string;
        };
        Insert: {
          id: string;
          logs?: string | null;
          name?: string | null;
          session_id: string;
        };
        Update: {
          id?: string;
          logs?: string | null;
          name?: string | null;
          session_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'agents_session_id_fkey';
            columns: ['session_id'];
            isOneToOne: false;
            referencedRelation: 'sessions';
            referencedColumns: ['id'];
          },
        ];
      };
      customers: {
        Row: {
          id: string;
          stripe_customer_id: string | null;
        };
        Insert: {
          id: string;
          stripe_customer_id?: string | null;
        };
        Update: {
          id?: string;
          stripe_customer_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: 'customers_id_fkey';
            columns: ['id'];
            isOneToOne: true;
            referencedRelation: 'users';
            referencedColumns: ['id'];
          },
        ];
      };
      developer_errors: {
        Row: {
          api_key: string;
          host_env: Json | null;
          id: number;
          message: string | null;
          sdk_version: string | null;
          session_id: string | null;
          stack_trace: string | null;
          timestamp: string | null;
          type: string | null;
        };
        Insert: {
          api_key: string;
          host_env?: Json | null;
          id?: number;
          message?: string | null;
          sdk_version?: string | null;
          session_id?: string | null;
          stack_trace?: string | null;
          timestamp?: string | null;
          type?: string | null;
        };
        Update: {
          api_key?: string;
          host_env?: Json | null;
          id?: number;
          message?: string | null;
          sdk_version?: string | null;
          session_id?: string | null;
          stack_trace?: string | null;
          timestamp?: string | null;
          type?: string | null;
        };
        Relationships: [];
      };
      errors: {
        Row: {
          code: string | null;
          details: string | null;
          error_type: string | null;
          id: number;
          logs: string | null;
          session_id: string;
          timestamp: string;
          trigger_event_id: string | null;
          trigger_event_type: Database['public']['Enums']['trigger_event_type'] | null;
        };
        Insert: {
          code?: string | null;
          details?: string | null;
          error_type?: string | null;
          id?: number;
          logs?: string | null;
          session_id: string;
          timestamp: string;
          trigger_event_id?: string | null;
          trigger_event_type?: Database['public']['Enums']['trigger_event_type'] | null;
        };
        Update: {
          code?: string | null;
          details?: string | null;
          error_type?: string | null;
          id?: number;
          logs?: string | null;
          session_id?: string;
          timestamp?: string;
          trigger_event_id?: string | null;
          trigger_event_type?: Database['public']['Enums']['trigger_event_type'] | null;
        };
        Relationships: [
          {
            foreignKeyName: 'errors_session_id_fkey';
            columns: ['session_id'];
            isOneToOne: false;
            referencedRelation: 'sessions';
            referencedColumns: ['id'];
          },
        ];
      };
      llms: {
        Row: {
          agent_id: string | null;
          completion: Json | null;
          completion_tokens: number | null;
          cost: number | null;
          end_timestamp: string;
          id: string;
          init_timestamp: string;
          model: string | null;
          params: string | null;
          prompt: Json | null;
          prompt_tokens: number | null;
          promptarmor_flag: boolean | null;
          returns: string | null;
          session_id: string;
          thread_id: string | null;
        };
        Insert: {
          agent_id?: string | null;
          completion?: Json | null;
          completion_tokens?: number | null;
          cost?: number | null;
          end_timestamp: string;
          id?: string;
          init_timestamp: string;
          model?: string | null;
          params?: string | null;
          prompt?: Json | null;
          prompt_tokens?: number | null;
          promptarmor_flag?: boolean | null;
          returns?: string | null;
          session_id: string;
          thread_id?: string | null;
        };
        Update: {
          agent_id?: string | null;
          completion?: Json | null;
          completion_tokens?: number | null;
          cost?: number | null;
          end_timestamp?: string;
          id?: string;
          init_timestamp?: string;
          model?: string | null;
          params?: string | null;
          prompt?: Json | null;
          prompt_tokens?: number | null;
          promptarmor_flag?: boolean | null;
          returns?: string | null;
          session_id?: string;
          thread_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: 'llms_session_id_fkey';
            columns: ['session_id'];
            isOneToOne: false;
            referencedRelation: 'sessions';
            referencedColumns: ['id'];
          },
        ];
      };
      org_invites: {
        Row: {
          inviter_id: string;
          invitee_email: string;
          org_id: string;
          org_name: string;
          role: Database['public']['Enums']['org_roles'];
          inviter: string;
          created_at: string | null;
        };
        Insert: {
          inviter_id: string;
          invitee_email: string;
          org_id: string;
          org_name: string;
          role: Database['public']['Enums']['org_roles'];
          inviter: string;
          created_at?: string | null;
        };
        Update: {
          inviter_id?: string;
          invitee_email?: string;
          org_id?: string;
          org_name?: string;
          role?: Database['public']['Enums']['org_roles'];
          inviter?: string;
          created_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: 'org_invites_org_id_fkey';
            columns: ['org_id'];
            isOneToOne: false;
            referencedRelation: 'orgs';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'org_invites_inviter_id_fkey';
            columns: ['inviter_id'];
            isOneToOne: false;
            referencedRelation: 'users';
            referencedColumns: ['id'];
          },
        ];
      };
      orgs: {
        Row: {
          id: string;
          name: string;
          prem_status: Database['public']['Enums']['prem_status'];
          subscription_id: string | null;
        };
        Insert: {
          id?: string;
          name: string;
          prem_status?: Database['public']['Enums']['prem_status'];
          subscription_id?: string | null;
        };
        Update: {
          id?: string;
          name?: string;
          prem_status?: Database['public']['Enums']['prem_status'];
          subscription_id?: string | null;
        };
        Relationships: [];
      };
      prices: {
        Row: {
          active: boolean | null;
          currency: string | null;
          description: string | null;
          id: string;
          interval: Database['public']['Enums']['pricing_plan_interval'] | null;
          interval_count: number | null;
          metadata: Json | null;
          product_id: string | null;
          trial_period_days: number | null;
          type: Database['public']['Enums']['pricing_type'] | null;
          unit_amount: number | null;
        };
        Insert: {
          active?: boolean | null;
          currency?: string | null;
          description?: string | null;
          id: string;
          interval?: Database['public']['Enums']['pricing_plan_interval'] | null;
          interval_count?: number | null;
          metadata?: Json | null;
          product_id?: string | null;
          trial_period_days?: number | null;
          type?: Database['public']['Enums']['pricing_type'] | null;
          unit_amount?: number | null;
        };
        Update: {
          active?: boolean | null;
          currency?: string | null;
          description?: string | null;
          id?: string;
          interval?: Database['public']['Enums']['pricing_plan_interval'] | null;
          interval_count?: number | null;
          metadata?: Json | null;
          product_id?: string | null;
          trial_period_days?: number | null;
          type?: Database['public']['Enums']['pricing_type'] | null;
          unit_amount?: number | null;
        };
        Relationships: [
          {
            foreignKeyName: 'prices_product_id_fkey';
            columns: ['product_id'];
            isOneToOne: false;
            referencedRelation: 'products';
            referencedColumns: ['id'];
          },
        ];
      };
      products: {
        Row: {
          active: boolean | null;
          description: string | null;
          id: string;
          image: string | null;
          metadata: Json | null;
          name: string | null;
        };
        Insert: {
          active?: boolean | null;
          description?: string | null;
          id: string;
          image?: string | null;
          metadata?: Json | null;
          name?: string | null;
        };
        Update: {
          active?: boolean | null;
          description?: string | null;
          id?: string;
          image?: string | null;
          metadata?: Json | null;
          name?: string | null;
        };
        Relationships: [];
      };
      projects: {
        Row: {
          api_key: string;
          environment: Database['public']['Enums']['environment'];
          id: string;
          name: string;
          org_id: string;
        };
        Insert: {
          api_key?: string;
          environment?: Database['public']['Enums']['environment'];
          id?: string;
          name: string;
          org_id: string;
        };
        Update: {
          api_key?: string;
          environment?: Database['public']['Enums']['environment'];
          id?: string;
          name?: string;
          org_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'projects_org_id_fkey';
            columns: ['org_id'];
            isOneToOne: false;
            referencedRelation: 'orgs';
            referencedColumns: ['id'];
          },
        ];
      };
      sessions: {
        Row: {
          end_state: Database['public']['Enums']['end_state'] | null;
          end_state_reason: string | null;
          end_timestamp: string | null;
          host_env: Json | null;
          id: string;
          init_timestamp: string;
          project_id: string;
          project_id_secondary: string | null;
          tags: string | null;
          video: string | null;
        };
        Insert: {
          end_state?: Database['public']['Enums']['end_state'] | null;
          end_state_reason?: string | null;
          end_timestamp?: string | null;
          host_env?: Json | null;
          id: string;
          init_timestamp: string;
          project_id: string;
          project_id_secondary?: string | null;
          tags?: string | null;
          video?: string | null;
        };
        Update: {
          end_state?: Database['public']['Enums']['end_state'] | null;
          end_state_reason?: string | null;
          end_timestamp?: string | null;
          host_env?: Json | null;
          id?: string;
          init_timestamp?: string;
          project_id?: string;
          project_id_secondary?: string | null;
          tags?: string | null;
          video?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: 'sessions_project_id_fkey';
            columns: ['project_id'];
            isOneToOne: false;
            referencedRelation: 'projects';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'sessions_project_id_secondary_fkey';
            columns: ['project_id_secondary'];
            isOneToOne: false;
            referencedRelation: 'projects';
            referencedColumns: ['id'];
          },
        ];
      };
      stats: {
        Row: {
          completion_tokens: number;
          cost: number | null;
          errors: number;
          events: number;
          prompt_tokens: number;
          session_id: string;
        };
        Insert: {
          completion_tokens?: number;
          cost?: number | null;
          errors?: number;
          events?: number;
          prompt_tokens?: number;
          session_id: string;
        };
        Update: {
          completion_tokens?: number;
          cost?: number | null;
          errors?: number;
          events?: number;
          prompt_tokens?: number;
          session_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'stats_session_id_fkey';
            columns: ['session_id'];
            isOneToOne: true;
            referencedRelation: 'sessions';
            referencedColumns: ['id'];
          },
        ];
      };
      subscriptions: {
        Row: {
          cancel_at: string | null;
          cancel_at_period_end: boolean | null;
          canceled_at: string | null;
          created: string;
          current_period_end: string;
          current_period_start: string;
          ended_at: string | null;
          id: string;
          metadata: Json | null;
          price_id: string | null;
          quantity: number | null;
          status: Database['public']['Enums']['subscription_status'] | null;
          trial_end: string | null;
          trial_start: string | null;
          user_id: string;
        };
        Insert: {
          cancel_at?: string | null;
          cancel_at_period_end?: boolean | null;
          canceled_at?: string | null;
          created?: string;
          current_period_end?: string;
          current_period_start?: string;
          ended_at?: string | null;
          id: string;
          metadata?: Json | null;
          price_id?: string | null;
          quantity?: number | null;
          status?: Database['public']['Enums']['subscription_status'] | null;
          trial_end?: string | null;
          trial_start?: string | null;
          user_id: string;
        };
        Update: {
          cancel_at?: string | null;
          cancel_at_period_end?: boolean | null;
          canceled_at?: string | null;
          created?: string;
          current_period_end?: string;
          current_period_start?: string;
          ended_at?: string | null;
          id?: string;
          metadata?: Json | null;
          price_id?: string | null;
          quantity?: number | null;
          status?: Database['public']['Enums']['subscription_status'] | null;
          trial_end?: string | null;
          trial_start?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'subscriptions_price_id_fkey';
            columns: ['price_id'];
            isOneToOne: false;
            referencedRelation: 'prices';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'subscriptions_user_id_fkey';
            columns: ['user_id'];
            isOneToOne: false;
            referencedRelation: 'users';
            referencedColumns: ['id'];
          },
        ];
      };
      threads: {
        Row: {
          agent_id: string;
          id: string;
          session_id: string;
        };
        Insert: {
          agent_id: string;
          id: string;
          session_id: string;
        };
        Update: {
          agent_id?: string;
          id?: string;
          session_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'threads_agent_id_fkey';
            columns: ['agent_id'];
            isOneToOne: false;
            referencedRelation: 'agents';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'threads_session_id_fkey';
            columns: ['session_id'];
            isOneToOne: false;
            referencedRelation: 'sessions';
            referencedColumns: ['id'];
          },
        ];
      };
      tools: {
        Row: {
          agent_id: string;
          end_timestamp: string;
          id: string;
          init_timestamp: string;
          logs: string | null;
          name: string | null;
          params: string | null;
          returns: string | null;
          session_id: string;
        };
        Insert: {
          agent_id: string;
          end_timestamp: string;
          id?: string;
          init_timestamp: string;
          logs?: string | null;
          name?: string | null;
          params?: string | null;
          returns?: string | null;
          session_id: string;
        };
        Update: {
          agent_id?: string;
          end_timestamp?: string;
          id?: string;
          init_timestamp?: string;
          logs?: string | null;
          name?: string | null;
          params?: string | null;
          returns?: string | null;
          session_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'tools_agent_id_fkey';
            columns: ['agent_id'];
            isOneToOne: false;
            referencedRelation: 'agents';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'tools_session_id_fkey';
            columns: ['session_id'];
            isOneToOne: false;
            referencedRelation: 'sessions';
            referencedColumns: ['id'];
          },
        ];
      };
      ttd: {
        Row: {
          branch_name: string;
          completion: Json | null;
          completion_tokens: number | null;
          created_at: string;
          id: string;
          llm_id: string;
          model: string | null;
          params: string | null;
          prompt: Json | null;
          prompt_tokens: number | null;
          returns: string | null;
          session_id: string;
          ttd_id: string;
        };
        Insert: {
          branch_name?: string;
          completion?: Json | null;
          completion_tokens?: number | null;
          created_at?: string;
          id?: string;
          llm_id: string;
          model?: string | null;
          params?: string | null;
          prompt?: Json | null;
          prompt_tokens?: number | null;
          returns?: string | null;
          session_id: string;
          ttd_id: string;
        };
        Update: {
          branch_name?: string;
          completion?: Json | null;
          completion_tokens?: number | null;
          created_at?: string;
          id?: string;
          llm_id?: string;
          model?: string | null;
          params?: string | null;
          prompt?: Json | null;
          prompt_tokens?: number | null;
          returns?: string | null;
          session_id?: string;
          ttd_id?: string;
        };
        Relationships: [];
      };
      user_orgs: {
        Row: {
          org_id: string;
          role: Database['public']['Enums']['org_roles'];
          user_email: string | null;
          user_id: string;
        };
        Insert: {
          org_id: string;
          role?: Database['public']['Enums']['org_roles'];
          user_email?: string | null;
          user_id: string;
        };
        Update: {
          org_id?: string;
          role?: Database['public']['Enums']['org_roles'];
          user_email?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'user_orgs_org_id_fkey';
            columns: ['org_id'];
            isOneToOne: false;
            referencedRelation: 'orgs';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'user_orgs_users_id_fkey';
            columns: ['user_id'];
            isOneToOne: false;
            referencedRelation: 'users';
            referencedColumns: ['id'];
          },
        ];
      };
      users: {
        Row: {
          avatar_url: string | null;
          billing_address: Json | null;
          full_name: string | null;
          id: string;
          payment_method: Json | null;
          email: string | null;
          survey_is_complete: boolean;
        };
        Insert: {
          avatar_url?: string | null;
          billing_address?: Json | null;
          full_name?: string | null;
          id: string;
          payment_method?: Json | null;
          email: string | null;
          survey_is_complete: boolean;
        };
        Update: {
          avatar_url?: string | null;
          billing_address?: Json | null;
          full_name?: string | null;
          id?: string;
          payment_method?: Json | null;
          email?: string | null;
          survey_is_complete: boolean;
        };
        Relationships: [
          {
            foreignKeyName: 'users_id_fkey';
            columns: ['id'];
            isOneToOne: true;
            referencedRelation: 'users';
            referencedColumns: ['id'];
          },
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      accept_org_invite: {
        Args: {
          org_id: string;
        };
        Returns: undefined;
      };
      create_new_org: {
        Args: {
          org_name: string;
        };
        Returns: string;
      };
      create_org_invite: {
        Args: {
          invited_email: string;
          org_id: string;
          role: Database['public']['Enums']['org_roles'];
        };
        Returns: undefined;
      };
      get_ttd: {
        Args: {
          ttd_id: string;
        };
        Returns: {
          branch_name: string;
          completion: Json | null;
          completion_tokens: number | null;
          created_at: string;
          id: string;
          llm_id: string;
          model: string | null;
          params: string | null;
          prompt: Json | null;
          prompt_tokens: number | null;
          returns: string | null;
          session_id: string;
          ttd_id: string;
        }[];
      };
      rename_org: {
        Args: {
          org_id: string;
          org_name: string;
        };
        Returns: undefined;
      };
      rotate_project_api_key: {
        Args: {
          project_id: string;
        };
        Returns: string;
      };
      transfer_org_ownership: {
        Args: {
          org_id: string;
          new_owner_id: string;
        };
        Returns: undefined;
      };
      user_aal: {
        Args: Record<PropertyKey, never>;
        Returns: string[];
      };
      user_belongs_to_org: {
        Args: {
          org_id: string;
        };
        Returns: boolean;
      };
      user_is_org_admin: {
        Args: {
          org_id: string;
        };
        Returns: boolean;
      };
      user_is_org_owner: {
        Args: {
          org_id: string;
        };
        Returns: boolean;
      };
      user_projects: {
        Args: Record<PropertyKey, never>;
        Returns: string[];
      };
    };
    Enums: {
      end_state: 'Success' | 'Fail' | 'Indeterminate';
      environment: 'production' | 'staging' | 'development' | 'community';
      org_roles: 'owner' | 'admin' | 'developer' | 'business_user';
      prem_status: 'free' | 'pro' | 'enterprise';
      pricing_plan_interval: 'day' | 'week' | 'month' | 'year';
      pricing_type: 'one_time' | 'recurring';
      subscription_status:
        | 'trialing'
        | 'active'
        | 'canceled'
        | 'incomplete'
        | 'incomplete_expired'
        | 'past_due'
        | 'unpaid'
        | 'paused';
      trigger_event_type: 'actions' | 'llms' | 'tools';
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type PublicSchema = Database[Extract<keyof Database, 'public'>];

export type Tables<
  PublicTableNameOrOptions extends
    | keyof (PublicSchema['Tables'] & PublicSchema['Views'])
    | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof (Database[PublicTableNameOrOptions['schema']]['Tables'] &
        Database[PublicTableNameOrOptions['schema']]['Views'])
    : never = never,
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? (Database[PublicTableNameOrOptions['schema']]['Tables'] &
      Database[PublicTableNameOrOptions['schema']]['Views'])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : PublicTableNameOrOptions extends keyof (PublicSchema['Tables'] & PublicSchema['Views'])
    ? (PublicSchema['Tables'] & PublicSchema['Views'])[PublicTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  PublicTableNameOrOptions extends keyof PublicSchema['Tables'] | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicTableNameOrOptions['schema']]['Tables']
    : never = never,
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? Database[PublicTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : PublicTableNameOrOptions extends keyof PublicSchema['Tables']
    ? PublicSchema['Tables'][PublicTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  PublicTableNameOrOptions extends keyof PublicSchema['Tables'] | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicTableNameOrOptions['schema']]['Tables']
    : never = never,
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? Database[PublicTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : PublicTableNameOrOptions extends keyof PublicSchema['Tables']
    ? PublicSchema['Tables'][PublicTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  PublicEnumNameOrOptions extends keyof PublicSchema['Enums'] | { schema: keyof Database },
  EnumName extends PublicEnumNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicEnumNameOrOptions['schema']]['Enums']
    : never = never,
> = PublicEnumNameOrOptions extends { schema: keyof Database }
  ? Database[PublicEnumNameOrOptions['schema']]['Enums'][EnumName]
  : PublicEnumNameOrOptions extends keyof PublicSchema['Enums']
    ? PublicSchema['Enums'][PublicEnumNameOrOptions]
    : never;
