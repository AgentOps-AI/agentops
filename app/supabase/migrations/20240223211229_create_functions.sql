-- Create user, org, and project on new user
CREATE FUNCTION public.setup_new_users()
RETURNS TRIGGER AS $$
DECLARE
    user_name TEXT;
    new_org_id UUID;
BEGIN
    user_name := NEW.raw_user_meta_data->>'full_name';
    -- Add entry into users table
    INSERT INTO public.users (id, full_name, avatar_url)
    VALUES (NEW.id, user_name, NEW.raw_user_meta_data->>'avatar_url');

    -- Add entry into orgs table
    IF user_name IS NOT NULL THEN
        INSERT INTO public.orgs (name)
        VALUES (user_name || '''s org')
        RETURNING id INTO new_org_id;
    ELSE
        INSERT INTO public.orgs (name)
        VALUES ('Default Organization')
        RETURNING id INTO new_org_id;
    END IF;

    -- Add user and org into user_orgs
    INSERT INTO public.user_orgs (user_id, org_id)
    VALUES (NEW.id, new_org_id);

    -- Create a project for the new org
    INSERT INTO public.projects (org_id, name)
    VALUES (new_org_id, 'Default Project');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE TRIGGER on_new_user_creation
AFTER INSERT ON auth.users
FOR EACH ROW 
EXECUTE FUNCTION public.setup_new_users();

-- Rotate API Keys
CREATE OR REPLACE FUNCTION rotate_project_api_key(project_id uuid) RETURNS text AS $$
DECLARE
  new_api_key uuid;
BEGIN
  new_api_key := gen_random_uuid();
  
  UPDATE projects
  SET api_key = new_api_key
  WHERE id = project_id;
  
  RETURN new_api_key;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;