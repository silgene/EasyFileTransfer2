# -*- coding: UTF-8 -*-
'''
@Project :fd_project 
@Author  :风吹落叶
@Contack :Waitkey1@outlook.com
@Version :V1.0
@Date    :2025/04/21 23:35
@Describe:
'''
# main.py (FastAPI后端)
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse,FileResponse
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
# 解决中文文件名编码
from urllib.parse import quote
import os
import sys


app = FastAPI(
    max_request_size=1024 * 1024 * 1024  # 1GB
)
# 创建上传目录
UPLOAD_DIR = "./static"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# s
# 允许所有来源（生产环境建议指定具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 挂载静态文件目录
app.mount(UPLOAD_DIR[1:], StaticFiles(directory="static"), name="static")

@app.get("/favicon.ico")
async def favicon():
    icon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(UPLOAD_DIR, "favicon.ico")
    if not os.path.exists(icon_path):
        raise HTTPException(status_code=404, detail="favicon not found")
    return FileResponse(icon_path, media_type="image/x-icon")

class FileInfo(BaseModel):
    name: str
    size: int
    modified_time: float

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    # 使用更大的缓冲区（8MB）提高磁盘写入吞吐
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer, length=8 * 1024 * 1024)
    return {"filename": file.filename}

@app.get("/files/", response_model=List[FileInfo])
async def list_files():
    files = []
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        stat = os.stat(file_path)
        files.append(FileInfo(
            name=filename,
            size=stat.st_size,
            modified_time=stat.st_mtime
        ))
    return files

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(file_path)
    return {"message": "File deleted successfully"}



def resource_path(relative_path: str) -> str:
    """在源码、PyInstaller --onefile 和 --onedir 三种环境下都能找到打包资源"""
    try:
        base_path = sys._MEIPASS  # onefile 模式的临时目录
    except Exception:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)  # onedir 模式下的可执行目录
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))  # 源码运行
    return os.path.join(base_path, relative_path)

@app.get("/", response_class=HTMLResponse)
async def main():

    # 使用打包安全的资源路径解析
    html_path = resource_path('index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()



    #print(html)
    return html

# main.py 后端新增下载端点
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    encoded_filename=quote(filename,safe='')
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"},
    )
from fastapi.responses import StreamingResponse

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    def iter_file():
        with open(file_path, mode="rb") as f:
            while chunk := f.read(1024 * 1024):  # 1MB chunks
                yield chunk

    encoded_filename = quote(filename, safe='')
    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}",
            "Content-Length": str(os.path.getsize(file_path))
        }
    )

if __name__ == '__main__':
    import uvicorn
    import platform
    import threading
    import webbrowser
    import time
    import socket

    def find_available_port(start: int = 3002, max_tries: int = 50) -> int:
        for port in range(start, start + max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('0.0.0.0', port))
                except OSError:
                    continue
                else:
                    return port
        return start

    selected_port = find_available_port(3002)

    def _open_browser(port: int):
        # 稍等后端启动，再打开浏览器
        time.sleep(1.2)
        # 获取本机IP地址（优先外网可用网卡，失败则回退）
        ip = "127.0.0.1"
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
        except Exception:
            try:
                import socket
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                pass
        url = f"http://{ip}:{port}/"
        # 控制台提示
        print(f"服务已启动，访问地址：{url}")
        print(f"提示：本机备用地址 http://127.0.0.1:{port}/")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"自动打开浏览器失败：{e}")
            print(f"请手动访问：{url}")
    # 仅在 Windows 系统自动打开浏览器；Linux/Unix 不打开
    if platform.system().lower().startswith('win'):
        threading.Thread(target=_open_browser, args=(selected_port,), daemon=True).start()

    uvicorn.run(app, host='0.0.0.0', port=selected_port)