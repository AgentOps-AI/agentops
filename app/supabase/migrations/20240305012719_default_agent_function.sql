----------------------------------------------------------------------------------------------------
----------- Lookup or create a default agent if not supplied in events --------------------
----------------------------------------------------------------------------------------

CREATE FUNCTION add_default_agent_if_null()
RETURNS TRIGGER AS $$
DECLARE
   agent_row agents%ROWTYPE;
BEGIN
   -- If agent_id is NULL
   IF NEW.agent_id IS NULL THEN
      -- Retrieve the default_agent for the given session
      SELECT * INTO agent_row
      FROM agents
      WHERE session_id = NEW.session_id AND name = 'Default Agent';

      -- Check for existence
      IF NOT FOUND THEN
         -- Create new agent and get inserted row
         INSERT INTO agents(id, session_id, name)
         VALUES (gen_random_uuid(), NEW.session_id, 'Default Agent')
         RETURNING * INTO agent_row;
      END IF;

      -- Assign the ID of the found or created agent to the new event
      NEW.agent_id := agent_row.id;
   END IF;

   RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;

-- Create the trigger on the Events table
CREATE TRIGGER actions_insert_trigger
    BEFORE INSERT ON actions
    FOR EACH ROW
    EXECUTE FUNCTION add_default_agent_if_null();

CREATE TRIGGER tools_insert_trigger
    BEFORE INSERT ON tools
    FOR EACH ROW
    EXECUTE FUNCTION add_default_agent_if_null();

CREATE TRIGGER threads_insert_trigger
    BEFORE INSERT ON threads
    FOR EACH ROW
    EXECUTE FUNCTION add_default_agent_if_null();

CREATE TRIGGER llms_insert_trigger
    BEFORE INSERT ON llms
    FOR EACH ROW
    EXECUTE FUNCTION add_default_agent_if_null();