# --coding:utf-8--
import os
import yaml
import asyncio
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from aomaker.storage import stats, cache
from aomaker.path import LOG_FILE_path
from aomaker.utils.gen_allure_report import gen_allure_summary

base_dir = os.path.dirname(__file__)
base_html_path = os.path.join(base_dir, "html")

app = FastAPI()

app.mount("/statics", StaticFiles(directory=base_html_path), name="statics")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Requested-With", "Content-Type"],
)


@app.get("/")
def read_root():
    return "hello,aomaker"


@app.get("/config/{param}")
def read_config(param: str):
    with open("conf/config.yaml", "r") as file:
        config_data = yaml.safe_load(file)
    if param == "current":
        current_env = config_data['env']
        current_config = {"current_env": current_env, **config_data[current_env]}
        return current_config
    return config_data


@app.get("/stats")
def get_stats(package: Optional[str] = Query(None, description="Package name to filter by."), ):
    conditions = {}

    if package:
        conditions['package'] = package

    results = stats.get(conditions=conditions)
    return results


@app.get("/stats/count")
def get_stats_count(stats_: list = Depends(get_stats)):
    return len(stats_)


@app.get("/summary")
def get_allure_summary():
    return gen_allure_summary()


@app.get("/progress")
def get_progress():
    progress_keys = cache.get_like("_progress.%")
    progress_data = {}

    for key in progress_keys:
        worker_name = key.split(".")[-1]
        progress_info = cache.get(key)

        progress_data[worker_name] = progress_info

    return progress_data


@app.websocket("/ws/logs")
async def get_logs(websocket: WebSocket):
    await websocket.accept()
    with open(LOG_FILE_path, "r") as log_file:
        try:
            log_file.seek(0, 2)  # Go to the end of file

            while True:
                new_line = log_file.readline()
                if new_line:
                    await websocket.send_text(new_line)
                else:
                    await asyncio.sleep(1)
        except WebSocketDisconnect:
            print("Logs WebSocket connection was closed.")
        finally:
            try:
                await websocket.close()
            except RuntimeError:
                print("Logs WebSocket connection was closed by the client.")


@app.websocket("/ws/progress")
async def get_progress(websocket: WebSocket):
    await websocket.accept()
    try:
        all_cases = 0
        all_completed = 0
        while True:

            progress_keys = cache.get_like("_progress.%")
            progress_data = {}
            for key in progress_keys:
                worker_name = key.split(".")[-1]
                progress_info = cache.get(key)  # {"target":"","completed":0,"total":0,"}
                print("progress_info:", progress_info)

                all_cases += progress_info["total"]
                all_completed += progress_info["completed"]
                progress_data[worker_name] = progress_info
            progress_data["Total"] = {"target": "", "completed": all_completed, "total": all_cases}
            await websocket.send_json(progress_data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Progress WebSocket connection was closed.")
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            print("Progress WebSocket connection was closed by the client.")
