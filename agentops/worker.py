import json
import threading
import time
from .http_client import HttpClient
from .config import Configuration
from .session import Session
from .helpers import safe_serialize, filter_unjsonable
from typing import Dict, Optional
import os


class Worker:
    def __init__(self, config: Configuration) -> None:
        self.config = config
        self.queue: list[Dict] = []
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()
        self._session: Optional[Session] = None
        self._debug_mode = os.getenv('DEBUG_MODE') == 'Y'

    def add_event(self, event: dict) -> None:
        with self.lock:
            self.queue.append(event)
            if len(self.queue) >= self.config.max_queue_size:
                self.flush_queue()

    def flush_queue(self) -> None:
        with self.lock:
            if len(self.queue) > 0:
                events = self.queue
                self.queue = []

                payload = {
                    "session_id": getattr(self._session, "session_id", None),
                    "events": events
                }

                serialized_payload = safe_serialize(payload).encode("utf-8")
                HttpClient.post(f'{self.config.endpoint}/events',
                                serialized_payload,
                                self.config.api_key,
                                self.config.parent_key)

                if self._debug_mode:
                    print("\n<AGENTOPS_DEBUG_OUTPUT>")
                    print(f"Worker request to {self.config.endpoint}/events")
                    print(serialized_payload)
                    print("</AGENTOPS_DEBUG_OUTPUT>\n")

    def start_session(self, session: Session) -> bool:
        self._session = session
        with self.lock:
            payload = {
                "session": session.__dict__
            }
            serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")
            res = HttpClient.post(f'{self.config.endpoint}/sessions',
                                  serialized_payload,
                                  self.config.api_key,
                                  self.config.parent_key)

            if res.code != 200:
                return False

            return True

    def end_session(self, session: Session) -> str:
        self.stop_flag.set()
        self.thread.join(timeout=1)
        self.flush_queue()
        self._session = None

        with self.lock:
            payload = {
                "session": session.__dict__
            }

            res = HttpClient.post(f'{self.config.endpoint}/sessions',
                            json.dumps(filter_unjsonable(
                                payload)).encode("utf-8"),
                            self.config.api_key,
                            self.config.parent_key)

            return res.body.get('token_cost', "unknown")

    def update_session(self, session: Session) -> None:
        with self.lock:
            payload = {
                "session": session.__dict__
            }

            HttpClient.post(f'{self.config.endpoint}/sessions',
                            json.dumps(filter_unjsonable(
                                payload)).encode("utf-8"),
                            self.config.api_key,
                            self.config.parent_key)

    def create_agent(self, agent_id, name):
        payload = {
            "id": agent_id,
            "name": name,
            "session_id": getattr(self._session, "session_id", None),
        }

        serialized_payload = \
            safe_serialize(payload).encode("utf-8")
        HttpClient.post(f'{self.config.endpoint}/agents',
                        serialized_payload,
                        self.config.api_key,
                        self.config.parent_key)

    def run(self) -> None:
        while not self.stop_flag.is_set():
            time.sleep(self.config.max_wait_time / 1000)
            if self.queue:
                self.flush_queue()
