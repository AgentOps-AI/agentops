-- Add new columns to users table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'users' 
                  AND column_name = 'email') THEN
        ALTER TABLE public.users ADD COLUMN email text NULL DEFAULT ''::text;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'users' 
                  AND column_name = 'survey_is_complete') THEN
        ALTER TABLE public.users ADD COLUMN survey_is_complete boolean NOT NULL DEFAULT false;
    END IF;
END $$;
