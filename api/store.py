"""Bounded, expiring, process-local sessions. No filesystem persistence."""
from dataclasses import dataclass, field
import secrets
import threading
import time


@dataclass
class Entry:
    expires: float
    datasets: dict = field(default_factory=dict)


class SessionStore:
    def __init__(self, ttl=3600, capacity=32, datasets_per_session=4):
        self.ttl = ttl
        self.capacity = capacity
        self.datasets_per_session = datasets_per_session
        self.entries = {}
        self.lock = threading.RLock()

    def prune(self):
        now = time.monotonic()
        for token in list(self.entries):
            if self.entries[token].expires <= now:
                del self.entries[token]

    def create(self):
        with self.lock:
            self.prune()
            if len(self.entries) >= self.capacity:
                raise OverflowError("Session capacity reached")
            token = secrets.token_urlsafe(32)
            self.entries[token] = Entry(time.monotonic() + self.ttl)
            return token

    def session(self, token):
        self.prune()
        if token not in self.entries:
            raise KeyError("Unknown or expired session")
        return self.entries[token]

    def check(self, token):
        with self.lock:
            self.session(token)

    def put(self, token, payload, response):
        with self.lock:
            session = self.session(token)
            if len(session.datasets) >= self.datasets_per_session:
                raise OverflowError("Dataset capacity reached; delete a dataset first")
            session.datasets[response["dataset_id"]] = (payload, response)

    def get(self, token, dataset_id):
        with self.lock:
            return self.session(token).datasets[dataset_id]

    def delete(self, token, dataset_id=None):
        with self.lock:
            session = self.session(token)
            if dataset_id is None:
                del self.entries[token]
            else:
                del session.datasets[dataset_id]
