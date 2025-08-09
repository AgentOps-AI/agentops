CREATE TYPE org_roles AS ENUM ('owner', 'admin', 'developer', 'business_user');
CREATE TYPE prem_status AS ENUM ('free', 'pro', 'enterprise');

DROP POLICY "Users can perform CRUD on orgs through org membership" ON public.orgs;
DROP POLICY "Users can view their user_orgs" ON public.user_orgs;

-- Add prem_status to orgs
ALTER TABLE public.orgs
ADD COLUMN prem_status public.prem_status NOT NULL DEFAULT 'free';

-- Add Role and Email Columns to user_orgs
ALTER TABLE public.user_orgs
ADD COLUMN role public.org_roles NOT NULL DEFAULT 'owner';

ALTER TABLE public.user_orgs
ADD COLUMN user_email TEXT NULL;

UPDATE public.user_orgs uo
SET user_email = au.email
FROM auth.users au
WHERE uo.user_id = au.id;

CREATE OR REPLACE FUNCTION public.setup_new_users()
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
  INSERT INTO public.user_orgs (user_id, org_id, user_email)
  VALUES (NEW.id, new_org_id, (SELECT email FROM auth.users WHERE id = NEW.id));

  -- Create a project for the new org
  INSERT INTO public.projects (org_id, name)
  VALUES (new_org_id, 'Default Project');

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Create functions for checking if a user belongs to an org / is admin
CREATE OR REPLACE FUNCTION user_belongs_to_org(org_id UUID) RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.user_orgs uo
    WHERE uo.user_id = (SELECT auth.uid())
    AND uo.org_id = user_belongs_to_org.org_id
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION user_is_org_admin(org_id UUID) RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.user_orgs uo
    WHERE uo.user_id = (SELECT auth.uid())
    AND uo.org_id = user_is_org_admin.org_id 
    AND uo.role in ('owner', 'admin')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION user_is_org_owner(org_id UUID) RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.user_orgs uo
    WHERE uo.user_id = (SELECT auth.uid())
    AND uo.org_id = user_is_org_owner.org_id 
    AND uo.role = 'owner'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create table to handle invitations to orgs
CREATE TABLE public.org_invites(
  user_id UUID NOT NULL,
  org_id UUID NOT NULL,
  role public.org_roles NOT NULL,
  org_name TEXT NOT NULL,
  inviter TEXT NOT NULL,
  CONSTRAINT org_invites_pkey PRIMARY KEY (user_id, org_id),
  CONSTRAINT org_invites_users_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT org_invites_org_id_fkey FOREIGN KEY (org_id) REFERENCES orgs (id) ON UPDATE CASCADE ON DELETE CASCADE
) tablespace pg_default;

ALTER TABLE
  public.org_invites enable ROW LEVEL SECURITY;



-- Update RLS Policies
CREATE POLICY "Users can view orgs through org membership" ON public.orgs FOR SELECT
TO authenticated
USING (
  user_belongs_to_org(id)
);

CREATE POLICY "Users can see all users in their orgs" ON public.user_orgs FOR SELECT
TO authenticated
USING (
    user_belongs_to_org(org_id)
);

CREATE POLICY "Owners and Admins can update users in their orgs" ON public.user_orgs FOR UPDATE
TO authenticated
USING (
  user_is_org_admin(org_id) 
  AND EXISTS(
    SELECT 1 
    FROM orgs 
    WHERE orgs.id = org_id 
    AND orgs.prem_status IN ('pro', 'enterprise'))
  AND user_id <> (SELECT auth.uid()) 
  AND role <> 'owner'
) WITH CHECK(
  user_is_org_admin(org_id) 
  AND EXISTS(
    SELECT 1 
    FROM orgs 
    WHERE orgs.id = org_id 
    AND orgs.prem_status IN ('pro', 'enterprise'))
  AND user_id <> (SELECT auth.uid()) 
  AND role <> 'owner'
);

CREATE POLICY "Owners and Admins can remove users in their orgs" ON public.user_orgs FOR DELETE
TO authenticated
USING (
  user_is_org_admin(org_id) 
  AND role <> 'owner'
);

CREATE POLICY "Users can leave orgs" ON public.user_orgs FOR DELETE
TO authenticated
USING (
  user_id = (SELECT auth.uid())
  AND NOT user_is_org_owner(org_id)
);

CREATE POLICY "Users can see their invitations" ON public.org_invites FOR SELECT
TO authenticated
USING (
  user_id = (SELECT auth.uid())
);

CREATE POLICY "Users can delete their invitations" ON public.org_invites FOR DELETE
TO authenticated
USING (
  user_id = (SELECT auth.uid())
);

