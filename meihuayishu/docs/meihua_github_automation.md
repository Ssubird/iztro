# 梅花易数 GitHub 托管与自动更新指南

## 1. 准备要托管的内容
- 仅保留 `meihuayishu/run_meihua.py`、`meihuayishu/meihuayishu/iching/meihua/` 相关子模块，以及它们依赖的配置文件（例如 `meihuayishu/meihuayishu/config/game_config.py`、`meihuayishu/meihuayishu/data/` 中真实数据下载所需的代码）。
- 在独立目录中整理项目结构，例如：
  - `meihuayishu/run_meihua.py`
  - `meihuayishu/meihuayishu/`
  - `scripts/`（后续新增自动化脚本）
  - `docs/`（说明文档）
  - `requirements.txt`
- 本地通过 `python run_meihua.py --game ssq` 验证脚本可以正常联网更新数据并生成结果，然后再继续下面的步骤。

### 建议的 `requirements.txt`
```text
pandas>=2.0
numpy>=1.24
requests>=2.32
```
如项目还依赖其他第三方库，请一并补充。

## 2. 初始化 Git 仓库并推送到 GitHub
1. 在 GitHub 上新建一个私有或公开仓库，例如 `meihua-daily`。
2. 在本地项目根目录执行：
```bash
git init
git add .
git commit -m "Initial meihua predictor"
git remote add origin git@github.com:<your-name>/meihua-daily.git
git push -u origin main
```
3. 后续若有本地调整，保持 `git add` → `git commit` → `git push` 的常规流程即可。

## 3. 新增每日更新与推送脚本
在 `scripts/` 目录下新增两个文件，分别负责刷新数据和向微信发送通知。

### `scripts/daily_update.py`

新增参数说明：命令行支持 `--recency-weight`、`--gap-weight`、`--calendar-weight`、`--history-half-life` 等，用于调节历史与黄历贡献。

> 提示：在联网下载受限（如需绕过代理/VPN）时，可在运行脚本前设置 `MEIHUA_DISABLE_PROXY=1` 或在命令中追加 `--no-proxy`。
> 进阶：命令支持 `--recency-weight`、`--gap-weight`、`--calendar-weight` 与 `--history-half-life`，可调节近期走势、黄历偏好与冷热号的影响。
```python
"""每天运行一次，刷新数据并生成简单的预测摘要"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)


def refresh_prediction() -> str:
    cmd = [
        "python",
        "run_meihua.py",
        "--game",
        "ssq",
    ]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    log_path = OUTPUT_DIR / "latest_prediction.txt"
    log_path.write_text(result.stdout, encoding="utf-8")
    return result.stdout


def build_message(body: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    headline = f"{today} 梅花易数预测结果"
    lines = [headline, "", body.strip().splitlines()[0] if body.strip() else "运行成功"]
    return "\n".join(lines)


def main() -> None:
    output = refresh_prediction()
    message = build_message(output)
    message_path = OUTPUT_DIR / "latest_message.txt"
    message_path.write_text(message, encoding="utf-8")
    print(message)


if __name__ == "__main__":
    main()
```

### `scripts/wechat_notify.py`
```python
"""通过企业微信机器人发送文本消息"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

WEBHOOK_KEY = "WECHAT_WEBHOOK"


def send_wechat_message(message: str) -> None:
    webhook = os.environ.get(WEBHOOK_KEY)
    if not webhook:
        raise RuntimeError(f"缺少环境变量 {WEBHOOK_KEY}")
    payload = {
        "msgtype": "text",
        "text": {
            "content": message,
        },
    }
    response = requests.post(webhook, json=payload, timeout=10)
    response.raise_for_status()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    message_path = repo_root / "reports" / "latest_message.txt"
    if not message_path.exists():
        raise FileNotFoundError("找不到最新的消息内容，请先运行 daily_update.py")
    send_wechat_message(message_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
```

## 4. 配置企业微信机器人
1. 在企业微信（WeCom）中创建或选择一个群组。
2. 点击群设置 → 添加机器人 → 选择“自定义机器人”，获取 webhook URL。
3. 将 webhook 保存在 GitHub 仓库的 Secrets 中（名称 `WECHAT_WEBHOOK`）。
4. 可以在本地通过 `python scripts/wechat_notify.py` 验证，前提是已设置 `WECHAT_WEBHOOK` 环境变量并先运行一次 `scripts/daily_update.py`。

## 5. 创建 GitHub Actions 工作流
在仓库中新建 `.github/workflows/daily-meihua.yml`：
```yaml
name: Daily Meihua Update

on:
  schedule:
    - cron: "30 10 * * *"  # UTC 时间 10:30，对应北京时间 18:30
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GH_PAT }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run daily update
        run: python scripts/daily_update.py

      - name: Commit refreshed data (if changed)
        run: |
          git config user.name "${{ secrets.GIT_USER_NAME }}"
          git config user.email "${{ secrets.GIT_USER_EMAIL }}"
          git status --short
          if [ -n "$(git status --porcelain)" ]; then
            git add data/meihua_cache reports
            git commit -m "chore: refresh data"
            git push
          else
            echo "No data changes"
          fi

      - name: Send WeChat notification
        env:
          WECHAT_WEBHOOK: ${{ secrets.WECHAT_WEBHOOK }}
        run: python scripts/wechat_notify.py
```

### 必需的仓库 Secrets
- `GH_PAT`：拥有 `repo` 和 `workflow` 权限的个人访问令牌，用于 Actions 推送提交。
- `GIT_USER_NAME` 与 `GIT_USER_EMAIL`：用于在 Actions 中配置提交信息。
- `WECHAT_WEBHOOK`：企业微信机器人 Webhook。

## 6. 运行与验证
1. 手动触发一次 `workflow_dispatch`，确认工作流能成功下载安装、刷新数据、提交变更，并收到微信通知。
2. 检查仓库中的 `data/meihua_cache/` 与 `reports/latest_prediction.txt` 是否按预期更新。
3. 若无新数据，工作流会输出 “No data changes”，并仍可通过微信收到运行结果。

## 7. 常见问题处理
- **数据下载失败**：检查 `RealDataLoader` 使用的网址是否可访问，或在 `run_meihua.py` 中添加 `--force-update` 以强制刷新。
- **微信通知未送达**：确认机器人仍在群内，Webhook 未过期，且 `WECHAT_WEBHOOK` 设置正确。
- **Actions 无法推送**：确保 `GH_PAT` 拥有足够权限，并且在工作流中使用了该令牌执行 `actions/checkout`。

完成以上步骤后，`run_meihua.py` 将在 GitHub 上每天自动运行一次，更新缓存数据，并将最新的预测摘要通过微信发送到指定群聊。

