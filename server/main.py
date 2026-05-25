import json
import random
import traceback
import asyncio
from asyncio import to_thread

import falcon
import falcon.asgi

import database
import tasks


# Base prices for mock data (seeded by ticker name for consistency)
MOCK_BASE_PRICES = {
    "AAPL": 195.0, "MSFT": 420.0, "GOOGL": 175.0, "AMZN": 185.0,
    "TSLA": 250.0, "META": 500.0, "NVDA": 130.0, "NFLX": 620.0,
    "BTC": 68000.0, "ETH": 3800.0, "SPY": 530.0, "QQQ": 460.0,
}


def generate_mock_candles(ticker, num_candles=24):
    """Generate mock hourly OHLCV candles for a ticker."""
    base = MOCK_BASE_PRICES.get(ticker.upper(), 100.0 + sum(ord(c) for c in ticker) % 400)
    rng = random.Random(ticker + "seed")
    volatility = base * 0.005  # 0.5% per candle

    candles = []
    price = base * (1 + rng.uniform(-0.02, 0.02))

    for i in range(num_candles):
        open_p = price
        high_p = open_p + rng.uniform(0, volatility * 2)
        low_p = open_p - rng.uniform(0, volatility * 2)
        close_p = open_p + rng.uniform(-volatility, volatility)
        # Ensure high >= open,close and low <= open,close
        high_p = max(high_p, open_p, close_p)
        low_p = min(low_p, open_p, close_p)
        volume = rng.randint(100000, 5000000)

        candles.append({
            "hour": i,
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": volume,
        })
        price = close_p

    current_price = candles[-1]["close"]
    day_open = candles[0]["open"]
    change = current_price - day_open
    change_pct = (change / day_open) * 100 if day_open else 0

    return {
        "ticker": ticker.upper(),
        "price": round(current_price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "candles": candles,
    }


class HealthResource:
    async def on_get(self, req, resp):
        resp.text = json.dumps({"status": "ok"})


class SchemaResource:
    async def on_get(self, req, resp):
        schema = await to_thread(database.get_synced_schema)
        resp.text = json.dumps(schema)


# ── WebSocket Client Registry ──

_ws_clients = {}  # client_id -> asyncio.Queue
_ws_clients_lock = asyncio.Lock()


async def ws_broadcast(change, exclude_client=None):
    """Broadcast a change to all connected WebSocket clients except the originator."""
    msg = json.dumps({"type": "change", "change": change})
    async with _ws_clients_lock:
        for cid, q in list(_ws_clients.items()):
            if cid != exclude_client:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass


async def ws_broadcast_log(log_row):
    """Broadcast a task log to all connected WebSocket clients."""
    msg = json.dumps({"type": "log", "log": log_row})
    async with _ws_clients_lock:
        for cid, q in list(_ws_clients.items()):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass


async def ws_broadcast_stock(data):
    """Broadcast stock data to all connected WebSocket clients."""
    msg = json.dumps({"type": "stock", "data": data})
    async with _ws_clients_lock:
        for cid, q in list(_ws_clients.items()):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass


def _sync_ws_broadcast(change, exclude_client=None):
    """Thread-safe bridge: schedule ws_broadcast on the event loop.
    Called from database.py (which runs in threads via to_thread)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(ws_broadcast(change, exclude_client))
    except RuntimeError:
        pass


# Register the broadcast function with database module
database.set_ws_broadcast(_sync_ws_broadcast)

# Register log broadcast with tasks module
def _sync_ws_broadcast_log(log_row):
    """Thread-safe bridge for task log broadcasting."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(ws_broadcast_log(log_row))
    except RuntimeError:
        pass

tasks.set_ws_broadcast_log(_sync_ws_broadcast_log)


# ── Helper to read request body ──

async def read_json_body(req):
    data = await req.bounded_stream.read()
    return json.loads(data) if data else {}



class HabitsResource:
    async def on_get(self, req, resp):
        try:
            rows = await to_thread(database.get_all_habits)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class HabitValueResource:
    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            date = body.get("date")
            column = body.get("column")
            value = body.get("value")

            if not date or not column:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "date and column are required"})
                return

            row = await to_thread(database.set_habit_value, date, column, value)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class WorkoutPresetsResource:
    async def on_get(self, req, resp):
        try:
            presets = await to_thread(database.get_workout_presets)
            resp.text = json.dumps(presets)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            name = body.get("name", "Untitled")
            content = body.get("content", "")
            preset = await to_thread(database.create_workout_preset, name, content)
            resp.text = json.dumps(preset)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class WorkoutPresetResource:
    async def on_put(self, req, resp, preset_id):
        try:
            body = await read_json_body(req)
            name = body.get("name")
            content = body.get("content")
            preset = await to_thread(database.update_workout_preset, int(preset_id), name, content)
            resp.text = json.dumps(preset)
        except ValueError as e:
            resp.status = falcon.HTTP_404
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_delete(self, req, resp, preset_id):
        try:
            await to_thread(database.delete_workout_preset, int(preset_id))
            resp.text = json.dumps({"ok": True})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class HabitTimerResource:
    async def on_get(self, req, resp):
        try:
            timers = await to_thread(database.get_habit_timers)
            resp.text = json.dumps(timers)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            action = body.get("action")
            timestamp = body.get("timestamp")

            if not action or not timestamp:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "action and timestamp are required"})
                return

            if action == "start":
                activity = body.get("activity")
                if not activity:
                    resp.status = falcon.HTTP_400
                    resp.text = json.dumps({"error": "activity is required for start"})
                    return
                result = await to_thread(database.start_habit_timer, activity, timestamp)
                resp.text = json.dumps(result)
            elif action in ("pause", "resume", "stop"):
                timer_id = body.get("timer_id")
                if not timer_id:
                    resp.status = falcon.HTTP_400
                    resp.text = json.dumps({"error": "timer_id is required"})
                    return
                if action == "pause":
                    result = await to_thread(database.pause_habit_timer, timer_id, timestamp)
                elif action == "resume":
                    result = await to_thread(database.resume_habit_timer, timer_id, timestamp)
                else:
                    result = await to_thread(database.stop_habit_timer, timer_id, timestamp)
                resp.text = json.dumps(result)
            else:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": f"Unknown action: {action}"})
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class SettingsResource:
    async def on_get(self, req, resp):
        try:
            settings = await to_thread(database.get_all_settings)
            resp.text = json.dumps(settings)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            key = body.get("key")
            value = body.get("value")

            if not key:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "key is required"})
                return

            await to_thread(database.set_setting, key, str(value))
            settings = await to_thread(database.get_all_settings)
            resp.text = json.dumps(settings)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class WorkoutsResource:
    async def on_get(self, req, resp):
        try:
            rows = await to_thread(database.get_all_workouts)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class WorkoutValueResource:
    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            date = body.get("date")
            column = body.get("column")
            value = body.get("value")

            if not date or not column:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "date and column are required"})
                return

            row = await to_thread(database.set_workout_value, date, column, value)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class ChoresResource:
    async def on_get(self, req, resp):
        try:
            rows = await to_thread(database.get_all_chores)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            title = body.get("title")
            interval_days = body.get("interval_days")

            if not title or interval_days is None:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and interval_days are required"})
                return

            row = await to_thread(database.create_chore, title, int(interval_days))
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class ChoreResource:
    async def on_put(self, req, resp, chore_id):
        try:
            body = await read_json_body(req)
            title = body.get("title")
            interval_days = body.get("interval_days")

            if not title or interval_days is None:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and interval_days are required"})
                return

            row = await to_thread(database.update_chore, int(chore_id), title, int(interval_days))
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_delete(self, req, resp, chore_id):
        try:
            await to_thread(database.delete_chore, int(chore_id))
            resp.text = json.dumps({"ok": True})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class ChoreDoneResource:
    async def on_post(self, req, resp, chore_id):
        try:
            body_bytes = await req.bounded_stream.read()
            done_date = None
            if body_bytes:
                data = json.loads(body_bytes)
                done_date = data.get("date")

            row = await to_thread(database.mark_chore_done, int(chore_id), done_date)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodosResource:
    async def on_get(self, req, resp):
        try:
            rows = await to_thread(database.get_all_todos)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            title = body.get("title")
            if not title:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title is required"})
                return
            row = await to_thread(database.create_todo, title)
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoResource:
    async def on_put(self, req, resp, todo_id):
        try:
            body = await read_json_body(req)
            title = body.get("title")
            if not title:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title is required"})
                return
            row = await to_thread(database.update_todo, int(todo_id), title)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoStatusResource:
    async def on_post(self, req, resp, todo_id):
        try:
            body = await read_json_body(req)
            status = body.get("status")
            if status not in ("open", "closed"):
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "status must be 'open' or 'closed'"})
                return
            row = await to_thread(database.set_todo_status, int(todo_id), status)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoMessagesResource:
    async def on_get(self, req, resp, todo_id):
        try:
            rows = await to_thread(database.get_todo_messages, int(todo_id))
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_post(self, req, resp, todo_id):
        try:
            body = await read_json_body(req)
            content = body.get("content")
            if not content:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "content is required"})
                return
            row = await to_thread(database.create_todo_message, int(todo_id), content)
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoMessageResource:
    async def on_put(self, req, resp, todo_id, message_id):
        try:
            body = await read_json_body(req)
            content = body.get("content")
            if not content:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "content is required"})
                return
            row = await to_thread(database.update_todo_message, int(message_id), content)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_delete(self, req, resp, todo_id, message_id):
        try:
            await to_thread(database.delete_todo_message, int(message_id))
            resp.text = json.dumps({"ok": True})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class StocksResource:
    async def on_get(self, req, resp):
        try:
            settings = await to_thread(database.get_all_settings)
            watchlist_str = settings.get("watchlist", "")
            tickers = [t.strip() for t in watchlist_str.split(",") if t.strip()]
            result = [generate_mock_candles(t) for t in tickers]
            resp.text = json.dumps(result)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class CalendarEventsResource:
    async def on_get(self, req, resp):
        try:
            start = req.get_param("start")
            end = req.get_param("end")
            if not start or not end:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "start and end query params are required"})
                return
            await to_thread(database.ensure_economic_events, start, end)
            rows = await to_thread(database.get_calendar_events, start, end)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_post(self, req, resp):
        try:
            body = await read_json_body(req)
            title = body.get("title")
            evt_date = body.get("date")
            evt_time = body.get("time")
            category = body.get("category", "personal")
            if not title or not evt_date:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and date are required"})
                return
            row = await to_thread(database.create_calendar_event, title, evt_date, evt_time, category)
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class CalendarEventResource:
    async def on_put(self, req, resp, event_id):
        try:
            body = await read_json_body(req)
            title = body.get("title")
            evt_date = body.get("date")
            evt_time = body.get("time")
            category = body.get("category", "personal")
            if not title or not evt_date:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and date are required"})
                return
            row = await to_thread(database.update_calendar_event, int(event_id), title, evt_date, evt_time, category)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    async def on_delete(self, req, resp, event_id):
        try:
            await to_thread(database.delete_calendar_event, int(event_id))
            resp.text = json.dumps({"ok": True})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TasksResource:
    async def on_get(self, req, resp):
        try:
            task_list = tasks.get_task_list()
            resp.text = json.dumps(task_list)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TaskStartResource:
    async def on_post(self, req, resp, task_name):
        try:
            tasks.start_task(task_name)
            resp.text = json.dumps({"ok": True})
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TaskPauseResource:
    async def on_post(self, req, resp, task_name):
        try:
            body = await read_json_body(req)
            paused = body.get("paused", True)
            tasks.set_task_paused(task_name, paused)
            resp.text = json.dumps({"ok": True, "paused": paused})
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TaskRunsResource:
    async def on_get(self, req, resp):
        try:
            limit = int(req.get_param("limit") or 50)
            rows = await to_thread(database.get_task_runs, limit)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TaskLogsResource:
    async def on_get(self, req, resp):
        try:
            task_name = req.get_param("task")
            limit = int(req.get_param("limit") or 500)
            since_id = req.get_param("since_id")
            if since_id is not None:
                since_id = int(since_id)
            rows = await to_thread(database.get_task_logs, task_name, limit, since_id)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


