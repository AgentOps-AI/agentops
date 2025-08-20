import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from termcolor import colored

from agentops.common.environment import APP_URL
import agentops.api.event_handlers as event_handlers
from agentops.api.db.supabase_client import AsyncSupabaseClient
from agentops.api.exceptions import ExpiredJWTError, InvalidModelError, InvalidAPIKeyError
from agentops.api.log_config import logger
from agentops.api.utils import generate_jwt, update_stats, validate_uuid, verify_jwt

from agentops.exporter import export

# Create a router for v2 endpoints
router = APIRouter(prefix="/v2")

jwt_secret = os.environ["JWT_SECRET_KEY"]
app_url = APP_URL



@router.post("/sessions")
async def create_session(request: Request, supabase: AsyncSupabaseClient):
    """Create a new session"""
    try:
        api_key = request.headers.get("X-Agentops-Api-Key")
        parent_key = request.headers.get("X-Agentops-Parent-Key")

        validate_uuid(api_key)
        tasks = [
            supabase.table("projects").select("*").eq("api_key", api_key).limit(1).single().execute(),
            request.json(),
        ]

        if parent_key:
            tasks.append(
                supabase.table("projects").select("*").eq("api_key", parent_key).limit(1).single().execute()
            )
            project, data, project_secondary = await asyncio.gather(*tasks)
        else:
            project, data = await asyncio.gather(*tasks)
            project_secondary = None

        logger.debug(data)

        if project is None:
            raise RuntimeError("Invalid API Key")

        session = {
            "id": data["session"]["session_id"],
            "project_id": project["id"],
            "init_timestamp": data["session"]["init_timestamp"],
            "end_timestamp": data["session"].get("end_timestamp", None),
            "tags": data["session"].get("tags", None),
            "end_state": data["session"].get("end_state", None),
            "end_state_reason": data["session"].get("end_state_reason", None),
            "video": data["session"].get("video", None),
            "host_env": data["session"].get("host_env", None),
        }

        if project_secondary:
            session["project_id_secondary"] = project_secondary["id"]

        await supabase.table("sessions").insert(session).execute()
        await supabase.table("stats").insert({"session_id": session["id"]}).execute()
        await export.create_session(session)

        token = generate_jwt(session["id"], jwt_secret)
        logger.info(colored(f"Completed request for {session['id']}", "yellow"))
        return JSONResponse(
            {
                "status": "Success",
                "jwt": token,
                "session_url": f'{app_url}/drilldown?session_id={data["session"]["session_id"]}',
            },
            status_code=200,
        )
    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": request.url.path, "message": "Expired Token"}, status_code=401)
    except InvalidAPIKeyError as e:
        # This is a user error (invalid API key format), not a system error
        # Log as warning to avoid Sentry alerts
        try:
            data = await request.json()
            logger.warning(
                f"{request.url.path}: Invalid API key format for session {data.get('session', {}).get('session_id', 'unknown')}"
            )
        except Exception:
            logger.warning(f"{request.url.path}: Invalid API key format")
        
        return JSONResponse(
            {
                "path": request.url.path,
                "message": "Invalid API key format",
            },
            status_code=400,
        )
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(
                f"{request.url.path}: Error creating session with id {data['session']['session_id']}: {e} Data received: {data}"
            )
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error creating session: {e} Could not read data: {log_error}")

        return JSONResponse(
            {
                "path": request.url.path,
                "message": f"Error creating session: {e}",
            },
            status_code=400,
        )


