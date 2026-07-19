@echo off
chcp 65001 >nul
cd /d C:\Users\18413\Desktop\kpl-meme\pipeline
.venv\Scripts\python.exe -m scripts.night_batch >> data\night_task_out.log 2>&1