# ── WebSocket Resource ──

class WebSocketResource:
    async def on_websocket(self, req, ws):
        try:
            await ws.accept()
        except falcon.WebSocketDisconnected:
            return

        client_id = req.get_param("client_id") or f"ws-{id(ws)}"
        outbound_queue = asyncio.Queue(maxsize=1000)

        async with _ws_clients_lock:
            old_queue = _ws_clients.get(client_id)
            if old_queue is not None:
                # Signal old connection to close by sending a sentinel
                try:
                    old_queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            _ws_clients[client_id] = outbound_queue

        try:
            schema = await to_thread(database.get_synced_schema)
            await ws.send_text(json.dumps({"type": "schema", "schema": schema}))

            await asyncio.gather(
                self._handle_inbound(ws, client_id),
                self._handle_outbound(ws, outbound_queue),
            )
        except falcon.WebSocketDisconnected:
            pass
        except Exception:
            traceback.print_exc()
        finally:
            async with _ws_clients_lock:
                _ws_clients.pop(client_id, None)

    async def _handle_inbound(self, ws, client_id):
        while True:
            try:
                text = await ws.receive_text()
            except falcon.WebSocketDisconnected:
                return

            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "sync":
                last_seq = msg.get("last_seq", 0)
                pending = msg.get("pending_changes", [])

                if pending:
                    await to_thread(database.apply_client_changes, pending, client_id)

                if last_seq == 0:
                    # Initial sync: send full table snapshot
                    changes = await to_thread(database.get_full_sync_snapshot)
                else:
                    changes = await to_thread(database.get_changes_since, last_seq)
                new_last_seq = await to_thread(database.get_last_seq)

                await ws.send_text(json.dumps({
                    "type": "sync_response",
                    "changes": changes,
                    "last_seq": new_last_seq,
                }))

            elif msg_type == "changes":
                changes = msg.get("changes", [])
                if changes:
                    await to_thread(database.apply_client_changes, changes, client_id)
                    new_last_seq = await to_thread(database.get_last_seq)
                    await ws.send_text(json.dumps({
                        "type": "ack",
                        "last_seq": new_last_seq,
                    }))

            elif msg_type == "task_start":
                task_name = msg.get("task_name")
                if task_name:
                    try:
                        tasks.start_task(task_name)
                    except ValueError:
                        pass

            elif msg_type == "task_pause":
                task_name = msg.get("task_name")
                paused = msg.get("paused", True)
                if task_name:
                    try:
                        tasks.set_task_paused(task_name, paused)
                    except ValueError:
                        pass

    async def _handle_outbound(self, ws, queue):
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                if msg is None:
                    # Sentinel: another connection took over this client_id
                    await ws.close()
                    return
                await ws.send_text(msg)
            except asyncio.TimeoutError:
                try:
                    await ws.send_text(json.dumps({"type": "ping"}))
                except falcon.WebSocketDisconnected:
                    return
            except falcon.WebSocketDisconnected:
                return