CREATE POLICY "Owners can delete orgs" ON public.orgs FOR DELETE
TO authenticated
USING (
  user_is_org_owner(id)
);

CREATE OR REPLACE FUNCTION create_org_invite(invited_email VARCHAR(255), org_id UUID, role public.org_roles) RETURNS VOID AS $$
DECLARE
  user_id UUID;
  inviter VARCHAR(255);
  org_name TEXT;
BEGIN
  IF user_is_org_admin(org_id)
   AND EXISTS (
    SELECT 1 
    FROM public.orgs
    WHERE orgs.id = org_id 
    AND orgs.prem_status IN ('pro', 'enterprise')
  ) AND (
    role <> 'owner'
  ) THEN
    SELECT id INTO user_id
    FROM auth.users
    WHERE invited_email = auth.users.email;

    SELECT name INTO org_name
    FROM public.orgs
    WHERE orgs.id = create_org_invite.org_id;

    SELECT email INTO inviter
    FROM auth.users
    WHERE (SELECT auth.uid()) = auth.users.id;

    INSERT INTO public.org_invites (org_id, user_id, role, org_name, inviter)
    VALUES (org_id, user_id, role, org_name, inviter);
  ELSE 
    RAISE EXCEPTION 'Error creating invite';
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION accept_org_invite(org_id UUID) RETURNS VOID AS $$
DECLARE
  role public.org_roles;
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.org_invites
    WHERE org_invites.user_id = (SELECT auth.uid())
    AND accept_org_invite.org_id = org_invites.org_id
  ) THEN
    BEGIN
      -- Retrieve the role from the invite
      SELECT org_invites.role INTO role
      FROM public.org_invites
      WHERE org_invites.user_id = (SELECT auth.uid())
      AND accept_org_invite.org_id = org_invites.org_id;
      
      -- Insert a new record into public.user_orgs
      INSERT INTO public.user_orgs (org_id, user_id, role, user_email)
      VALUES (accept_org_invite.org_id, (SELECT auth.uid()), role, (SELECT auth.email()));

      -- Delete the invite from public.org_invites
      DELETE FROM public.org_invites
      WHERE org_invites.user_id = (SELECT auth.uid())
      AND accept_org_invite.org_id = org_invites.org_id;
      
    EXCEPTION WHEN OTHERS THEN
      RAISE EXCEPTION 'Error accepting invite';
    END;
  ELSE 
    RAISE EXCEPTION 'Error: invite does not exist';
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION create_new_org(org_name TEXT) RETURNS UUID AS $$
DECLARE
    new_org_id UUID;
BEGIN
  BEGIN
    -- Create new org
    INSERT INTO public.orgs (name)
    VALUES (org_name)
    RETURNING id INTO new_org_id;

    -- Add user and org into user_orgs
    INSERT INTO public.user_orgs (user_id, org_id, user_email)
    VALUES ((SELECT auth.uid()), new_org_id, (SELECT auth.email()));

    -- Create a project for the new org
    INSERT INTO public.projects (org_id, name)
    VALUES (new_org_id, 'Default Project');

    RETURN new_org_id;
  EXCEPTION
    WHEN others THEN
      RAISE EXCEPTION 'Error creating new org';
  END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION rename_org(org_id UUID, org_name TEXT) RETURNS VOID AS $$
BEGIN
  IF user_is_org_admin(org_id)
  AND EXISTS (
    SELECT 1
    FROM public.orgs
    WHERE orgs.id = org_id
  ) THEN
    UPDATE public.orgs
    SET name = org_name
    WHERE id = org_id;
  ELSE 
    RAISE EXCEPTION 'Error renaming org';
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION transfer_org_ownership(org_id UUID, new_owner_id UUID) RETURNS VOID AS $$
BEGIN
  IF user_is_org_owner(org_id) 
  AND EXISTS (
    SELECT 1 
    FROM public.user_orgs 
    WHERE user_orgs.user_id = new_owner_id
  ) AND EXISTS (
    SELECT 1
    FROM public.orgs
    WHERE prem_status IN ('pro', 'enterprise')
  )
  THEN
    BEGIN
      UPDATE public.user_orgs
      SET role = 'admin'
      WHERE user_id = (SELECT auth.uid())
      AND user_orgs.org_id = transfer_org_ownership.org_id;

      UPDATE public.user_orgs
      SET role = 'owner'
      WHERE user_id = new_owner_id
      AND user_orgs.org_id = transfer_org_ownership.org_id;

    EXCEPTION WHEN OTHERS THEN 
      RAISE EXCEPTION 'Error transferring ownership';
    END;
  ELSE 
    RAISE EXCEPTION 'Error: either the user is not the current owner or the new owner is not a member of the organization';
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;