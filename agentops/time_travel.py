import json
import yaml
from .http_client import HttpClient
import os
from .helpers import singleton
from dotenv import load_dotenv
from .log_config import logger

load_dotenv()


@singleton
class TimeTravel:
    def __init__(self):
        self._completion_overrides_map = {}
        self._prompt_override_map = {}

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        cache_path = os.path.join(parent_dir, "agentops_time_travel.json")

        try:
            with open(cache_path, "r") as file:
                time_travel_cache_json = json.load(file)
                self._completion_overrides_map = time_travel_cache_json.get(
                    "completion_overrides"
                )
                self._prompt_override_map = time_travel_cache_json.get(
                    "prompt_override"
                )
        except FileNotFoundError:
            return


def fetch_time_travel_id(ttd_id):
    try:
        endpoint = "http://localhost:8000"
        payload = json.dumps({"ttd_id": ttd_id}).encode("utf-8")
        ttd_res = HttpClient.post(f"{endpoint}/v2/get_ttd", payload)
        if ttd_res.code != 200:
            raise Exception(
                f"Failed to fetch TTD with status code {ttd_res.status_code}"
            )

        prompt_to_returns_map = {
            "completion_overrides": {
                (
                    str({"messages": item["prompt"]["messages"]})
                    if item["prompt"].get("type") == "chatml"
                    else str(item["prompt"])
                ): item["returns"]
                for item in ttd_res.body  # TODO: rename returns to completion_override
            }
        }
        with open("agentops_time_travel.json", "w") as file:
            json.dump(prompt_to_returns_map, file, indent=4)

        set_time_travel_active_state("on")
    except Exception as e:
        manage_time_travel_state(activated=False, error=e)


def fetch_completion_override_from_time_travel_cache(kwargs):
    if not check_time_travel_active():
        return

    if TimeTravel()._completion_overrides_map:
        search_prompt = str({"messages": kwargs["messages"]})
        result_from_cache = TimeTravel()._completion_overrides_map.get(search_prompt)
        return result_from_cache


def fetch_prompt_override_from_time_travel_cache(kwargs):
    if not check_time_travel_active():
        return

    if TimeTravel()._prompt_override_map:
        search_prompt = str({"messages": kwargs["messages"]})
        result_from_cache = TimeTravel()._prompt_override_map.get(search_prompt)
        return json.loads(result_from_cache)


def check_time_travel_active():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        config_file_path = os.path.join(parent_dir, "agentops_time_travel.yaml")

        with open(config_file_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            if config.get("Time_Travel_Debugging_Active", True):
                # TODO: Find a way to only set background for cache hits or duration relevant to time travel.
                # May not be possible. Right now we will set the background color multiple times which is benign
                # but still not ideal
                manage_time_travel_state(activated=True)
                return True
    except FileNotFoundError:
        logger.error(
            "Time travel debugging failed -- Could not find agentops_time_travel.yaml"
        )
    except Exception as e:
        pass

    return False


def set_time_travel_active_state(active_setting):
    config_path = "agentops_time_travel.yaml"
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file) or {}
    except FileNotFoundError:
        config = {}

    config["Time_Travel_Debugging_Active"] = True if active_setting == "on" else False

    with open(config_path, "w") as config_file:
        try:
            yaml.dump(config, config_file)
        except:
            print(
                f"🖇 AgentOps: Unable to write to {config_path}. Time Travel not activated"
            )
            return

        if active_setting == "on":
            manage_time_travel_state(activated=True)
            print("AgentOps: Time Travel Activated")
        else:
            manage_time_travel_state(activated=False)
            print("🖇 AgentOps: Time Travel Deactivated")


def set_background_color_truecolor(r, g, b):
    print(f"🖇️ ⏰ | ", end="")


def reset_terminal_background_color():
    print("\033[0m", end="")


def manage_time_travel_state(activated=False, error=None):
    if activated:
        set_background_color_truecolor(147, 243, 250)  # lightblue
    else:
        reset_terminal_background_color()
        if error is not None:
            print(f"Deactivating Time Travel. Error with configuration: {error}")
