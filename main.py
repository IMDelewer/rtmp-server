import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json

# Создание папки для HLS
HLS_PATH = "hls"
os.makedirs(HLS_PATH, exist_ok=True)

# Инициализация FastAPI
app = FastAPI()

# Файл с ключами потоков
STREAM_KEYS_FILE = "streams.json"
if not os.path.exists(STREAM_KEYS_FILE):
    with open(STREAM_KEYS_FILE, "w") as f:
        json.dump({}, f)

# Загружаем ключи потоков
def load_stream_keys():
    with open(STREAM_KEYS_FILE, "r") as f:
        return json.load(f)

# Сохраняем ключи потоков
def save_stream_keys(data):
    with open(STREAM_KEYS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Запущенные FFmpeg процессы
ffmpeg_processes = {}

class StreamKey(BaseModel):
    stream_key: str

@app.get("/")
def home():
    return {"message": "🔥 RTMP сервер на Python с FFmpeg работает! Стримьте через /rtmp и смотрите через /hls"}

@app.post("/rtmp/{stream_key}")
def start_stream(stream_key: str):
    stream_keys = load_stream_keys()

    if stream_key not in stream_keys:
        raise HTTPException(status_code=403, detail="❌ Неверный ключ потока!")

    rtmp_url = f"rtmp://127.0.0.1:1935/live/{stream_key}"
    hls_output = f"{HLS_PATH}/{stream_key}.m3u8"

    # Запускаем FFmpeg для HLS
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", rtmp_url,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-c:a", "aac",
        "-f", "hls",
        "-hls_time", "3",
        "-hls_list_size", "10",
        "-hls_flags", "delete_segments",
        hls_output
    ]

    process = subprocess.Popen(ffmpeg_cmd)
    ffmpeg_processes[stream_key] = process

    return {"message": f"✅ Стрим {stream_key} запущен!"}

@app.get("/hls/{stream_key}")
def watch_stream(stream_key: str):
    file_path = f"{HLS_PATH}/{stream_key}.m3u8"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="❌ Стрим не найден!")

@app.get("/status")
def stream_status():
    return {"active_streams": list(ffmpeg_processes.keys())}

@app.post("/add_stream")
def add_stream(data: StreamKey):
    stream_keys = load_stream_keys()
    stream_keys[data.stream_key] = True
    save_stream_keys(stream_keys)
    return {"message": f"✅ Ключ {data.stream_key} добавлен!"}

@app.post("/stop/{stream_key}")
def stop_stream(stream_key: str):
    if stream_key in ffmpeg_processes:
        ffmpeg_processes[stream_key].terminate()
        del ffmpeg_processes[stream_key]
        return {"message": f"🛑 Стрим {stream_key} остановлен"}
    raise HTTPException(status_code=404, detail="❌ Стрим не найден!")

# Запуск FastAPI сервера
if __name__ == "__main__":
    import uvicorn
    from threading import Thread

    # Запуск FastAPI
    uvicorn.run(app, host="0.0.0.0", port=5000)
