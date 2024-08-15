import json
import yaml
import os
from .http_client import HttpClient
from .exceptions import ApiServerException
from .helpers import singleton


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
        endpoint = os.environ.get("AGENTOPS_API_ENDPOINT", "https://api.agentops.ai")
        ttd_res = HttpClient.get(f"{endpoint}/v2/ttd/{ttd_id}")
        if ttd_res.code != 200:
            raise Exception(f"Failed to fetch TTD with status code {ttd_res.code}")

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

        set_time_travel_active_state(True)
    except ApiServerException as e:
        manage_time_travel_state(activated=False, error=e)
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
        prompt_messages = kwargs["messages"]

        find_cache_hit(prompt_messages, TimeTravel()._prompt_override_map)

        # def find_cache_hit(listA, listB):
        #     for item in listB:
        #         for key, value in item.items():
        #             if (
        #                 isinstance(key, list)
        #                 and len(key) == len(listA)
        #                 and all(a == c for a, c in zip(listA, key))
        #             ):
        #                 return value
        #     return None  # Return None if no match is found

        # matched_prompt = None
        # continue_to_next_prompt_message = False

        # for i in range(len(prompt_messages)):
        #     try:
        #         for key in TimeTravel()._prompt_override_map.keys():
        #             matched_prompt = TimeTravel()._prompt_override_map[key]
        #             try:
        #                 cached_messages = json.loads(key).get("messages", [])
        #                 if len(prompt_messages) != len(cached_messages):
        #                     continue

        #                 if (
        #                     prompt_messages[i]["content"]
        #                     == cached_messages[i]["content"]
        #                 ):
        #                     continue_to_next_prompt_message = True
        #                 else:
        #                     return

        #             except (json.JSONDecodeError, ValueError) as e:
        #                 pass  # TODO
        #             except KeyError as e:
        #                 pass  # TODO
        #     except KeyError as e:
        #         pass  # TODO

        # return matched_prompt


def find_cache_hit(listA, mapA):
    for key, value in mapA.items():
        print(f"key: {key}")
        print(f"value: {value}")
        if isinstance(key, list) and len(key) == len(listA):
            print(f"listA: {listA}")
            if all(a["content"] == b["content"] for a, b in zip(listA, key)):
                return value
    return None


def check_time_travel_active():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    config_file_path = os.path.join(parent_dir, ".agentops_time_travel.yaml")

    try:
        with open(config_file_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            if config.get("Time_Travel_Debugging_Active", True):
                manage_time_travel_state(activated=True)
                return True
    except FileNotFoundError:
        return False

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
                f"🖇 AgentOps: Unable to write to {config_path}. Time Travel not activated"
            )
            return

        if is_active:
            manage_time_travel_state(activated=True)
            print("AgentOps: Time Travel Activated")
        else:
            manage_time_travel_state(activated=False)
            print("🖇 AgentOps: Time Travel Deactivated")


def add_time_travel_terminal_indicator():
    print(f"🖇️ ⏰ | ", end="")


def reset_terminal():
    print("\033[0m", end="")


def manage_time_travel_state(activated=False, error=None):
    if activated:
        add_time_travel_terminal_indicator()
    else:
        reset_terminal()
        if error is not None:
            print(f"🖇 Deactivating Time Travel. Error with configuration: {error}")