@router.post("/reauthorize_jwt")
async def v2_reauthorize_jwt(request: Request, supabase: AsyncSupabaseClient):
    try:
        api_key = request.headers.get("X-Agentops-Api-Key")

        validate_uuid(api_key)

        tasks = [
            supabase.table("projects").select("id").eq("api_key", api_key).execute(),
            request.json(),
        ]
        project_response, data = await asyncio.gather(*tasks)

        project = project_response.data[0] if project_response.data else None

        if project is None:
            raise RuntimeError("Invalid API Key")

        session_response = (
            await supabase.table("sessions").select("project_id").eq("id", data["session_id"]).execute()
        )
        session = session_response.data[0] if session_response.data else None

        if session is None:
            raise RuntimeError("Invalid Session Id")

        if session["project_id"] != project["id"]:
            raise RuntimeError("Invalid Session Id")

        token = generate_jwt(data["session_id"], jwt_secret)
        logger.info(colored(f"Completed request for session: {data['session_id']}", "yellow"))
        return JSONResponse({"status": "Success", "jwt": token})
    
    except InvalidAPIKeyError as e:
        # This is a user error (invalid API key format), not a system error
        # Log as warning to avoid Sentry alerts
        try:
            data = await request.json()
            logger.warning(
                f"{request.url.path}: Invalid API key format for session {data.get('session', {}).get('session_id', 'unknown')}"
            )
        except Exception:
            logger.warning(f"{request.url.path}: Invalid API key format")
        
        return JSONResponse(
            {
                "path": request.url.path,
                "message": "Invalid API key format",
            },
            status_code=400,
        )


    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error reauthorizing Api Key: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(
                f"{request.url.path}: Error reauthorizing Api Key: {e} Could not read data: {log_error}"
            )

        return JSONResponse(
            {
                "path": request.url.path,
                "message": f" Error reauthorizing Api Key: {e}",
            },
            status_code=400,
        )


@router.post("/create_session")
async def v2_create_session(request: Request, supabase: AsyncSupabaseClient):
    try:
        api_key = request.headers.get("X-Agentops-Api-Key")
        parent_key = request.headers.get("X-Agentops-Parent-Key")

        validate_uuid(api_key)

        tasks = [
            supabase.table("projects").select("id").eq("api_key", api_key).execute(),
            request.json(),
        ]

        if parent_key:
            tasks.append(supabase.table("projects").select("id").eq("api_key", parent_key).execute())
            project_response, data, project_secondary_response = await asyncio.gather(*tasks)
            project_secondary = (
                project_secondary_response.data[0] if project_secondary_response.data else None
            )
        else:
            project_response, data = await asyncio.gather(*tasks)
            project_secondary = None

        project = project_response.data[0] if project_response.data else None

        logger.debug(data)

        if project is None:
            raise RuntimeError("Invalid API Key")

        session = {
            "id": data["session"]["session_id"],
            "project_id": project["id"],
            "init_timestamp": data["session"].get("init_timestamp", None)
            or datetime.now(timezone.utc).isoformat(),
            "end_timestamp": data["session"].get("end_timestamp", None),
            "tags": data["session"].get("tags", None),
            "end_state": data["session"].get("end_state", None),
            "end_state_reason": data["session"].get("end_state_reason", None),
            "video": data["session"].get("video", None),
            "host_env": data["session"].get("host_env", None),
        }

        if project_secondary:
            session["project_id_secondary"] = project_secondary["id"]

        await supabase.table("sessions").insert(session).execute()
        await supabase.table("stats").insert({"session_id": session["id"]}).execute()
        await export.create_session(session)

        token = generate_jwt(session["id"], jwt_secret)
        logger.info(colored(f"Completed request for {session['id']}", "yellow"))
        return JSONResponse(
            {
                "status": "Success",
                "jwt": token,
                "session_url": f'{app_url}/drilldown?session_id={data["session"]["session_id"]}',
            }
        )
    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": str(request.url.path), "message": "Expired Token"}, status_code=401)
    except InvalidAPIKeyError as e:
        # This is a user error (invalid API key format), not a system error
        # Log as warning to avoid Sentry alerts
        try:
            data = await request.json()
            logger.warning(
                f"{request.url.path}: Invalid API key format for session {data.get('session', {}).get('session_id', 'unknown')}"
            )
        except Exception:
            logger.warning(f"{request.url.path}: Invalid API key format")
        
        return JSONResponse(
            {
                "path": request.url.path,
                "message": "Invalid API key format",
            },
            status_code=400,
        )
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(
                f"{request.url.path}: Error creating session with id {data['session']['session_id']}: {e} Data received: {data}"
            )
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error creating session: {e} Could not read data: {log_error}")

        return JSONResponse(
            {
                "path": str(request.url.path),
                "message": f"Error creating session: {e}",
            },
            status_code=400,
        )


