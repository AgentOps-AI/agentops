from unittest.mock import patch
from agentops import host_env

# noinspection PyProtectedMember
from psutil._common import sdiskpart, sdiskusage


def mock_partitions():
    return [
        sdiskpart(
            device="/dev/sda1",
            mountpoint="/",
            fstype="ext4",
            opts="rw,relatime",
            maxfile=0,
            maxpath=0,
        ),
        sdiskpart(
            device="z:\\",
            mountpoint="z:\\",
            fstype="ntfs",
            opts="rw,relatime",
            maxfile=0,
            maxpath=0,
        ),
    ]


def mock_disk_usage(partition):
    if partition == "/":
        return sdiskusage(total=(1024**3), used=0, free=(1024**3), percent=100)
    else:
        raise PermissionError("Device access exception should have been caught")


class TestHostEnv:
    @patch("psutil.disk_partitions", new=lambda: [mock_partitions()[0]])
    @patch("psutil.disk_usage", new=mock_disk_usage)
    def test_disk_info(self):
        self.assert_disk_info()

    @patch("psutil.disk_partitions", new=mock_partitions)
    @patch("psutil.disk_usage", new=mock_disk_usage)
    def test_disk_info_skips_oserror(self):
        self.assert_disk_info()

    def assert_disk_info(self):
        disk_info = host_env.get_disk_details()
        assert list(disk_info.keys()) == ["/dev/sda1"]
        sda1 = disk_info["/dev/sda1"]
        assert sda1["Mountpoint"] == "/"
        assert sda1["Total"] == "1.00 GB"
        assert sda1["Used"] == "0.00 GB"
        assert sda1["Free"] == "1.00 GB"
        assert sda1["Percentage"] == "100%"
