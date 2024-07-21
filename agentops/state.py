state_dict = {}


def set_state(key: str, value: any):
    state_dict[key] = value


def get_state(key: str) -> any:
    return state_dict.get(key)
