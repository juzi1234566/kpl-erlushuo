$ErrorActionPreference = 'Continue'
Set-Location C:\Users\18413\Desktop\kpl-meme\pipeline
$py = ".\.venv\Scripts\python.exe"

& $py -m scripts.analyze_collection --bvid BV1TcNd6UEV6 --pages 1-5 --caster 可温 --up-name kpl二路 --mid 333332650 --match-id 2026071703 *>> data\bo5_kewen.log
& $py -m scripts.analyze_collection --bvid BV1TcNd6UEV6 --pages 6-10 --caster 时间 --up-name kpl二路 --mid 333332650 --match-id 2026071703 *>> data\bo5_shijian.log
Add-Content data\bo5_all.log "ALL_BO5_DONE_REAL"