@router.post("/update_session")
async def v2_update_session(request: Request, supabase: AsyncSupabaseClient):
    try:
        authorization_header = request.headers.get("Authorization")
        if authorization_header is None:
            raise RuntimeError("Bearer Token is Missing")

        token = authorization_header.split(" ")[1]
        session_id = verify_jwt(token, jwt_secret)
        data = await request.json()

        logger.debug(data)

        session = {
            "id": session_id,
            "init_timestamp": data["session"]["init_timestamp"],
            "end_timestamp": data["session"].get("end_timestamp", None),
            "tags": data["session"].get("tags", None),
            "end_state": data["session"].get("end_state", None),
            "end_state_reason": data["session"].get("end_state_reason", None),
            "video": data["session"].get("video", None),
            "host_env": data["session"].get("host_env", None),
        }

        await supabase.table("sessions").update(session).eq("id", session_id).execute()
        await export.update_session(session)

        cost_response = await supabase.table("stats").select("cost").eq("session_id", session_id).execute()
        cost = cost_response.data[0] if cost_response.data else None

        logger.info(colored(f"Completed request for session: {session_id}", "yellow"))
        if cost is not None:
            return JSONResponse(
                {
                    "status": "success",
                    "token_cost": cost.get("cost", "0.00") or "0.00",
                    "session_url": f"{app_url}/drilldown?session_id={session_id}",
                }
            )
        return JSONResponse({"status": "success"})
    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": str(request.url.path), "message": "Expired Token"}, status_code=401)
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error posting session: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error posting session: {e} Could not read data: {log_error}")

        return JSONResponse(
            {
                "path": str(request.url.path),
                "message": f"Error posting session: {e}",
            },
            status_code=400,
        )


@router.post("/create_agent")
async def v2_create_agent(request: Request, supabase: AsyncSupabaseClient):
    try:
        authorization_header = request.headers.get("Authorization")
        if authorization_header is None:
            raise RuntimeError("Bearer Token is Missing")

        token = authorization_header.split(" ")[1]
        session_id = verify_jwt(token, jwt_secret)
        data = await request.json()

        logger.debug(data)

        agent = {
            "id": data["id"],
            "session_id": session_id,
            "name": data.get("name", None),
            "logs": data.get("logs", None),
        }

        await supabase.table("agents").upsert(agent).execute()
        await export.create_agent(agent)

        logger.info(
            colored(
                f"Completed request request for agent {agent['id']} and session {session_id}",
                "yellow",
            )
        )
        return JSONResponse("Success")
    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": request.url.path, "message": "Expired Token"}, status_code=401)
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error creating agent: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error creating agent: {e} Could not read data: {log_error}")

        return JSONResponse(
            {
                "path": request.url.path,
                "message": f"Error creating agent: {e}",
            },
            status_code=400,
        )


@router.post("/create_thread")
async def v2_create_thread(request: Request, supabase: AsyncSupabaseClient):
    try:
        authorization_header = request.headers.get("Authorization")
        if authorization_header is None:
            raise RuntimeError("Bearer Token is Missing")

        token = authorization_header.split(" ")[1]
        session_id = verify_jwt(token, jwt_secret)
        data = await request.json()

        logger.debug(data)

        thread = {
            "id": data["id"],
            "session_id": session_id,
            "agent_id": data.get("agent_id", None),
        }

        await supabase.table("threads").upsert(thread).execute()

        logger.info(colored(f"Completed request request for thread: {thread['id']}", "yellow"))
        return JSONResponse("Success")
    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": request.url.path, "message": "Expired Token"}, status_code=401)
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error creating agent: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error creating agent: {e} Could not read data: {log_error}")

        return JSONResponse(
            {
                "path": request.url.path,
                "message": f"Error creating agent: {e}",
            },
            status_code=400,
        )