# ── Build App ──

app = falcon.asgi.App(cors_enable=True)

app.add_route("/api/schema", SchemaResource())
app.add_route("/api/health", HealthResource())
app.add_route("/api/habits", HabitsResource())
app.add_route("/api/habits/value", HabitValueResource())
app.add_route("/api/habits/timer", HabitTimerResource())
app.add_route("/api/settings", SettingsResource())
app.add_route("/api/workouts", WorkoutsResource())
app.add_route("/api/workouts/value", WorkoutValueResource())
app.add_route("/api/workout-presets", WorkoutPresetsResource())
app.add_route("/api/workout-presets/{preset_id}", WorkoutPresetResource())
app.add_route("/api/chores", ChoresResource())
app.add_route("/api/chores/{chore_id}", ChoreResource())
app.add_route("/api/chores/{chore_id}/done", ChoreDoneResource())
app.add_route("/api/todos", TodosResource())
app.add_route("/api/todos/{todo_id}", TodoResource())
app.add_route("/api/todos/{todo_id}/status", TodoStatusResource())
app.add_route("/api/todos/{todo_id}/messages", TodoMessagesResource())
app.add_route("/api/todos/{todo_id}/messages/{message_id}", TodoMessageResource())
app.add_route("/api/stocks", StocksResource())
app.add_route("/api/calendar", CalendarEventsResource())
app.add_route("/api/calendar/{event_id}", CalendarEventResource())
app.add_route("/api/tasks", TasksResource())
app.add_route("/api/tasks/{task_name}/start", TaskStartResource())
app.add_route("/api/tasks/{task_name}/pause", TaskPauseResource())
app.add_route("/api/task-runs", TaskRunsResource())
app.add_route("/api/task-logs", TaskLogsResource())
app.add_route("/ws", WebSocketResource())

if __name__ == "__main__":
    import uvicorn
    print("Starting ASGI server on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
