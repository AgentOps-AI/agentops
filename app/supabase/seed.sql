DELETE FROM auth.users;

INSERT INTO auth.users (
  instance_id, 
  id, 
  aud, 
  role, 
  email, 
  encrypted_password, 
  email_confirmed_at, 
  invited_at, 
  confirmation_token, 
  confirmation_sent_at, 
  recovery_token, 
  recovery_sent_at, 
  email_change_token_new, 
  email_change, 
  email_change_sent_at, 
  last_sign_in_at, 
  raw_app_meta_data, 
  raw_user_meta_data, 
  is_super_admin, 
  created_at, 
  updated_at, 
  phone, 
  phone_confirmed_at, 
  phone_change, 
  phone_change_token, 
  phone_change_sent_at, 
  email_change_token_current, 
  email_change_confirm_status, 
  banned_until, 
  reauthentication_token, 
  reauthentication_sent_at, 
  is_sso_user, 
  deleted_at
) VALUES (
  '00000000-0000-0000-0000-000000000000', -- instance_id
  'e043e8e0-504d-4e80-83ee-c42c47c63d8b', -- id
  'authenticated', -- aud
  'authenticated', -- role
  'test@agentops.ai', -- email
  '$2a$10$CPA4tnp7Su0HqAEDJELoveVXWi/bRSJmMcMdmu8T2X5fi3X33Efuu', -- encrypted_password
  '2024-03-06 20:48:52.665092+00', -- email_confirmed_at
  NULL, -- invited_at
  '', -- confirmation_token
  NULL, -- confirmation_sent_at
  '', -- recovery_token
  NULL, -- recovery_sent_at
  '', -- email_change_token_new
  '', -- email_change
  NULL, -- email_change_sent_at
  '2024-03-06 22:09:55.290859+00', -- last_sign_in_at
  '{"provider":"email","providers":["email"]}', -- raw_app_meta_data
  '{}', -- raw_user_meta_data
  NULL, -- is_super_admin
  '2024-03-06 20:48:52.66207+00', -- created_at
  '2024-03-06 22:09:55.292596+00', -- updated_at
  NULL, -- phone
  NULL, -- phone_confirmed_at
  '', -- phone_change
  '', -- phone_change_token
  NULL, -- phone_change_sent_at
  '', -- email_change_token_current
  0, -- email_change_confirm_status
  NULL, -- banned_until
  '', -- reauthentication_token
  NULL, -- reauthentication_sent_at
  FALSE, -- is_sso_user
  NULL -- deleted_at
);

INSERT INTO auth.identities (
  provider_id, 
  user_id, 
  identity_data, 
  provider, 
  last_sign_in_at, 
  created_at, 
  updated_at, 
  id
) VALUES (
  'e043e8e0-504d-4e80-83ee-c42c47c63d8b', -- provider_id
  'e043e8e0-504d-4e80-83ee-c42c47c63d8b', -- user_id
  '{"sub":"e043e8e0-504d-4e80-83ee-c42c47c63d8b","email":"test@agentops.ai","email_verified":false,"phone_verified":false}', -- identity_data
  'email', -- provider
  '2024-03-06 20:48:52.663498+00', -- last_sign_in_at
  '2024-03-06 20:48:52.663547+00', -- created_at
  '2024-03-06 20:48:52.663547+00', -- updated_at
  'fbe71b0d-8f06-423f-a2d3-1c32571127de' -- id
);

INSERT INTO public.orgs (
  id, 
  name,
  prem_status
) VALUES (
  '8e6301f7-bfae-4852-b30e-ab0f6d0b7253', 
  'test_org',
  'pro'
);

INSERT INTO public.user_orgs (
  user_id, 
  org_id,
  user_email,
  role
) VALUES (
  'e043e8e0-504d-4e80-83ee-c42c47c63d8b', 
  '8e6301f7-bfae-4852-b30e-ab0f6d0b7253',
  'test@agentops.ai',
  'owner'
);

-- Commented out duplicate key constraint
-- INSERT INTO public.user_orgs (
--   user_id, org_id, user_email, role
-- ) VALUES (
--   'e043e8e0-504d-4e80-83ee-c42c47c63d8b',
--   'c0000000-0000-0000-0000-000000000000',
--   'test@agentops.ai',
--   'business_user'
-- );

INSERT INTO public.projects (
  id, 
  org_id, 
  api_key, 
  name, 
  environment,
  user_callback_url
) VALUES (
  '0e2bf9df-8980-4afc-9041-2e116dc7ad0e', 
  '8e6301f7-bfae-4852-b30e-ab0f6d0b7253', 
  '6b7a1469-bdcb-4d47-85ba-c4824bc8486e', 
  'test_project', 
  'production',
  NULL
);

