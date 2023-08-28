import json
import threading
import time
from .http import HttpClient
from .config import Configuration
from .event import Event, Session
from typing import Dict


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def filter_unjsonable(d):
    return {k: v for k, v in d.items() if is_jsonable(v)}


class Worker:
    def __init__(self, config: Configuration) -> None:
        self.config = config
        self.queue: list[Dict] = []
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def add_event(self, event: str) -> None:
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
                    "events": events
                }

                HttpClient.post(f'{self.config.endpoint}/events',
                                json.dumps(filter_unjsonable(
                                    payload)).encode("utf-8"),
                                self.config.api_key)

    def start_session(self, session: Session) -> None:
        with self.lock:
            payload = {
                "session": session.__dict__
            }

            HttpClient.post(f'{self.config.endpoint}/sessions',
                            json.dumps(filter_unjsonable(
                                payload)).encode("utf-8"),
                            self.config.api_key)

    def end_session(self, session: Session) -> None:
        self.stop_flag.set()
        self.thread.join()
        self.flush_queue()

        with self.lock:
            payload = {
                "session": session.__dict__
            }

            HttpClient.post(f'{self.config.endpoint}/sessions',
                            json.dumps(filter_unjsonable(
                                payload)).encode("utf-8"),
                            self.config.api_key)

    def run(self) -> None:
        while not self.stop_flag.is_set():
            time.sleep(self.config.max_wait_time / 1000)
            if self.queue:
                self.flush_queue()
