"""Paced, bounded HTTP load using only the Python standard library."""

import json
import logging
import math
import os
import signal
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def number(name, default, *, allow_zero=False):
    value = float(os.getenv(name, default))
    if not math.isfinite(value) or value < 0 or (not allow_zero and value == 0):
        raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")
    return value


def rate_at(elapsed, start_rps, target_rps, ramp_seconds):
    fraction = min(max(elapsed / ramp_seconds, 0), 1)
    return start_rps + (target_rps - start_rps) * fraction


@dataclass
class Target:
    url: str
    ordinal: int = 0
    item_id: int | None = None
    statuses: Counter = field(default_factory=Counter)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def next_request(self):
        with self.lock:
            index = self.ordinal
            self.ordinal += 1
            item_id = self.item_id
        # Per target, every 100 requests have two validation errors and two misses.
        slot = index % 100
        if slot in (96, 97):
            if slot == 97 and item_id is not None:
                return "PUT", f"/items/{item_id}", {}, 400
            return "POST", "/items", {}, 400
        if slot in (98, 99):
            if slot == 99:
                return "PUT", "/items/-1", {"name": "missing"}, 404
            return "GET", "/items/-1", None, 404
        body = {"name": f"load-{index}", "description": "background load"}
        if item_id is None or index % 3 == 0:
            return "POST", "/items", body, 201
        if index % 3 == 1:
            return "GET", f"/items/{item_id}", None, 200
        return "PUT", f"/items/{item_id}", body, 200


def execute(target, operation, timeout):
    method, path, body, expected = operation
    request = Request(target.url + path, method=method,
                      data=None if body is None else json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    try:
        try:
            with urlopen(request, timeout=timeout) as response:
                status = response.status
                payload = response.read()
        except HTTPError as response:
            with response:
                status = response.code
                payload = response.read()
        if status == 201:
            with target.lock:
                target.item_id = json.loads(payload)["id"]
        with target.lock:
            target.statuses[str(status)] += 1
            if status != expected:
                target.statuses["unexpected"] += 1
    except (URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        with target.lock:
            target.statuses["transport_error"] += 1
        logging.warning("%s %s: %s", method, target.url + path, error)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    urls = os.getenv("TARGET_URLS", "http://app:8080,http://app-2:8080").split(",")
    targets = [Target(url.strip().rstrip("/")) for url in urls]
    if not targets or any(urlparse(t.url).scheme not in ("http", "https")
                          or not urlparse(t.url).netloc for t in targets):
        raise ValueError("TARGET_URLS must contain comma-separated HTTP(S) URLs")
    start_rps = number("START_RPS", "1")
    target_rps = number("TARGET_RPS", "30")
    ramp_seconds = number("RAMP_SECONDS", "180")
    timeout = number("REQUEST_TIMEOUT", "3")
    duration = number("RUN_SECONDS", "0", allow_zero=True)
    if start_rps > target_rps:
        raise ValueError("START_RPS must not exceed TARGET_RPS")
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    slots = threading.BoundedSemaphore(8)
    started = time.monotonic()
    next_request = started
    last_report = started
    previous_completed = 0
    sent = skipped = 0

    def report():
        nonlocal last_report, previous_completed
        now = time.monotonic()
        statuses = {}
        for target in targets:
            with target.lock:
                statuses[target.url] = dict(target.statuses)
        completed = sum(value for counters in statuses.values()
                        for key, value in counters.items() if key.isdigit())
        logging.info(json.dumps({"elapsed_s": round(now - started, 1),
                                 "scheduled_rps": round(rate_at(now - started, start_rps, target_rps, ramp_seconds), 2),
                                 "actual_rps": round((completed - previous_completed) / max(now - last_report, .001), 2),
                                 "sent": sent, "skipped": skipped, "statuses": statuses}))
        last_report, previous_completed = now, completed

    logging.info("Load: %s, %.1f -> %.1f total RPS over %.1fs; 2%% HTTP 400 + 2%% HTTP 404 per target",
                 urls, start_rps, target_rps, ramp_seconds)
    with ThreadPoolExecutor(max_workers=8) as executor:
        while not stop.is_set():
            now = time.monotonic()
            if duration and now - started >= duration:
                break
            if now - last_report >= 10:
                report()
            if now < next_request:
                stop.wait(min(next_request - now, .5))
                continue
            rate = rate_at(now - started, start_rps, target_rps, ramp_seconds)
            # Do not catch up with a burst after delays; never queue unlimited work.
            next_request = max(next_request + 1 / rate, now + 1 / rate)
            if slots.acquire(blocking=False):
                target = targets[sent % len(targets)]
                operation = target.next_request()
                future = executor.submit(execute, target, operation, timeout)
                future.add_done_callback(lambda _: slots.release())
                sent += 1
            else:
                skipped += 1
    report()


if __name__ == "__main__":
    main()
