import threading
import time
import queue
from datetime import datetime

import database

# Global SSE subscribers: list of queue.Queue instances
_log_subscribers = []
_log_subscribers_lock = threading.Lock()

def subscribe_logs():
    q = queue.Queue()
    with _log_subscribers_lock:
        _log_subscribers.append(q)
    return q

def unsubscribe_logs(q):
    with _log_subscribers_lock:
        try:
            _log_subscribers.remove(q)
        except ValueError:
            pass

def _broadcast_log(log_row):
    with _log_subscribers_lock:
        for q in _log_subscribers:
            try:
                q.put_nowait(log_row)
            except queue.Full:
                pass


class TaskLogger:
    """Logger that writes to DB and broadcasts to SSE subscribers."""
    def __init__(self, run_id, task_name):
        self.run_id = run_id
        self.task_name = task_name

    def log(self, message):
        row = database.append_task_log(self.run_id, self.task_name, message)
        _broadcast_log(row)


# ── Task Registry ──

TASKS = {}  # name -> { "fn": callable, "description": str, "paused": bool }
_running = {}  # name -> threading.Thread


def register_task(name, fn, description=""):
    TASKS[name] = {"fn": fn, "description": description, "paused": False}


def get_task_list():
    result = []
    for name, info in TASKS.items():
        result.append({
            "name": name,
            "description": info["description"],
            "paused": info["paused"],
            "running": name in _running and _running[name].is_alive(),
        })
    return result


def start_task(name):
    if name not in TASKS:
        raise ValueError(f"Unknown task: {name}")
    if name in _running and _running[name].is_alive():
        raise ValueError(f"Task {name} is already running")
    if TASKS[name]["paused"]:
        raise ValueError(f"Task {name} is paused")

    task_info = TASKS[name]

    def _run():
        run = database.create_task_run(name)
        logger = TaskLogger(run["id"], name)
        logger.log(f"\033[1mStarting task: {name}\033[0m")
        try:
            task_info["fn"](logger)
            database.finish_task_run(run["id"], "completed")
            logger.log(f"\033[32mTask completed successfully\033[0m")
        except Exception as e:
            database.finish_task_run(run["id"], "failed")
            logger.log(f"\033[31mTask failed: {e}\033[0m")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    _running[name] = t


def set_task_paused(name, paused):
    if name not in TASKS:
        raise ValueError(f"Unknown task: {name}")
    TASKS[name]["paused"] = paused


# ── Shim Tasks ──

def _backup_task(logger):
    """Simulated backup task."""
    logger.log("Checking backup targets...")
    time.sleep(1)
    targets = ["database", "config", "media"]
    for i, target in enumerate(targets):
        logger.log(f"Backing up \033[36m{target}\033[0m... ({i+1}/{len(targets)})")
        time.sleep(1.5)
        logger.log(f"  \033[32m✓\033[0m {target} backed up (42 MB)")
    logger.log(f"\033[1;32mAll backups completed.\033[0m Total: {len(targets)} targets, 126 MB")


def _watchlist_update_task(logger):
    """Simulated watchlist update task."""
    import random
    settings = database.get_all_settings()
    watchlist_str = settings.get("watchlist", "AAPL,MSFT")
    tickers = [t.strip() for t in watchlist_str.split(",") if t.strip()]
    logger.log(f"Updating watchlist: \033[1m{len(tickers)} tickers\033[0m")
    time.sleep(0.5)
    for ticker in tickers:
        price = round(random.uniform(50, 500), 2)
        change = round(random.uniform(-5, 5), 2)
        color = "\033[32m" if change >= 0 else "\033[31m"
        logger.log(f"  {ticker}: ${price} ({color}{change:+.2f}%\033[0m)")
        time.sleep(0.3)
    logger.log(f"\033[1;32mWatchlist updated.\033[0m")


register_task("backup", _backup_task, "Back up database, config, and media files")
register_task("watchlist_update", _watchlist_update_task, "Fetch latest prices for watchlist tickers")
