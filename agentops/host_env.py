import platform
import psutil
import socket


def get_os_details():
    return {
        "Hostname": socket.gethostname(),
        "OS": platform.system(),
        "OS Version": platform.version(),
        "OS Release": platform.release()
    }


def get_cpu_details():
    return {
        "Physical cores": psutil.cpu_count(logical=False),
        "Total cores": psutil.cpu_count(logical=True),
        "Max Frequency": f"{psutil.cpu_freq().max:.2f}Mhz",
        "CPU Usage": f"{psutil.cpu_percent()}%"
    }


def get_ram_details():
    ram_info = psutil.virtual_memory()
    return {
        "Total": f"{ram_info.total / (1024**3):.2f} GB",
        "Available": f"{ram_info.available / (1024**3):.2f} GB",
        "Used": f"{ram_info.used / (1024**3):.2f} GB",
        "Percentage": f"{ram_info.percent}%"
    }


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


def get_host_env():
    return {
        "OS": get_os_details(),
        "CPU": get_cpu_details(),
        "RAM": get_ram_details(),
        "Disk": get_disk_details(),
    }


if __name__ == "__main__":
    print("Gathering system information...")
    print("OS Details:", get_os_details())
    print("CPU Details:", get_cpu_details())
    print("RAM Details:", get_ram_details())
    print("Disk Details:", get_disk_details())
