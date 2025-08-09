-- Enable the "pg_jsonschema" extension
CREATE extension pg_jsonschema WITH schema extensions;

CREATE TYPE pricing_plan_interval AS ENUM ('day', 'week', 'month', 'year');

CREATE TYPE pricing_type AS ENUM ('one_time', 'recurring');

CREATE TYPE subscription_status AS ENUM (
  'trialing',
  'active',
  'canceled',
  'incomplete',
  'incomplete_expired',
  'past_due',
  'unpaid',
  'paused'
);

CREATE TYPE trigger_event_type AS ENUM ('actions', 'llms', 'tools');

CREATE TYPE environment AS ENUM (
  'production',
  'staging',
  'development',
  'community'
);

CREATE TYPE end_state AS ENUM ('Success', 'Fail', 'Indeterminate');

CREATE TABLE public.orgs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL
) tablespace pg_default;

CREATE TABLE public.user_orgs(
  user_id UUID NOT NULL,
  org_id UUID NOT NULL,
  CONSTRAINT user_orgs_pkey PRIMARY KEY (user_id, org_id),
  CONSTRAINT user_orgs_users_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT user_orgs_org_id_fkey FOREIGN KEY (org_id) REFERENCES orgs (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE TABLE public.projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  api_key UUID NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  environment public.environment NOT NULL DEFAULT 'development',
  CONSTRAINT projects_api_key_key UNIQUE (api_key),
  CONSTRAINT projects_org_id_fkey FOREIGN KEY (org_id) REFERENCES orgs (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE INDEX ON public.projects(org_id);

----------------------------------------------------------------------------------------------------
-------------------------- vvv Data coming from client sdk vvv -------------------------------------
----------------------------------------------------------------------------------------------------
-- id is UUID because needs to be passed by client sdk. client can just generate UUID instead of requesting a sequential bigint from the server
-- Not given a generated default value because we want insertion to fail if ommited
CREATE TABLE public.sessions (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL,
  project_id_secondary UUID NULL,
  init_timestamp timestamp WITH time zone NOT NULL,
  end_timestamp timestamp WITH time zone NULL,
  tags text NULL,
  -- TODO: add link to log bucket logs text NULL, 
  end_state public.end_state NULL,
  end_state_reason text NULL,
  video text NULL,
  host_env jsonb NULL,
  CONSTRAINT sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects (id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT sessions_project_id_secondary_fkey FOREIGN KEY (project_id_secondary) REFERENCES projects (id) ON UPDATE CASCADE ON DELETE SET NULL
) tablespace pg_default;

CREATE INDEX ON public.sessions(project_id);
CREATE INDEX ON public.sessions(project_id_secondary);

CREATE TABLE public.agents (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL,
  name text NULL,
  logs text NULL,
  CONSTRAINT agents_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE INDEX ON public.agents(session_id);

CREATE TABLE public.threads (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL,
  agent_id UUID NOT NULL,
  CONSTRAINT threads_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES agents (id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT threads_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE INDEX ON public.threads(session_id);

CREATE TABLE public.stats (
  session_id UUID NOT NULL,
  cost numeric,
  events integer NOT NULL DEFAULT 0,
  prompt_tokens integer NOT NULL DEFAULT 0,
  completion_tokens integer NOT NULL DEFAULT 0,
  errors integer NOT NULL DEFAULT 0,
  CONSTRAINT stats_pkey PRIMARY KEY (session_id),
  CONSTRAINT stats_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE TABLE public.actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  agent_id UUID NOT NULL,
  action_type text NULL,
  logs text NULL,
  screenshot text NULL,
  params text NULL,
  returns text NULL,
  init_timestamp timestamp WITH time zone NOT NULL,
  end_timestamp timestamp WITH time zone NOT NULL,
  CONSTRAINT actions_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT actions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES agents (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE INDEX ON public.actions(session_id);

CREATE TABLE public.llms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  agent_id UUID NULL,
  thread_id UUID NULL,
  prompt jsonb NULL,
  completion jsonb NULL,
  model text NULL,
  prompt_tokens numeric NULL,
  completion_tokens numeric NULL,
  cost numeric NULL,
  promptarmor_flag boolean NULL,
  params text NULL,
  returns text NULL,
  init_timestamp timestamp WITH time zone NOT NULL,
  end_timestamp timestamp WITH time zone NOT NULL,
  CONSTRAINT llms_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE INDEX ON public.llms(session_id);

CREATE TABLE public.tools (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  agent_id UUID NOT NULL,
  name text NULL,
  logs text NULL,
  params text NULL,
  returns text NULL,
  init_timestamp timestamp WITH time zone NOT NULL,
  end_timestamp timestamp WITH time zone NOT NULL,
  CONSTRAINT tools_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT tools_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES agents (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE INDEX ON public.tools(session_id);

CREATE TABLE public.errors (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  session_id UUID NOT NULL,
  trigger_event_id UUID NULL,
  trigger_event_type trigger_event_type NULL,
  error_type text NULL,
  code text NULL,
  details text NULL,
  logs text NULL,
  timestamp timestamp WITH time zone NOT NULL,
  CONSTRAINT errors_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE INDEX ON public.errors(session_id);

CREATE TABLE public.developer_errors (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  api_key UUID NOT NULL,
  sdk_version text NULL,
  type text NULL,
  message text NULL,
  stack_trace text NULL,
  host_env jsonb NULL
);

INSERT INTO storage.buckets (
  id, 
  name, 
  public,
  allowed_mime_types
) VALUES (
  'screenshots', -- id
  'screenshots', -- name
  false,         -- public
  ARRAY['image/*']  -- allowed_mime_types
) ON CONFLICT DO NOTHING; -- Buckets do not get deleted on db reset

INSERT INTO storage.buckets (
  id, 
  name, 
  public
) VALUES (
  'blobs', -- id
  'blobs', -- name
  false    -- public
) ON CONFLICT DO NOTHING; -- Buckets do not get deleted on db reset

----------------------------------------------------------------------------------------------------
----------- vvv Generated by Next.js template. Do not modify existing lines vvv --------------------
----------------------------------------------------------------------------------------------------
CREATE TABLE public.users (
  id uuid NOT NULL,
  full_name text NULL,
  avatar_url text NULL,
  billing_address jsonb NULL,
  payment_method jsonb NULL,
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

CREATE TABLE public.products (
  id text NOT NULL,
  active boolean NULL,
  name text NULL,
  description text NULL,
  image text NULL,
  metadata jsonb NULL,
  CONSTRAINT products_pkey PRIMARY KEY (id)
) tablespace pg_default;

CREATE TABLE public.prices (
  id text NOT NULL,
  product_id text NULL,
  active boolean NULL,
  description text NULL,
  unit_amount bigint NULL,
  currency text NULL,
  type public.pricing_type NULL,
  interval public.pricing_plan_interval NULL,
  interval_count integer NULL,
  trial_period_days integer NULL,
  metadata jsonb NULL,
  CONSTRAINT prices_pkey PRIMARY KEY (id),
  CONSTRAINT prices_product_id_fkey FOREIGN KEY (product_id) REFERENCES products (id),
  CONSTRAINT prices_currency_check CHECK ((char_length(currency) = 3))
) tablespace pg_default;

CREATE TABLE public.subscriptions (
  id text NOT NULL,
  user_id uuid NOT NULL,
  status public.subscription_status NULL,
  metadata jsonb NULL,
  price_id text NULL,
  quantity integer NULL,
  cancel_at_period_end boolean NULL,
  created timestamp WITH time zone NOT NULL DEFAULT timezone ('utc' :: text, NOW()),
  current_period_start timestamp WITH time zone NOT NULL DEFAULT timezone ('utc' :: text, NOW()),
  current_period_end timestamp WITH time zone NOT NULL DEFAULT timezone ('utc' :: text, NOW()),
  ended_at timestamp WITH time zone NULL DEFAULT timezone ('utc' :: text, NOW()),
  cancel_at timestamp WITH time zone NULL DEFAULT timezone ('utc' :: text, NOW()),
  canceled_at timestamp WITH time zone NULL DEFAULT timezone ('utc' :: text, NOW()),
  trial_start timestamp WITH time zone NULL DEFAULT timezone ('utc' :: text, NOW()),
  trial_end timestamp WITH time zone NULL DEFAULT timezone ('utc' :: text, NOW()),
  CONSTRAINT subscriptions_pkey PRIMARY KEY (id),
  CONSTRAINT subscriptions_price_id_fkey FOREIGN KEY (price_id) REFERENCES prices (id),
  CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id)
) tablespace pg_default;

CREATE TABLE public.customers (
  id uuid NOT NULL,
  stripe_customer_id text NULL,
  CONSTRAINT customers_pkey PRIMARY KEY (id),
  CONSTRAINT customers_id_fkey FOREIGN KEY (id) REFERENCES auth.users (id)
) tablespace pg_default;

----------------------------------------------------------------------------------------------------
----------- ^^^ Generated by Next.js template. Do not modify existing lines ^^^ --------------------
----------------------------------------------------------------------------------------------------