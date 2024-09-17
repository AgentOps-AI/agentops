import json
import yaml
import os
from .http_client import HttpClient
from .exceptions import ApiServerException
from .singleton import singleton

ttd_prepend_string = "🖇️ Agentops: ⏰ Time Travel |"


@singleton
class TimeTravel:
    def __init__(self):
        self._completion_overrides = {}

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        cache_path = os.path.join(parent_dir, "agentops_time_travel.json")

        try:
            with open(cache_path, "r") as file:
                time_travel_cache_json = json.load(file)
                self._completion_overrides = time_travel_cache_json.get(
                    "completion_overrides"
                )
        except FileNotFoundError:
            return


def fetch_time_travel_id(ttd_id):
    try:
        endpoint = os.environ.get("AGENTOPS_API_ENDPOINT", "https://api.agentops.ai")
        ttd_res = HttpClient.get(f"{endpoint}/v2/ttd/{ttd_id}")
        if ttd_res.code != 200:
            raise Exception(f"Failed to fetch TTD with status code {ttd_res.code}")

        completion_overrides = {
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
            json.dump(completion_overrides, file, indent=4)

        set_time_travel_active_state(True)
    except ApiServerException as e:
        print(f"{ttd_prepend_string} Error - {e}")
    except Exception as e:
        print(f"{ttd_prepend_string} Error - {e}")


def fetch_completion_override_from_time_travel_cache(kwargs):
    if not check_time_travel_active():
        return

    if TimeTravel()._completion_overrides:
        return find_cache_hit(kwargs["messages"], TimeTravel()._completion_overrides)


# NOTE: This is specific to the messages: [{'role': '...', 'content': '...'}, ...] format
def find_cache_hit(prompt_messages, completion_overrides):
    if not isinstance(prompt_messages, (list, tuple)):
        print(
            f"{ttd_prepend_string} Error - unexpected type for prompt_messages. Expected 'list' or 'tuple'. Got ",
            type(prompt_messages),
        )
        return None

    if not isinstance(completion_overrides, dict):
        print(
            f"{ttd_prepend_string} Error - unexpected type for completion_overrides. Expected 'dict'. Got ",
            type(completion_overrides),
        )
        return None
    for key, value in completion_overrides.items():
        try:
            completion_override_dict = eval(key)
            if not isinstance(completion_override_dict, dict):
                print(
                    f"{ttd_prepend_string} Error - unexpected type for completion_override_dict. Expected 'dict'. Got ",
                    type(completion_override_dict),
                )
                continue

            cached_messages = completion_override_dict.get("messages")
            if not isinstance(cached_messages, list):
                print(
                    f"{ttd_prepend_string} Error - unexpected type for cached_messages. Expected 'list'. Got ",
                    type(cached_messages),
                )
                continue

            if len(cached_messages) != len(prompt_messages):
                continue

            if all(
                isinstance(a, dict)
                and isinstance(b, dict)
                and a.get("content") == b.get("content")
                for a, b in zip(prompt_messages, cached_messages)
            ):
                return value
        except (SyntaxError, ValueError, TypeError) as e:
            print(
                f"{ttd_prepend_string} Error - Error processing completion_overrides item: {e}"
            )
        except Exception as e:
            print(
                f"{ttd_prepend_string} Error - Unexpected error in find_cache_hit: {e}"
            )
    return None


def check_time_travel_active():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    config_file_path = os.path.join(parent_dir, ".agentops_time_travel.yaml")

    try:
        with open(config_file_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            return config.get("Time_Travel_Debugging_Active", False)
    except FileNotFoundError:
        return False


def set_time_travel_active_state(is_active: bool):
    config_path = ".agentops_time_travel.yaml"
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file) or {}
    except FileNotFoundError:
        config = {}

    config["Time_Travel_Debugging_Active"] = is_active

    with open(config_path, "w") as config_file:
        try:
            yaml.dump(config, config_file)
        except:
            print(
                f"{ttd_prepend_string} Error - Unable to write to {config_path}. Time Travel not activated"
            )
            return

    if is_active:
        print(f"{ttd_prepend_string} Activated")
    else:
        print(f"{ttd_prepend_string} Deactivated")
