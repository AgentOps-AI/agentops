from opentelemetry import trace

import agentops
from agentops.session import Session


def main():
    session = Session(tags=["demo", "basic-tracing"])

if __name__ == "__main__":
    main() 
