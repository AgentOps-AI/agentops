-- Create the default shared org
DO $$ 
DECLARE
    default_org_id UUID;
BEGIN
    INSERT INTO public.orgs (id, name, prem_status)
    VALUES (
        'c0000000-0000-0000-0000-000000000000',
        'AgentOps Demo Org',
        'pro'
    )
    ON CONFLICT (id) DO NOTHING
    RETURNING id INTO default_org_id;
END $$;

-- Create a new trigger function for adding users to the shared org
CREATE OR REPLACE FUNCTION public.add_to_shared_org()
RETURNS TRIGGER AS $$
BEGIN
    -- Add user to shared org as developer
    INSERT INTO public.user_orgs (user_id, org_id, role, user_email)
    VALUES (NEW.id, 'c0000000-0000-0000-0000-000000000000', 'business_user', NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a new trigger that runs after setup_new_users
CREATE TRIGGER on_new_user_add_to_shared_org
AFTER INSERT ON auth.users
FOR EACH ROW 
EXECUTE FUNCTION public.add_to_shared_org();