@router.post("/create_events")
async def v2_create_events(request: Request, supabase: AsyncSupabaseClient):
    try:
        authorization_header = request.headers.get("Authorization")
        if authorization_header is None:
            raise RuntimeError("Bearer Token is Missing")

        token = authorization_header.split(" ")[1]
        session_id = verify_jwt(token, jwt_secret)
        data = await request.json()

        # premium_status = await get_premium_status(supabase, sessions['id'])
        premium_status = False

        actions = []
        llms = []
        tools = []
        errors = []
        additional_cost: Decimal | None = Decimal(0)
        additional_events = 0
        additional_prompt_tokens = 0
        additional_completion_tokens = 0
        for event in data.get("events"):
            additional_events += 1
            if event["event_type"] == "llms":
                llm = await event_handlers.handle_llms(event, premium_status, session_id)
                cost = llm.get("cost")
                if cost is not None:
                    additional_cost += Decimal(cost)
                additional_prompt_tokens += llm["prompt_tokens"]
                additional_completion_tokens += llm["completion_tokens"]
                llms.append(llm)
            elif event["event_type"] == "tools":
                tools.append(await event_handlers.handle_tools(event, session_id))
            elif event["event_type"] == "errors":
                errors.append(await event_handlers.handle_errors(event, session_id))
            else:
                actions.append(await event_handlers.handle_actions(supabase, event, session_id))

        if additional_cost == Decimal(0):
            additional_cost = None

        inserts = []
        if len(actions) != 0:
            inserts.append(supabase.table("actions").insert(actions).execute())
            for action in actions:
                await export.create_action_event(action)
        if len(llms) != 0:
            inserts.append(supabase.table("llms").insert(llms).execute())
            for llm in llms:
                await export.create_llm_event(llm)
        if len(tools) != 0:
            inserts.append(supabase.table("tools").insert(tools).execute())
            for tool in tools:
                await export.create_tool_event(tool)
        if len(errors) != 0:
            inserts.append(supabase.table("errors").insert(errors).execute())
            for error in errors:
                await export.create_error_event(error)

        inserts.append(
            update_stats(
                supabase=supabase,
                session_id=session_id,
                cost=additional_cost,
                events=additional_events,
                prompt_tokens=additional_prompt_tokens,
                completion_tokens=additional_completion_tokens,
                errors=len(errors),
            )
        )

        if inserts:
            results = await asyncio.gather(*inserts, return_exceptions=True)
            runtime_errors = [result for result in results if isinstance(result, Exception)]
            if len(runtime_errors) > 0:
                raise RuntimeError(runtime_errors[0])

        logger.info(colored(f"Completed request request for Session: {session_id}", "yellow"))
        return JSONResponse("Success")
    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": request.url.path, "message": "Expired Token"}, status_code=401)
    except InvalidModelError as e:
        message = {
            "path": request.url.path,
            "message": f"Invalid model while posting event: {e}",
        }
        return JSONResponse(message, status_code=401)
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error posting event: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error posting event: {e} Could not read data: {log_error}")

        return JSONResponse(
            {"path": request.url.path, "message": f"Error posting event: {e}"},
            status_code=400,
        )


@router.post("/update_events")
async def v2_update_events(request: Request, supabase: AsyncSupabaseClient):
    try:
        authorization_header = request.headers.get("Authorization")
        if authorization_header is None:
            raise RuntimeError("Bearer Token is Missing")

        token = authorization_header.split(" ")[1]
        session_id = verify_jwt(token, jwt_secret)
        data = await request.json()

        # premium_status = await get_premium_status(supabase, sessions['id'])
        premium_status = False

        actions = []
        llms = []
        tools = []
        errors = []
        for event in data.get("events"):
            if event["event_type"] == "llms":
                llm = await event_handlers.handle_llms(event, premium_status, session_id)
                llms.append(llm)
            elif event["event_type"] == "tools":
                tools.append(await event_handlers.handle_tools(event, session_id))
            elif event["event_type"] == "errors":
                errors.append(await event_handlers.handle_errors(event, session_id))
            else:
                actions.append(await event_handlers.handle_actions(supabase, event, session_id))

        inserts = []
        for action in actions:
            inserts.append(supabase.table("actions").update(action).eq("id", action.get("id")).execute())
            await export.update_action_event(action)
        for llm in llms:
            inserts.append(supabase.table("llms").update(llm).eq("id", llm.get("id")).execute())
            await export.update_llm_event(llm)
        for tool in tools:
            inserts.append(supabase.table("tools").update(tool).eq("id", tool.get("id")).execute())
            await export.update_tool_event(tool)
        for error in errors:
            inserts.append(supabase.table("errors").update(error).eq("id", error.get("id")).execute())
            await export.update_error_event(error)

        if inserts:
            results = await asyncio.gather(*inserts, return_exceptions=True)
            runtime_errors = [result for result in results if isinstance(result, RuntimeError)]
            if len(runtime_errors) > 0:
                raise RuntimeError(runtime_errors)

        logger.info(colored(f"Completed request request for Session: {session_id}", "yellow"))
        return JSONResponse("Success")
    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": request.url.path, "message": "Expired Token"}, status_code=401)
    except InvalidModelError as e:
        message = {
            "path": request.url.path,
            "message": f"Invalid model while posting event: {e}",
        }
        return JSONResponse(message, status_code=401)
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error posting event: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error posting event: {e} Could not read data: {log_error}")

        return JSONResponse(
            {"path": request.url.path, "message": f"Error posting event: {e}"},
            status_code=400,
        )


