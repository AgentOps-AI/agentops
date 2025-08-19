-- Migration: Fix setup_new_users trigger to properly populate email field
-- This fixes the issue where user.email was not being populated, causing invite acceptance to fail

-- Drop and recreate the function with the email field included
CREATE OR REPLACE FUNCTION public.setup_new_users()
RETURNS TRIGGER AS $$
DECLARE
  user_name TEXT;
  new_org_id UUID;
BEGIN
  user_name := NEW.raw_user_meta_data->>'full_name';
  
  -- Add entry into users table (NOW INCLUDING EMAIL!)
  INSERT INTO public.users (id, full_name, avatar_url, email)
  VALUES (NEW.id, user_name, NEW.raw_user_meta_data->>'avatar_url', NEW.email);

  -- ALWAYS create a personal default organization for every user
  IF user_name IS NOT NULL THEN
    INSERT INTO public.orgs (name)
    VALUES (user_name || '''s org')
    RETURNING id INTO new_org_id;
  ELSE
    INSERT INTO public.orgs (name)
    VALUES ('Default Organization')
    RETURNING id INTO new_org_id;
  END IF;

  -- Add user to their default org as owner
  INSERT INTO public.user_orgs (user_id, org_id, role, user_email)
  VALUES (NEW.id, new_org_id, 'owner', NEW.email);

  -- Create a project for the new org
  INSERT INTO public.projects (org_id, name)
  VALUES (new_org_id, 'Default Project');

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- The trigger itself doesn't need to be recreated, it will use the updated function

-- Now fix existing users who have empty email fields
-- This will populate the email field for users where it's currently empty
UPDATE public.users u
SET email = au.email
FROM auth.users au
WHERE u.id = au.id
  AND (u.email IS NULL OR u.email = '');

-- Add a comment to document this fix
COMMENT ON FUNCTION public.setup_new_users() IS 'Creates user record, default org, and project for new signups. Fixed to include email field in users table.'; 