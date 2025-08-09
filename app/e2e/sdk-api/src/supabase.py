import httpx
import logging


class Supabase:
    def __init__(self, supabase_url, supabase_key):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key

    def get_url(self):
        return self.supabase_url

    async def get(self, table: str, columns: str, key_name: str, key_value):
        logging.info(f"Retrieving {columns} for {key_name}: {key_value}")

        url = f"{self.supabase_url}/rest/v1/{table}?{key_name}=eq.{key_value}&select={columns}"
        headers = {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

        async with httpx.AsyncClient() as async_client:
            response = await async_client.get(url, headers=headers)

        json = response.json()
        if not response.is_success:
            raise RuntimeError(
                f"Error retrieving {columns=} from {table=} : {json['code']=}. {json['message']=}"
            )

        return json

    async def get_first(self, table: str, columns: str, key_name: str, key_value):
        rows = await self.get(table, columns, key_name, key_value)
        return rows[0] if rows else None

    async def delete(self, table: str, key_name: str, key_value):
        logging.info(f"Deleting row with {key_name}: {key_value} from table {table}")

        url = f"{self.supabase_url}/rest/v1/{table}?{key_name}=eq.{key_value}"
        headers = {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

        async with httpx.AsyncClient() as async_client:
            response = await async_client.delete(url, headers=headers)

        if not response.status_code == 204:
            raise RuntimeError(f"Error deleting row from {table=} : {table}")

        return response.status_code == 204

    async def insert(self, table: str, data):
        logging.info(f"Inserting to {table} table: {data}")
        table_url = f"{self.supabase_url}/rest/v1/{table}"
        headers = {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

        async with httpx.AsyncClient() as async_client:
            response = await async_client.post(table_url, json=data, headers=headers)

        if not response.is_success:
            json = response.json()
            raise RuntimeError(
                f"Error inserting to {table=}. Postgres: {json['code']=}. {json['message']=}"
            )

        return response

    async def upsert(self, table: str, pkey_name: str, data):
        logging.info(f"Upserting to {table} table: {data}")
        table_url = (
            f"{self.supabase_url}/rest/v1/{table}?{pkey_name}=eq.{data.get(pkey_name)}"
        )
        headers = {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Prefer": "resolution=merge",
        }

        async with httpx.AsyncClient() as async_client:
            response = await async_client.put(table_url, json=data, headers=headers)

        if not response.is_success:
            json = response.json()
            raise RuntimeError(
                f"Error upserting to {table=}. Postgres: {json['code']=}. {json['message']=}"
            )

        return response

    async def post_to_bucket(
        self, bucket: str, session_id: str, image_bytes, filename: str
    ):
        logging.info(f"Writing {filename} to {bucket} for session: {session_id}")

        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{session_id}/{filename}"
        headers = {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }
        file = {"file": (filename, image_bytes, "image/png")}

        async with httpx.AsyncClient() as async_client:
            response = await async_client.post(url, files=file, headers=headers)

        if not response.is_success:
            json = response.json()
            raise RuntimeError(
                f"Error writing to {bucket=}. Postgres: {json['code']=}. {json['message']=}"
            )

        return response

    async def get_session_ids(self, api_key, parent_key=None):
        """
        Validates the API key and retrieves the valid sessions for the given API key.

        :param api_key: The API key to validate and retrieve sessions for.
        :return: The project with all valid sessions inner joined
        :raises RuntimeError: If there was an error retrieving the project id with the API key or if no valid session was found.
        """
        api_keys = [api_key]
        if parent_key:
            api_keys.append(parent_key)

        logging.info(f'Validating api_keys: {",".join(api_keys)}')

        url = f'{self.supabase_url}/rest/v1/projects?api_key=in.({",".join(api_keys)})&select=id'
        headers = {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

        async with httpx.AsyncClient() as async_client:
            response = await async_client.get(url, headers=headers)

        if not response.is_success:
            raise RuntimeError(f"Error retrieving project id with API key {api_key}")

        json = response.json()

        project_ids = [project["id"] for project in json]

        url = f'{self.supabase_url}/rest/v1/sessions?or=(project_id.in.({",".join(project_ids)}),project_id_secondary.in.({",".join(project_ids)}))&select=id'
        headers = {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

        async with httpx.AsyncClient() as async_client:
            response = await async_client.get(url, headers=headers)

        if not response.is_success:
            raise RuntimeError(f"Error retrieving project id with API key {api_key}")

        json = response.json()

        if len(json) == 0:
            raise RuntimeError("No valid session found")

        return json
