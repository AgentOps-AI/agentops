import pytest
from .conftest import (
    get_api_requests, 
    get_otel_requests, 
    assert_otel_requests_are_unique, 
    assert_instrumentation_is_loaded, 
)

import autogen
import agentops

# TODO VCR causes a timeout with autogen requests. 
#pytestmark = [pytest.mark.vcr]


@pytest.mark.asyncio
async def test_instrumentation_is_loaded():
    assert_instrumentation_is_loaded("autogen")


@pytest.mark.asyncio
async def test_autogen_single_agent(vcr):
    """Test a single agent with Autogen"""
    
    agentops.init()
    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config={
            "config_list": [{"model": "gpt-3.5-turbo"}],
            "temperature": 0
        },
        system_message="You are a helpful assistant. Be brief in your responses."
    )
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1
    )
    user_proxy.initiate_chat(
        assistant,
        message="Tell me a short joke"
    )
    agentops.end_session("Succeeded")
    
    if vcr is None:
        print("VCR is None, skipping assertions")
        return
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_autogen_function_call(vcr):
    """Test an Autogen agent using function calling"""
    
    def get_weather(location):
        return f"The weather in {location} is sunny and 72 degrees Fahrenheit."
    
    agentops.init()
    assistant = autogen.AssistantAgent(
        name="function_assistant",
        llm_config={
            "config_list": [{"model": "gpt-3.5-turbo"}],
            "functions": [
                {
                    "name": "get_weather",
                    "description": "Get the current weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA"
                            }
                        },
                        "required": ["location"]
                    }
                }
            ]
        },
        system_message="You are a helpful assistant who can check the weather."
    )
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        code_execution_config={"work_dir": ".", "get_weather": get_weather}
    )
    user_proxy.initiate_chat(
        assistant,
        message="How's the weather in San Francisco?"
    )
    agentops.end_session("Succeeded")
    
    if vcr is None:
        print("VCR is None, skipping assertions")
        return
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_autogen_multi_agent_conversation(vcr):
    """Test multiple Autogen agents working together"""
    
    agentops.init()
    manager = autogen.AssistantAgent(
        name="manager",
        llm_config={
            "config_list": [{"model": "gpt-3.5-turbo"}],
            "temperature": 0
        },
        system_message="""You are a project manager. You delegate tasks and coordinate between team members.
        Keep your responses brief and focused on task coordination."""
    )
    researcher = autogen.AssistantAgent(
        name="researcher",
        llm_config={
            "config_list": [{"model": "gpt-3.5-turbo"}],
            "temperature": 0
        },
        system_message="""You are a research specialist. You gather and summarize information.
        Keep your responses brief and informative."""
    )
    writer = autogen.AssistantAgent(
        name="writer",
        llm_config={
            "config_list": [{"model": "gpt-3.5-turbo"}],
            "temperature": 0
        },
        system_message="""You are a content writer. You create clear and engaging text.
        Keep your responses brief and well-structured."""
    )
    user_proxy = autogen.UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1
    )
    groupchat = autogen.GroupChat(
        agents=[user_proxy, manager, researcher, writer],
        messages=[],
        max_round=4
    )
    group_chat_manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config={
            "config_list": [{"model": "gpt-3.5-turbo"}],
            "temperature": 0
        }
    )
    user_proxy.initiate_chat(
        group_chat_manager,
        message="Write a brief summary about renewable energy"
    )
    agentops.end_session("Succeeded")
    
    if vcr is None:
        print("VCR is None, skipping assertions")
        return
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert_otel_requests_are_unique(vcr)