import platform
import psutil
import socket
from .helpers import get_agentops_version
from .log_config import logger
import importlib.metadata
import os
import sys


def get_sdk_details():
    try:
        return {
            "AgentOps SDK Version": get_agentops_version(),
            "Python Version": platform.python_version(),
            "System Packages": get_sys_packages(),
        }
    except:
        return {}


def get_python_details():
    try:
        return {"Python Version": platform.python_version()}
    except:
        return {}


def get_agentops_details():
    try:
        return {"AgentOps SDK Version": get_agentops_version()}
    except:
        return {}


def get_sys_packages():
    sys_packages = {}
    for module in sys.modules:
        try:
            version = importlib.metadata.version(module)
            sys_packages[module] = version
        except importlib.metadata.PackageNotFoundError:
            # Skip built-in modules and those without package metadata
            continue

    return sys_packages


def get_installed_packages():

    try:
        return {
            # TODO: test
            # TODO: add to opt out
            "Installed Packages": {
                dist.metadata["Name"]: dist.version
                for dist in importlib.metadata.distributions()
            }
        }
    except:
        return {}


def get_current_directory():
    try:
        return {"Project Working Directory": os.getcwd()}
    except:
        return {}


def get_virtual_env():
    try:
        return {"Virtual Environment": os.environ.get("VIRTUAL_ENV", None)}
    except:
        return {}


def get_os_details():
    try:
        return {
            "Hostname": socket.gethostname(),
            "OS": platform.system(),
            "OS Version": platform.version(),
            "OS Release": platform.release(),
        }
    except:
        return {}


def get_cpu_details():
    try:
        return {
            "Physical cores": psutil.cpu_count(logical=False),
            "Total cores": psutil.cpu_count(logical=True),
            # "Max Frequency": f"{psutil.cpu_freq().max:.2f}Mhz", # Fails right now
            "CPU Usage": f"{psutil.cpu_percent()}%",
        }
    except:
        return {}


def get_ram_details():
    try:
        ram_info = psutil.virtual_memory()
        return {
            "Total": f"{ram_info.total / (1024 ** 3):.2f} GB",
            "Available": f"{ram_info.available / (1024 ** 3):.2f} GB",
            "Used": f"{ram_info.used / (1024 ** 3):.2f} GB",
            "Percentage": f"{ram_info.percent}%",
        }
    except:
        return {}


def get_disk_details():
    partitions = psutil.disk_partitions()
    disk_info = {}
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info[partition.device] = {
                "Mountpoint": partition.mountpoint,
                "Total": f"{usage.total / (1024**3):.2f} GB",
                "Used": f"{usage.used / (1024**3):.2f} GB",
                "Free": f"{usage.free / (1024**3):.2f} GB",
                "Percentage": f"{usage.percent}%",
            }
        except OSError as inaccessible:
            # Skip inaccessible partitions, such as removable drives with no media
            logger.debug(
                "Mountpoint %s inaccessible: %s", partition.mountpoint, inaccessible
            )

    return disk_info


def get_host_env(opt_out: bool = False):
    if opt_out:
        return {
            "SDK": get_sdk_details(),
            "OS": get_os_details(),
            "Project Working Directory": get_current_directory(),
            "Virtual Environment": get_virtual_env(),
        }
    else:
        return {
            "SDK": get_sdk_details(),
            "OS": get_os_details(),
            "CPU": get_cpu_details(),
            "RAM": get_ram_details(),
            "Disk": get_disk_details(),
            "Installed Packages": get_installed_packages(),
            "Project Working Directory": get_current_directory(),
            "Virtual Environment": get_virtual_env(),
        }
