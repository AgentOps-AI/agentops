ALTER TABLE public.developer_errors 
ADD COLUMN timestamp timestamp with time zone null default now();