import asyncio
from decimal import Decimal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import agentops.api.event_handlers as event_handlers
import agentops.api.interactors.spans as span_handlers
from agentops.api.db.supabase_client import AsyncSupabaseClient
from agentops.api.exceptions import InvalidModelError
from agentops.api.log_config import logger
from agentops.api.utils import update_stats

# Create a router for v1 endpoints
router = APIRouter(prefix="/v1")


@router.post("/sessions")
async def create_session(request: Request, supabase: AsyncSupabaseClient):
    """Create a new session"""
    try:
        api_key = request.headers.get("X-Agentops-Auth")
        parent_key = request.headers.get("X-Agentops-Parent-Key")

        tasks = [
            supabase.table("projects").select("id").eq("api_key", api_key).limit(1).single().execute(),
            request.json(),
        ]

        if parent_key:
            tasks.append(
                supabase.table("projects").select("id").eq("api_key", parent_key).limit(1).single().execute()
            )
            project, data, project_secondary = await asyncio.gather(*tasks)
        else:
            project, data = await asyncio.gather(*tasks)
            project_secondary = None

        logger.debug(data)

        if project is None:
            raise RuntimeError("Invalid API Key")

    except RuntimeError as e:
        message = {"message": f"/sessions: Error posting session: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=401)

    try:
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

        await supabase.table("sessions").upsert(session).execute()
        await supabase.table("stats").upsert({"session_id": session["id"]}).execute()

        cost = await (
            supabase.table("stats").select("cost").eq("session_id", session["id"]).limit(1).single().execute()
        )

        logger.info(f"/session: Completed POST request for {session['id']}")
        if cost is not None:
            return JSONResponse(
                {
                    "status": "success",
                    "token_cost": cost.get("cost", "0.00") or "0.00",
                }
            )
        return JSONResponse({"status": "success"})
    except RuntimeError as e:
        message = {"message": f"/sessions: Error posting session: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=400)


@router.post("/agents")
async def agents(request: Request, supabase: AsyncSupabaseClient):
    try:
        api_key = request.headers.get("X-Agentops-Auth")

        sessions, data = await asyncio.gather(
            supabase.table("sessions").select("id").eq("api_key", api_key).limit(1).single().execute(),
            request.json(),
        )

        session_ids = [session["id"] for session in sessions]
        if data["session_id"] not in session_ids:
            raise RuntimeError("Invalid API Key for Session")

        logger.debug(data)

    except RuntimeError as e:
        message = {"message": f"/agents: Error creating agent: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=401)

    try:
        agent = {
            "id": data["id"],
            "session_id": data["session_id"],
            "name": data.get("name", None),
            "logs": data.get("logs", None),
        }

        await supabase.table("agents").upsert(agent).execute()

        logger.info(f"/agents: Completed POST request for {agent['id']}")
        return JSONResponse("Success")
    except RuntimeError as e:
        message = {"message": f"/agents: Error creating agent: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=400)


@router.post("/threads")
async def threads(request: Request, supabase: AsyncSupabaseClient):
    try:
        api_key = request.headers.get("X-Agentops-Auth")

        sessions, data = await asyncio.gather(
            supabase.table("sessions").select("id").eq("api_key", api_key).limit(1).single().execute(),
            request.json(),
        )

        session_ids = [session["id"] for session in sessions]
        if data["threads"]["session_id"] not in session_ids:
            raise RuntimeError("Invalid API Key for Session")

        logger.debug(data)

    except RuntimeError as e:
        message = {"message": f"/threads: Error creating thread: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=401)

    try:
        thread = {
            "id": data["threads"]["id"],
            "session_id": data["threads"]["session_id"],
            "agent_id": data["threads"].get("agent_id", None),
        }

        await supabase.table("threads").upsert(thread).execute()

        logger.info(f"/threads: Completed POST request for {thread['id']}")
        return JSONResponse("Success")
    except RuntimeError as e:
        message = {"message": f"/threads: Error creating agent: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=400)


@router.post("/events")
async def events(request: Request, supabase: AsyncSupabaseClient):
    try:
        api_key = request.headers.get("X-Agentops-Auth")

        sessions, data = await asyncio.gather(
            supabase.table("sessions").select("id").eq("api_key", api_key).limit(1).single().execute(),
            request.json(),
        )
        # premium_status = await get_premium_status(supabase, sessions['id'])
        premium_status = False

        session_id = data.get("session_id")
        session_ids_for_project = [session["id"] for session in sessions]
        if session_id not in session_ids_for_project:
            raise RuntimeError("Invalid API Key for session")

    except RuntimeError as e:
        message = {"message": f"/events: Error posting event: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=401)

    except InvalidModelError as e:
        message = {"message": f"/events: Invalid model while posting event: {e}"}
        return JSONResponse(message, status_code=401)

    try:
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
            # TODO: move into an /errors endpoint?
            elif event["event_type"] == "errors":
                errors.append(await event_handlers.handle_errors(event, session_id))
            else:
                actions.append(await event_handlers.handle_actions(event, session_id))

        if additional_cost == Decimal(0):
            additional_cost = None

        inserts = []
        if len(actions) != 0:
            inserts.append(supabase.table("actions").upsert(actions).execute())
        if len(llms) != 0:
            inserts.append(supabase.table("llms").upsert(llms).execute())
        if len(tools) != 0:
            inserts.append(supabase.table("tools").upsert(tools).execute())
        if len(errors) != 0:
            inserts.append(supabase.table("errors").upsert(errors).execute())

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

        logger.info(f"/events: Completed POST request for {api_key}")
        return JSONResponse("Success")
    except RuntimeError as e:
        message = {"message": f"/events: Error posting event: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=400)


@router.post("/developer_errors")
async def developer_errors(request: Request, supabase: AsyncSupabaseClient):
    try:
        data = await request.json()
        logger.debug(data)

        developer_error = {
            "api_key": request.headers.get("X-Agentops-Auth"),
            "session_id": data.get("session_id", None),
            "sdk_version": data.get("sdk_version", None),
            "type": data.get("type", None),
            "message": data.get("message", None),
            "stack_trace": data.get("stack_trace", None),
            "host_env": data.get("host_env", None),
        }

        await supabase.table("developer_errors").upsert(developer_error).execute()
        logger.info(f"/developer_errors: Completed POST request for {request.headers.get('X-Agentops-Auth')}")
        return JSONResponse("", status_code=204)
    except RuntimeError as e:
        message = {"message": f"/developer_errors: Error posting developer_error: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=400)


@router.post("/traces")
async def traces(request: Request, supabase: AsyncSupabaseClient):
    """Ingest OpenTelemetry spans"""
    try:
        api_key = request.headers.get("X-Agentops-Auth")

        sessions, data = await asyncio.gather(
            supabase.table("sessions").select("id").eq("api_key", api_key).limit(1).single().execute(),
            request.json(),
        )

        session_id = data.get("session_id")
        session_ids_for_project = [session["id"] for session in sessions]
        if session_id not in session_ids_for_project:
            raise RuntimeError("Invalid API Key for session")

        logger.debug(data)

    except RuntimeError as e:
        message = {"message": f"/traces: Error processing spans: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=401)

    try:
        spans_data = []
        for span in data.get("spans", []):
            # Classify the span
            span_type = await span_handlers.classify_span(span)

            # Route to the appropriate handler
            if span_type == span_handlers.SESSION_UPDATE_SPAN:
                span_data = await span_handlers.handle_session_update_span(span, session_id)
            elif span_type == span_handlers.GEN_AI_SPAN:
                span_data = await span_handlers.handle_gen_ai_span(span, session_id)
            elif span_type == span_handlers.LOG_SPAN:
                span_data = await span_handlers.handle_log_span(span, session_id)
            else:
                # Default to session update handler
                span_data = await span_handlers.handle_session_update_span(span, session_id)

            spans_data.append(span_data)

        # Insert spans into the database
        if spans_data:
            await supabase.table("spans").upsert(spans_data).execute()

        logger.info(f"/traces: Completed POST request for {api_key}")
        return JSONResponse({"status": "success"})
    except RuntimeError as e:
        message = {"message": f"/traces: Error processing spans: {e}"}
        logger.error(message)
        return JSONResponse(message, status_code=400)


# @router.get("/openapi.yaml")
# async def openapi_yaml(request: Request):
#     with open("openapi-spec.yaml", "r") as f:
#         content = f.read()
#     return Response(content=content, media_type="text/yaml")
