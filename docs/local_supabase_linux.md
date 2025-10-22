Local Supabase on Linux (CLI install fallback)

1) Install CLI
- Download latest Linux x86_64 binary from https://github.com/supabase/cli/releases/latest
- Extract to ~/.supabase/bin and chmod +x
- Add to PATH:
  export PATH="$HOME/.supabase/bin:$PATH"
- Verify:
  supabase --version

2) Initialize and start in app/
- cd ~/repos/agentops/app
- supabase init
- supabase start

3) Capture credentials from output
- URL: http://127.0.0.1:54321
- anon key
- service_role key
- Postgres: host 127.0.0.1, port 54322, user postgres, password postgres, database postgres

4) Fill envs
- app/.env
  NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
  NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon>
  SUPABASE_SERVICE_ROLE_KEY=<service_role>
  SUPABASE_PROJECT_ID=local
  SUPABASE_HOST=127.0.0.1
  SUPABASE_PORT=54322
  SUPABASE_DATABASE=postgres
  SUPABASE_USER=postgres
  SUPABASE_PASSWORD=postgres
- app/api/.env
  SUPABASE_URL=http://127.0.0.1:54321
  SUPABASE_KEY=<service_role>
  SUPABASE_HOST=127.0.0.1
  SUPABASE_PORT=54322
  SUPABASE_DATABASE=postgres
  SUPABASE_USER=postgres
  SUPABASE_PASSWORD=postgres
- app/dashboard/.env.local
  NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
  NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon>
  SUPABASE_SERVICE_ROLE_KEY=<service_role>
  SUPABASE_PROJECT_ID=local

5) Run stack
- From app/: docker compose up -d
- API: http://localhost:8000/redoc
- Dashboard: http://localhost:3000

6) Notes
- Playground must be disabled:
  app/.env -> NEXT_PUBLIC_PLAYGROUND=false
  app/dashboard/.env.local -> NEXT_PUBLIC_PLAYGROUND="false"
- ClickHouse Cloud requires IP allowlist.
