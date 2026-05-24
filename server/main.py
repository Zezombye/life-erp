import json
import random
import traceback
import queue
from wsgiref.simple_server import make_server

import falcon

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
    def on_get(self, req, resp):
        resp.text = json.dumps({"status": "ok"})



class HabitsResource:
    def on_get(self, req, resp):
        try:
            rows = database.get_all_habits()
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class HabitValueResource:
    def on_post(self, req, resp):
        try:
            body = json.loads(req.bounded_stream.read())
            date = body.get("date")
            column = body.get("column")
            value = body.get("value")

            if not date or not column:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "date and column are required"})
                return

            row = database.set_habit_value(date, column, value)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class SettingsResource:
    def on_get(self, req, resp):
        try:
            settings = database.get_all_settings()
            resp.text = json.dumps(settings)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_post(self, req, resp):
        try:
            body = json.loads(req.bounded_stream.read())
            key = body.get("key")
            value = body.get("value")

            if not key:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "key is required"})
                return

            database.set_setting(key, str(value))
            settings = database.get_all_settings()
            resp.text = json.dumps(settings)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class WorkoutsResource:
    def on_get(self, req, resp):
        try:
            rows = database.get_all_workouts()
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class WorkoutValueResource:
    def on_post(self, req, resp):
        try:
            body = json.loads(req.bounded_stream.read())
            date = body.get("date")
            column = body.get("column")
            value = body.get("value")

            if not date or not column:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "date and column are required"})
                return

            row = database.set_workout_value(date, column, value)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class ChoresResource:
    def on_get(self, req, resp):
        try:
            rows = database.get_all_chores()
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_post(self, req, resp):
        try:
            body = json.loads(req.bounded_stream.read())
            title = body.get("title")
            interval_days = body.get("interval_days")

            if not title or interval_days is None:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and interval_days are required"})
                return

            row = database.create_chore(title, int(interval_days))
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class ChoreResource:
    def on_put(self, req, resp, chore_id):
        try:
            body = json.loads(req.bounded_stream.read())
            title = body.get("title")
            interval_days = body.get("interval_days")

            if not title or interval_days is None:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and interval_days are required"})
                return

            row = database.update_chore(int(chore_id), title, int(interval_days))
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_delete(self, req, resp, chore_id):
        try:
            database.delete_chore(int(chore_id))
            resp.text = json.dumps({"ok": True})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class ChoreDoneResource:
    def on_post(self, req, resp, chore_id):
        try:
            body = req.bounded_stream.read()
            done_date = None
            if body:
                data = json.loads(body)
                done_date = data.get("date")

            row = database.mark_chore_done(int(chore_id), done_date)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodosResource:
    def on_get(self, req, resp):
        try:
            rows = database.get_all_todos()
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_post(self, req, resp):
        try:
            body = json.loads(req.bounded_stream.read())
            title = body.get("title")
            if not title:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title is required"})
                return
            row = database.create_todo(title)
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoResource:
    def on_put(self, req, resp, todo_id):
        try:
            body = json.loads(req.bounded_stream.read())
            title = body.get("title")
            if not title:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title is required"})
                return
            row = database.update_todo(int(todo_id), title)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoStatusResource:
    def on_post(self, req, resp, todo_id):
        try:
            body = json.loads(req.bounded_stream.read())
            status = body.get("status")
            if status not in ("open", "closed"):
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "status must be 'open' or 'closed'"})
                return
            row = database.set_todo_status(int(todo_id), status)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoMessagesResource:
    def on_get(self, req, resp, todo_id):
        try:
            rows = database.get_todo_messages(int(todo_id))
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_post(self, req, resp, todo_id):
        try:
            body = json.loads(req.bounded_stream.read())
            content = body.get("content")
            if not content:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "content is required"})
                return
            row = database.create_todo_message(int(todo_id), content)
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TodoMessageResource:
    def on_put(self, req, resp, todo_id, message_id):
        try:
            body = json.loads(req.bounded_stream.read())
            content = body.get("content")
            if not content:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "content is required"})
                return
            row = database.update_todo_message(int(message_id), content)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_delete(self, req, resp, todo_id, message_id):
        try:
            database.delete_todo_message(int(message_id))
            resp.text = json.dumps({"ok": True})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class StocksResource:
    def on_get(self, req, resp):
        try:
            settings = database.get_all_settings()
            watchlist_str = settings.get("watchlist", "")
            tickers = [t.strip() for t in watchlist_str.split(",") if t.strip()]
            result = [generate_mock_candles(t) for t in tickers]
            resp.text = json.dumps(result)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class CalendarEventsResource:
    def on_get(self, req, resp):
        try:
            start = req.get_param("start")
            end = req.get_param("end")
            if not start or not end:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "start and end query params are required"})
                return
            database.ensure_economic_events(start, end)
            rows = database.get_calendar_events(start, end)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_post(self, req, resp):
        try:
            body = json.loads(req.bounded_stream.read())
            title = body.get("title")
            evt_date = body.get("date")
            evt_time = body.get("time")
            category = body.get("category", "personal")
            if not title or not evt_date:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and date are required"})
                return
            row = database.create_calendar_event(title, evt_date, evt_time, category)
            resp.text = json.dumps(row)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class CalendarEventResource:
    def on_put(self, req, resp, event_id):
        try:
            body = json.loads(req.bounded_stream.read())
            title = body.get("title")
            evt_date = body.get("date")
            evt_time = body.get("time")
            category = body.get("category", "personal")
            if not title or not evt_date:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"error": "title and date are required"})
                return
            row = database.update_calendar_event(int(event_id), title, evt_date, evt_time, category)
            resp.text = json.dumps(row)
        except ValueError as e:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"error": str(e)})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()

    def on_delete(self, req, resp, event_id):
        try:
            database.delete_calendar_event(int(event_id))
            resp.text = json.dumps({"ok": True})
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TasksResource:
    def on_get(self, req, resp):
        try:
            task_list = tasks.get_task_list()
            resp.text = json.dumps(task_list)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TaskStartResource:
    def on_post(self, req, resp, task_name):
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
    def on_post(self, req, resp, task_name):
        try:
            body = json.loads(req.bounded_stream.read())
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
    def on_get(self, req, resp):
        try:
            limit = int(req.get_param("limit") or 50)
            rows = database.get_task_runs(limit)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TaskLogsResource:
    def on_get(self, req, resp):
        try:
            task_name = req.get_param("task")
            limit = int(req.get_param("limit") or 500)
            since_id = req.get_param("since_id")
            if since_id is not None:
                since_id = int(since_id)
            rows = database.get_task_logs(task_name, limit, since_id)
            resp.text = json.dumps(rows)
        except Exception:
            resp.status = falcon.HTTP_500
            resp.text = traceback.format_exc()


