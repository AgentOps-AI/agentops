import json
import os
from uuid import UUID

from .log_config import logger
import threading
import time
from .http_client import HttpClient
from .config import ClientConfiguration
from .helpers import safe_serialize, filter_unjsonable
from typing import Dict, Optional, List, Union
import copy


class QueueSession:
    events: List[Dict] = []
    jwt: str = None


class Worker:
    def __init__(self, config: ClientConfiguration) -> None:
        self.config = config
        self.queue: Dict[str, QueueSession] = {}
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def add_event(self, event: dict, session_id: Union[str, UUID]) -> None:
        session_id = str(session_id)
        with self.lock:
            if session_id in self.queue.keys():
                self.queue[session_id].events.append(event)
            else:
                self.queue[session_id].events = [event]

            if len(self.queue[session_id].events) >= self.config.max_queue_size:
                self.flush_queue()

    def flush_queue(self) -> None:
        with self.lock:
            queue_copy = copy.deepcopy(self.queue)  # Copy the current items

            # clear events from queue
            for session_id in self.queue.keys():
                self.queue[session_id].events = []

            if len(queue_copy.keys()) > 0:
                for session_id, queue_session in queue_copy.items():
                    if len(queue_copy[session_id].events) > 0:
                        payload = {
                            "events": queue_session.events,
                        }

                        serialized_payload = safe_serialize(payload).encode("utf-8")
                        HttpClient.post(
                            f"{self.config.endpoint}/v2/create_events",
                            serialized_payload,
                            jwt=queue_session.jwt,
                        )

                        logger.debug("\n<AGENTOPS_DEBUG_OUTPUT>")
                        logger.debug(f"Worker request to {self.config.endpoint}/events")
                        logger.debug(serialized_payload)
                        logger.debug("</AGENTOPS_DEBUG_OUTPUT>\n")

    def create_agent(self, agent_id, name, session_id: str):
        payload = {
            "id": agent_id,
            "name": name,
            "session_id": session_id,
        }

        serialized_payload = safe_serialize(payload).encode("utf-8")
        HttpClient.post(
            f"{self.config.endpoint}/v2/create_agent", serialized_payload, jwt=self.jwt
        )

    def run(self) -> None:
        while not self.stop_flag.is_set():
            time.sleep(self.config.max_wait_time / 1000)
            if self.queue:
                self.flush_queue()
