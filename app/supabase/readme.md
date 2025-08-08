> **Note:** While this project may not have specific linting/formatting configurations, the repository uses shared development tools. Please see the [root README.md](../README.md#development-setup) for setup instructions if needed.

###Useful Commands:

Download Supabase CLI
`npm i supabase --save-dev`
or on Mac
`brew install supabase/tap/supabase`

login
`supabase login`

start supabase
`supabase start`

link with remote project
`supabase link --project-ref <project-id>`

pull changes from remote
`supabase db pull`

load supabase configuration:
`supabase migration up`
`supabase db reset`
`supabase db reset --linked`

deploy configuration to remote
`supabase db push`

create diff
`supabase db diff`

## Setting up a new project

### Setting up Auth

1. Go to Authentication > URL Configuration
2. Add `https://app.agentops.ai` as the Site URL
3. Add `https://app.agentops.ai/**` into the Redirect URLs
4. Go to Authentication > Providers
5. Enable GitHub (by creating a GitHub app and filling in the provided info)
6. Go to Settings > Authentication > SMTP Settings
7. Enable `Enable Custom SMTP`
8. Fill in the required sender and SMTP Provider details

### Setting up Webhooks

1. Download Supabase CLI (See above)
2. Run `supabase link --project-ref $Project-ID --password $db-password`. The Project-ID can be found on supabase under _settings > general > reference ID_. If the password is not saved, it must be reset and stored in a secure location.
3. Create a .env file in the **supabase** folder
4. Add .env variables:

```
ATTIO_API_KEY=
ATTIO_OBJECT_ID=
```

5. Run `supabase secrets set --env-file ./supabase/.env`
6. Run `supabase functions deploy`
7. On the Supabase website, go to _database > webhooks_ and click "enable webhooks"
8. Create a new webhook that posts to the Supabase function. Add the authorization header from the dropdown. This should auto-populate the service role key

You should be set!