@router.put("/update_logs")
async def v2_update_logs(request: Request, supabase: AsyncSupabaseClient):
    try:
        authorization_header = request.headers.get("Authorization")
        if authorization_header is None:
            raise RuntimeError("Bearer Token is Missing")

        token = authorization_header.split(" ")[1]
        session_id = verify_jwt(token, jwt_secret)
        data = await request.json()

        if "logs" not in data:
            raise RuntimeError("Logs data is missing")

        # Store logs in Supabase Storage
        bucket_name = "session-logs"
        file_path = f"{session_id}.txt"

        # Get the project_id
        session_response = (
            await supabase.table("sessions").select("project_id").eq("id", session_id).execute()
        )
        session = session_response.data[0] if session_response.data else None

        if not session:
            raise RuntimeError("Session not found")

        project_id = session["project_id"]

        # Create the logs content
        logs_content = data["logs"]

        # Append to existing logs in Supabase Storage
        storage_client = supabase.storage.from_(bucket_name)

        # Check if file exists
        try:
            existing_file = await storage_client.download(f"{project_id}/{file_path}")
            existing_content = existing_file.decode("utf-8")
            new_content = existing_content + logs_content
        except:
            # File doesn't exist yet
            new_content = logs_content

        # Upload the file
        await storage_client.upload(f"{project_id}/{file_path}", new_content.encode("utf-8"))

        # Get the public URL
        public_url = storage_client.get_public_url(f"{project_id}/{file_path}")

        # Update the session with the logs URL
        await supabase.table("sessions").update({"logs_url": public_url}).eq("id", session_id).execute()

        logger.info(colored(f"Completed logs update for session: {session_id}", "yellow"))
        return JSONResponse({"status": "success", "logs_url": public_url})

    except ExpiredJWTError:
        logger.warning("Expired JWT")
        return JSONResponse({"path": request.url.path, "message": "Expired Token"}, status_code=401)
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error updating logs: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(f"{request.url.path}: Error updating logs: {e} Could not read data: {log_error}")

        return JSONResponse(
            {
                "path": request.url.path,
                "message": f"Error updating logs: {e}",
            },
            status_code=400,
        )


@router.get("/ttd/{ttd_id}")
async def v2_get_ttd(ttd_id: str, request: Request, supabase: AsyncSupabaseClient):
    try:
        ttds_response = await supabase.table("ttd").select("*").eq("ttd_id", ttd_id).execute()
        return JSONResponse(ttds_response.data)
    except RuntimeError as e:
        logger.error(f"Error getting ttd: {e}")
        return JSONResponse(
            {"path": request.url.path, "message": f"Error getting ttd: {e}"},
            status_code=400,
        )


@router.post("/developer_errors")
async def v2_developer_errors(request: Request, supabase: AsyncSupabaseClient):
    try:
        data = await request.json()
        logger.debug(data)

        developer_error = {
            "api_key": request.headers.get("X-Agentops-Api-Key"),
            "sdk_version": data.get("sdk_version", None),
            "type": data.get("type", None),
            "message": data.get("message", None),
            "stack_trace": data.get("stack_trace", None),
            "host_env": data.get("host_env", None),
        }

        await supabase.table("developer_errors").insert(developer_error).execute()
        logger.info(
            colored(
                f"Completed request request for API Key: {request.headers.get('X-Agentops-Api-Key')}",
                "yellow",
            )
        )
        return JSONResponse("", status_code=204)
    except RuntimeError as e:
        try:
            data = await request.json()
            logger.error(f"{request.url.path}: Error posting developer_error: {e} Data received: {data}")
        except Exception as log_error:
            logger.error(
                f"{request.url.path}: Error posting developer_error: {e} Could not read data: {log_error}"
            )

        return JSONResponse(
            {
                "path": request.url.path,
                "message": f"Error posting developer_error: {e}",
            },
            status_code=400,
        )


