#!/usr/bin/env bash
# 云服务器一键部署（Ubuntu 22.04/24.04，2核4G 起）
# 用法：把仓库代码放到 /opt/kpl-meme 后执行本脚本；或先跑本脚本再 git clone
set -e

echo "== 1. 系统依赖 =="
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ffmpeg git

APP=/opt/kpl-meme
cd $APP/pipeline

echo "== 2. Python 环境 =="
python3 -m venv .venv
./.venv/bin/pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
./.venv/bin/pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
./.venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "== 3. 环境变量 =="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "!! 请编辑 $APP/pipeline/.env 填入 DEEPSEEK_API_KEY / SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / BILI_SESSDATA"
  echo "!! 国内服务器直连 DeepSeek/Supabase/B站，OUTBOUND_PROXY 留空"
fi

echo "== 4. systemd 常驻服务 =="
cat > /etc/systemd/system/kpl-watcher.service <<'EOF'
[Unit]
Description=KPL二路说 监听器（UP发布即处理）
After=network-online.target

[Service]
WorkingDirectory=/opt/kpl-meme/pipeline
ExecStart=/opt/kpl-meme/pipeline/.venv/bin/python -m scripts.watcher
Restart=always
RestartSec=60
StandardOutput=append:/opt/kpl-meme/pipeline/data/watcher.log
StandardError=append:/opt/kpl-meme/pipeline/data/watcher.log

[Install]
WantedBy=multi-user.target
EOF

mkdir -p $APP/pipeline/data
systemctl daemon-reload
systemctl enable kpl-watcher

echo "== 完成 =="
echo "填好 .env 后：systemctl start kpl-watcher && tail -f $APP/pipeline/data/watcher.log"