INSERT INTO public.sessions (
  id, 
  project_id, 
  project_id_secondary,
  init_timestamp,
  end_state
) VALUES (
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0', 
  '0e2bf9df-8980-4afc-9041-2e116dc7ad0e', 
  NULL,
  '2024-03-05T21:15:52.981Z',
  'Indeterminate'
);

INSERT INTO public.stats (
  session_id 
) VALUES (
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0' 
);

INSERT INTO public.agents (
  id, 
  session_id, 
  name
) VALUES (
  'bab61b5e-d79d-11ee-a73d-1691af3348bd', 
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0', 
  'Test Agent'
);

INSERT INTO public.threads (
  id, 
  session_id, 
  agent_id
) VALUES (
  '8e9b80e0-d79d-11ee-a73d-1691af3348bd', 
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0', 
  'bab61b5e-d79d-11ee-a73d-1691af3348bd'
);

INSERT INTO public.actions (
  session_id, 
  agent_id,
  init_timestamp,
  end_timestamp
) VALUES (
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0', 
  'bab61b5e-d79d-11ee-a73d-1691af3348bd',
  '2024-03-05T21:15:59Z',
  '2024-03-05T21:16:01Z'
);

INSERT INTO public.llms (
  id,
  session_id,
  agent_id,
  thread_id,
  init_timestamp,
  end_timestamp,
  prompt,
  completion
) VALUES (
  'cd4bb00f-3532-44a5-b5fb-86eb4ab30247',
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0',
  'bab61b5e-d79d-11ee-a73d-1691af3348bd',
  '8e9b80e0-d79d-11ee-a73d-1691af3348bd',
  '2024-03-05T21:15:59Z',
  '2024-03-05T21:16:02Z',
  '{"type":"chatml","messages":[{"role":"user","content":"say hello"}]}',
  '{"type":"chatml","messages":{"role":"assistant","content":"hello"}}'
);


INSERT INTO public.tools (
  session_id, 
  agent_id,
  init_timestamp,
  end_timestamp
) VALUES (
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0', 
  'bab61b5e-d79d-11ee-a73d-1691af3348bd',
  '2024-03-05T21:16:01Z',
  '2024-03-05T21:16:03Z'
);

INSERT INTO public.errors (
  session_id,
  error_type,
  timestamp
) VALUES (
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0', 
  'RuntimeError',
  '2024-03-06 11:15:13.761+00'
);

-- Temporarily disabled: deployments table
-- INSERT INTO public.deployments (
--   id, project_id, created_at, shutdown_time, image_id, is_active, build_log
-- ) VALUES (
--   'd1e1f9df-8980-4afc-9041-2e116dc7ad0e',
--   '0e2bf9df-8980-4afc-9041-2e116dc7ad0e',
--   '2024-03-05T21:16:00Z',
--   NULL,
--   'img-123',
--   TRUE,
--   NULL
-- );

INSERT INTO public.spans (
  id, session_id, agent_id, trace_id, span_id, parent_span_id, name, kind, start_time, end_time, attributes, span_type
) VALUES (
  'f1e1f9df-8980-4afc-9041-2e116dc7ad0e',
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0',
  'bab61b5e-d79d-11ee-a73d-1691af3348bd',
  'trace-1',
  'span-1',
  NULL,
  'test-span',
  'internal',
  '2024-03-05T21:16:00Z',
  '2024-03-05T21:16:01Z',
  NULL,
  'test-type'
);

INSERT INTO public.ttd (
  id, ttd_id, branch_name, session_id, llm_id, prompt, completion, model, prompt_tokens, completion_tokens, params, returns, created_at
) VALUES (
  'a1e1f9df-8980-4afc-9041-2e116dc7ad0e',
  'b1e1f9df-8980-4afc-9041-2e116dc7ad0e',
  'main',
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0',
  'cd4bb00f-3532-44a5-b5fb-86eb4ab30247',
  NULL, NULL, 'gpt-4', 10, 10, NULL, NULL, '2024-03-05T21:16:00Z'
);

INSERT INTO public.org_invites (
  inviter_id, org_id, role, org_name, invitee_email, created_at
) VALUES (
  'e043e8e0-504d-4e80-83ee-c42c47c63d8b',
  '8e6301f7-bfae-4852-b30e-ab0f6d0b7253',
  'developer',
  'test_org',
  'invitee@agentops.ai',
  '2024-03-07T10:00:00Z'
);

INSERT INTO public.developer_errors (
  api_key, sdk_version, type, message, stack_trace, host_env, session_id
) VALUES (
  '6b7a1469-bdcb-4d47-85ba-c4824bc8486e',
  '1.0.0',
  'TypeError',
  'Test error',
  'stacktrace',
  NULL,
  'e8cf0a8c-11d5-418a-805d-767437e5dbd0'
);