import time
from collections import deque

class TokenBucket:
    def __init__(self, rate: int, per_seconds: int):
        self.capacity = rate
        self.tokens = rate
        self.per = per_seconds
        self.queue = deque()
        self.last = time.time()

    def allow(self) -> bool:
        now = time.time()
        elapsed = now - self.last
        self.last = now
        self.tokens = min(self.capacity, self.tokens + elapsed * (self.capacity / self.per))
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
