-- Add pack_name column to deploy.projects table
ALTER TABLE deploy.projects 
ADD COLUMN pack_name TEXT DEFAULT NULL;