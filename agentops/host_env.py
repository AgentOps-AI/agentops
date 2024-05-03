import platform
import psutil
import socket
from .helpers import get_agentops_version


def get_sdk_details():
    try:
        return {
            "AgentOps SDK Version": get_agentops_version(),
            "Python Version": platform.python_version(),
        }
    except:
        return {}


def get_os_details():
    try:
        return {
            "Hostname": socket.gethostname(),
            "OS": platform.system(),
            "OS Version": platform.version(),
            "OS Release": platform.release()
        }
    except:
        return {}


def get_cpu_details():
    try:
        return {
            "Physical cores": psutil.cpu_count(logical=False),
            "Total cores": psutil.cpu_count(logical=True),
            # "Max Frequency": f"{psutil.cpu_freq().max:.2f}Mhz", # Fails right now
            "CPU Usage": f"{psutil.cpu_percent()}%"
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
            "Percentage": f"{ram_info.percent}%"
        }
    except:
        return {}



def get_disk_details():
    partitions = psutil.disk_partitions()
    disk_info = {}
    for partition in partitions:
        usage = psutil.disk_usage(partition.mountpoint)
        disk_info[partition.device] = {
            "Mountpoint": partition.mountpoint,
            "Total": f"{usage.total / (1024**3):.2f} GB",
            "Used": f"{usage.used / (1024**3):.2f} GB",
            "Free": f"{usage.free / (1024**3):.2f} GB",
            "Percentage": f"{usage.percent}%"
        }
    return disk_info


def get_host_env(opt_out: bool = False):
    if opt_out:
        return {
            "SDK": get_sdk_details(),
            "OS": get_os_details()
        }
    else:
        return {
            "SDK": get_sdk_details(),
            "OS": get_os_details(),
            "CPU": get_cpu_details(),
            "RAM": get_ram_details(),
            "Disk": get_disk_details(),
        }