class TaskLogStreamResource:
    """SSE endpoint for real-time log streaming."""
    def on_get(self, req, resp):
        resp.content_type = "text/event-stream"
        resp.cache_control = ["no-cache"]
        resp.set_header("Connection", "keep-alive")
        resp.set_header("X-Accel-Buffering", "no")
        resp.set_header("Access-Control-Allow-Origin", "*")

        q = tasks.subscribe_logs()

        def _stream():
            try:
                while True:
                    try:
                        log_row = q.get(timeout=15)
                        data = json.dumps(log_row)
                        yield f"data: {data}\n\n".encode("utf-8")
                    except queue.Empty:
                        # Send keepalive
                        yield ": keepalive\n\n".encode("utf-8")
            except GeneratorExit:
                pass
            finally:
                tasks.unsubscribe_logs(q)

        resp.stream = _stream()


app = falcon.App(cors_enable=True)
app.add_route("/api/health", HealthResource())
app.add_route("/api/habits", HabitsResource())
app.add_route("/api/habits/value", HabitValueResource())
app.add_route("/api/settings", SettingsResource())
app.add_route("/api/workouts", WorkoutsResource())
app.add_route("/api/workouts/value", WorkoutValueResource())
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
app.add_route("/api/task-logs/stream", TaskLogStreamResource())

if __name__ == "__main__":
    print("Starting server on http://localhost:8000")
    with make_server("", 8000, app) as httpd:
        httpd.serve_forever()
