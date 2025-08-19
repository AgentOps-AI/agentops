from pathlib import Path
from dotenv import load_dotenv

# Load test environment before importing anything else
load_dotenv(Path(__file__).parent.parent / "tests/.env", override=True)

from ._conftest.common import *
from ._conftest.app import *
from ._conftest.supabase import *
from ._conftest.clickhouse import *
from ._conftest.users import *
from ._conftest.projects import *