@router.get("/sessions/{session_id}/stats")
async def v2_get_session_stats(session_id: str, request: Request, supabase: AsyncSupabaseClient):
    try:
        api_key = request.headers.get("X-Agentops-Api-Key")
        if api_key is None:
            raise RuntimeError("API Key is Missing")

        validate_uuid(api_key)

        # Get project ID from API key
        project_response = await supabase.table("projects").select("id").eq("api_key", api_key).execute()
        project = project_response.data[0] if project_response.data else None

        if not project:
            raise RuntimeError("Invalid API Key")

        # Check if session belongs to this project
        session_response = (
            await supabase.table("sessions")
            .select("id")
            .eq("id", session_id)
            .eq("project_id", project["id"])
            .execute()
        )
        if not session_response.data:
            raise RuntimeError("Session does not belong to this project")

        stats_response = await supabase.table("stats").select("*").eq("session_id", session_id).execute()
        stats = (
            stats_response.data[0]
            if stats_response.data
            else {
                "events": 0,
                "cost": "0.00",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "errors": 0,
            }
        )

        return JSONResponse(stats)

    except InvalidAPIKeyError as e:
        # This is a user error (invalid API key format), not a system error
        # Log as warning to avoid Sentry alerts
        logger.warning(f"{request.url.path}: Invalid API key format for session {session_id}")
        return JSONResponse({"path": request.url.path, "message": "Invalid API key format"}, status_code=400)
    except RuntimeError as e:
        logger.error(f"Error getting session stats: {e}")
        return JSONResponse({"path": request.url.path, "message": str(e)}, status_code=400)


@router.get("/sessions/{session_id}/export")
async def v2_export_session(session_id: str, request: Request, supabase: AsyncSupabaseClient):
    try:
        api_key = request.headers.get("X-Agentops-Api-Key")
        if api_key is None:
            raise RuntimeError("API Key is Missing")

        validate_uuid(api_key)

        # Get project ID from API key
        project_response = await supabase.table("projects").select("id").eq("api_key", api_key).execute()
        project = project_response.data[0] if project_response.data else None

        if not project:
            raise RuntimeError("Invalid API Key")

        # Check if session belongs to this project
        session_response = (
            await supabase.table("sessions")
            .select("id")
            .eq("id", session_id)
            .eq("project_id", project["id"])
            .execute()
        )
        if not session_response.data:
            raise RuntimeError("Session does not belong to this project")

        session_response = await supabase.table("sessions").select("*").eq("id", session_id).execute()
        actions_response = await supabase.table("actions").select("*").eq("session_id", session_id).execute()
        llms_response = await supabase.table("llms").select("*").eq("session_id", session_id).execute()
        tools_response = await supabase.table("tools").select("*").eq("session_id", session_id).execute()
        errors_response = await supabase.table("errors").select("*").eq("session_id", session_id).execute()

        export_data = {
            "session": session_response.data[0] if session_response.data else None,
            "actions": actions_response.data,
            "llms": llms_response.data,
            "tools": tools_response.data,
            "errors": errors_response.data,
        }

        return JSONResponse(export_data)

    except InvalidAPIKeyError as e:
        # This is a user error (invalid API key format), not a system error
        # Log as warning to avoid Sentry alerts
        logger.warning(f"{request.url.path}: Invalid API key format for session {session_id}")
        return JSONResponse({"path": request.url.path, "message": "Invalid API key format"}, status_code=400)
    except RuntimeError as e:
        logger.error(f"Error exporting session data: {e}")
        return JSONResponse({"path": request.url.path, "message": str(e)}, status_code=400)


@router.get("/openapi.yaml")
async def v2_openapi_yaml(request: Request):
    return JSONResponse(await request.send_file("openapi-spec-v2.yaml"))
