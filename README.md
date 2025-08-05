# Maya Sawa V2 - Gen AI 自動回覆平台

## 開始

### 1. 環境設置

```bash
# 複製環境變量模板
cp .env.example .env

# 編輯 .env 文件，填入你的配置
# 詳細說明請參考 ENV_SETUP.md
```

### 2. 安裝依賴

```bash
poetry install
```

### 3. 數據庫遷移

```bash
poetry run python manage.py migrate
poetry run python manage.py setup_ai_models
```

### 4. 創建超級用戶

```bash
poetry run python manage.py createsuperuser
```

### 5. 啟動服務

```bash
# 開發環境
poetry run python manage.py runserver

# 生產環境
poetry run uvicorn config.asgi:application --host 0.0.0.0 --port 8000

# Celery Worker（新終端）
poetry run celery -A config worker -l info -Q maya_v2
```

## 開發命令

### 基本
```bash
# 檢查配置
poetry run python manage.py check

# 創建遷移
poetry run python manage.py makemigrations

# 執行遷移
poetry run python manage.py migrate

# 設置 AI 模型
poetry run python manage.py setup_ai_models
```

### 測試
```bash
# 運行測試
poetry run pytest

# 類型檢查
poetry run mypy maya_sawa_v2
```

### Celery 監控
```bash
# 查看 Worker 狀態
poetry run celery -A config inspect stats

# 查看活躍任務
poetry run celery -A config inspect active
```

## API 端點

- **管理介面**：`http://127.0.0.1:8000/admin/`
- **API 根目錄**：`http://127.0.0.1:8000/api/v1/`
- **對話 API**：`http://127.0.0.1:8000/api/v1/conversations/`


## 授權

MIT License
