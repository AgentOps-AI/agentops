import { Database } from '../auth-types.ts';

const LOOPS_API_KEY = Deno.env.get('LOOPS_API_KEY');
const LOOPS_ENDPOINT = 'https://app.loops.so/api/v1/contacts/create';

const headers = {
  Authorization: `Bearer ${LOOPS_API_KEY}`,
  'Content-Type': 'application/json',
};

type AuthUserRecord = Database['auth']['Tables']['users']['Row'];

interface UserPayload {
  type: 'INSERT';
  table: string;
  record: AuthUserRecord;
  schema: 'auth';
  old_record: AuthUserRecord | null;
}

Deno.serve(async (req) => {
  try {
    const requestJson: UserPayload = await req.json();
    const full_name = requestJson.record.raw_user_meta_data?.['full_name'] || '';
    const [firstName, lastName] = splitFullName(full_name);

    const payload = {
      email: requestJson.record.email,
      firstName,
      lastName,
      agentOpsUser: true,
      source: 'AgentOps Supabase Hook',
      subscribed: true,
    };

    const loopsData = {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    };

    const response = await fetch(LOOPS_ENDPOINT, loopsData);

    if (!response.ok) {
      throw new Error(`Failed to create contact: ${response.statusText}`);
    }

    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
});

function splitFullName(fullName: string): [string, string] {
  const nameParts = fullName.trim().split(' ');
  const firstName = nameParts[0];
  const lastName = nameParts.slice(1).join(' ') || '';
  return [firstName, lastName];
}
