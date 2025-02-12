#################
# DEBUGGER SETUP
import sys


def info(type, value, tb):
    if hasattr(sys, "ps1") or not sys.stderr.isatty():
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import pdb
        import traceback

        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        # ...then start the debugger in post-mortem mode.
        # pdb.pm() # deprecated
        pdb.post_mortem(tb)  # more "modern"


sys.excepthook = info
#################


import os

os.putenv("TESTING", "1")

import agentops
from agentops.decorators import record_function
from agentops.session.session import Session

agentops.init(auto_start_session=False)
s = agentops.start_session()


assert isinstance(s, Session)


@record_function("boo")
def foo():
    breakpoint()
    print("1")


foo()


s.end_session()
