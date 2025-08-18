# Maya Sawa V2 - Gen AI 自動回覆平台

## 系統架構圖

```mermaid
graph TB
    subgraph "前端層"
        A[用戶介面] --> B[API 客戶端]
    end

    subgraph "API 層"
        B --> A1[ask-with-model]
        B --> A2[chat-history]
        B --> A3[available-models]
    end

    subgraph "服務層"
        S1[FilterChainManager] --> S2[KMSourceManager]
        S3[ChatHistoryService] --> R[(Redis)]
        S4[AIResponseService] --> P1[AI Providers]
        P1 --> P1a[OpenAI]
        P1 --> P1b[Gemini]
        P1 --> P1c[Qwen]
        P1 --> P1d[Mock]
    end

    subgraph "資料層"
        D1[(PostgreSQL)]
        D2[(Redis)]
        D3[(Celery Broker)]
    end

    subgraph "外部系統"
        E1[Paprika API]
        E2[OpenAI API]
        E3[Google Gemini API]
        E4[Qwen API]
    end

    %% 關聯
    A1 --> S1
    S1 --> S2
    S2 --> D1
    A1 --> S3
    S3 --> D2
    A1 --> S4
    S4 --> P1
    P1a --> E2
    P1b --> E3
    P1c --> E4
    S2 --> E1

    %% DB 關聯
    A1 --> D1
    A2 --> D2

    %% 註解
    D1:::db
    D2:::cache
    D3:::broker

    classDef db fill:#f1f8e9
    classDef cache fill:#e3f2fd
    classDef broker fill:#fff3e0
```

## 對話流程圖

```mermaid
sequenceDiagram
    participant U as 用戶
    participant F as 前端
    participant A as API
    participant R as Redis
    participant DB as PostgreSQL
    participant KM as 知識檢索
    participant AI as AI Provider

    U->>F: 發送問題
    F->>A: POST /maya-v2/ask-with-model/
    A->>DB: 建立 Conversation, Message
    A->>R: 追加使用者訊息(chat:session)
    A->>KM: Hybrid Search(trigram + pgvector)
    KM->>DB: 檢索 articles.content/embedding
    DB-->>A: Top-K 相關內容
    A->>AI: 調用指定模型(OpenAI/Gemini/Qwen/Mock)
    AI-->>A: 回傳 AI 回應
    A->>R: 追加 AI 訊息(chat:session)
    A->>DB: 建立 AI Message
    A-->>F: 回傳 AI 回應 + 引用

    Note over F,R: 可用 GET /maya-v2/chat-history/{session_id}
```

## 全文檢索混和 Embedding 架構圖

```mermaid
graph TD
  %% 使用者與入口
  U["User"] --> Q["ask-with-model API<br/>question"]
  Q --> P["Full-text Retrieval Pipeline"]

  %% 檢索流程
  subgraph "Pipeline"
    P --> N["Normalize/Lowercase<br/>trim punctuation"]
    N --> E{"Compute Embedding?"}
    E -- Yes --> EM["OpenAI Embeddings<br/>(text-embedding-3-small) → qvec(1536)"]
    E -- No --> SKIP["Skip vector branch"]

    %% Postgres 檢索（Trigram 與 Vector）
    subgraph "PostgreSQL"
      direction LR
      PG1["Trigram Search<br/>content % :query<br/>similarity(content, :query) as text_sim"]:::trgm
      PG2["Vector Search<br/>1 - (embedding <=> :qvec) as vec_sim"]:::vec
      IDX1["GIN Index<br/>idx_articles_content_trgm<br/>(content gin_trgm_ops)"]:::idx
      IDX2["IVFFlat Index<br/>idx_articles_embedding_ivfcos<br/>(embedding vector_cosine_ops)"]:::idx
      EXT1["EXTENSION pg_trgm<br/>set_limit(:min_sim)"]:::ext
      EXT2["EXTENSION pgvector"]:::ext
    end

    EM --> PG2
    SKIP -.-> PG1
    N --> PG1
    PG1 --> MRG["Merge & Rank<br/>score = 0.6*text_sim + 0.4*vec_sim"]
    PG2 --> MRG
    MRG --> TOPK["Top-K Articles"]
  end

  %% 後處理與回傳
  TOPK --> CTX["Build Context from Articles<br/>(title + snippet)"]
  CTX --> AI["LLM Call (OpenAI/Gemini/Qwen/Mock)"]
  AI --> RESP["Answer + Citations"]
  RESP --> RDS["Redis ChatHistory<br/>chat:session:{sid}"]
  RESP --> OUT["API Response"]

  %% 資料表與索引
  subgraph "articles schema"
    TBL["articles<br/>- id BIGSERIAL PK<br/>- file_path VARCHAR(500) UNIQUE<br/>- content TEXT NOT NULL<br/>- file_date TIMESTAMP NOT NULL<br/>- embedding vector(1536)"]:::tbl
  end
  TBL -. indexed by .-> IDX1
  TBL -. indexed by .-> IDX2

  %% 樣式
  classDef trgm fill:#e3f2fd,stroke:#1e88e5,stroke-width:1px
  classDef vec fill:#fce4ec,stroke:#d81b60,stroke-width:1px
  classDef idx fill:#fff3e0,stroke:#fb8c00,stroke-width:1px
  classDef ext fill:#ede7f6,stroke:#5e35b1,stroke-width:1px
  classDef tbl fill:#f1f8e9,stroke:#43a047,stroke-width:1px
```

## 技術棧

### 後端技術
- **Django 5.1.11** - Web 框架
- **Django REST Framework 3.15.2** - API 框架
- **Celery 5.4.0** - 異步任務處理
- **PostgreSQL** - 主資料庫 (支援 pgvector 擴展)
- **Redis 6.2.0** - 快取和 Celery Broker
- **Poetry** - 依賴管理

### AI 提供者
- **OpenAI** - GPT-4o-mini, GPT-4o, GPT-4.1-nano, GPT-3.5-turbo
- **Google Gemini** - gemini-1.5-flash, gemini-1.5-pro
- **Qwen** - qwen-turbo, qwen-plus
- **Mock Provider** - 測試用模擬提供者

### 核心依賴
- **django-cors-headers 4.6.0** - CORS 支援
- **drf-spectacular 0.28.0** - API 文檔生成
- **django-allauth 65.10.0** - 用戶認證
- **psycopg 3.2.9** - PostgreSQL 驅動
- **openai 1.12.0** - OpenAI API 客戶端
- **google-generativeai 0.8.3** - Google Gemini API
- **dashscope 1.14.0** - Qwen API 客戶端

## 快速開始

### 環境要求
- Python 3.12+
- PostgreSQL 13+ (支援 pgvector)
- Redis 6.0+
- Poetry

### 本地開發設置

```bash
# 1. 克隆專案
git clone <repository-url>
cd maya-sawa-v2

# 2. 安裝 Poetry (如果尚未安裝)
curl -sSL https://install.python-poetry.org | python3 -

# 3. 安裝依賴
poetry install

# 4. 複製環境變量模板
cp .env.example .env

# 5. 編輯 .env 文件，填入你的配置
# 必要配置：
# - DATABASE_URL 或 DB_* 變數
# - REDIS_URL
# - OPENAI_API_KEY (如果使用 OpenAI)
# - GOOGLE_API_KEY (如果使用 Gemini)
# - QWEN_API_KEY (如果使用 Qwen)

# 6. 數據庫遷移
poetry run python manage.py migrate

# 7. 設置 AI 模型
poetry run python manage.py setup_ai_models

# 8. 創建超級用戶
poetry run python manage.py createsuperuser

# 9. 啟動服務
poetry run python manage.py runserver

# 10. Celery Worker（新終端）
poetry run celery -A config worker -l info -Q maya_v2
```

### 環境變數配置

#### 資料庫配置
```bash
# 方式 1: 使用 DATABASE_URL
DATABASE_URL=postgres://user:password@localhost:5432/maya_sawa_v2

# 方式 2: 使用分離變數
DB_CONNECTION=pgsql
DB_HOST=localhost
DB_PORT=5432
DB_DATABASE=maya_sawa_v2
DB_USERNAME=user
DB_PASSWORD=password
DB_SSLMODE=require
```

#### AI 提供者配置
```bash
# 啟用的提供者
ENABLED_PROVIDERS=openai,gemini,qwen,mock

# OpenAI 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_ORGANIZATION=your_org_id
OPENAI_MODELS=gpt-4o-mini,gpt-4o,gpt-4.1-nano,gpt-3.5-turbo
OPENAI_AVAILABLE_MODELS=gpt-4o-mini,gpt-4o
OPENAI_DEFAULT_MODEL=gpt-4o-mini

# Google Gemini 配置
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODELS=gemini-1.5-flash,gemini-1.5-pro
GEMINI_AVAILABLE_MODELS=gemini-1.5-flash
GEMINI_DEFAULT_MODEL=gemini-1.5-flash

# Qwen 配置
QWEN_API_KEY=your_qwen_api_key
QWEN_MODELS=qwen-turbo,qwen-plus
QWEN_AVAILABLE_MODELS=qwen-turbo
QWEN_DEFAULT_MODEL=qwen-turbo
```

#### CORS 配置
```bash
# 允許的來源
CORS_ALLOWED_ORIGINS=http://localhost:4321,http://127.0.0.1:4321

# API 安全配置
API_REQUIRE_AUTHENTICATION=false
API_REQUIRE_CSRF=false
API_RATE_LIMIT_ENABLED=false
```

## API 使用

### 獲取可用模型列表
```bash
curl -X GET "http://127.0.0.1:8000/maya-v2/available-models/"
```

### 使用指定模型進行對話
```bash
# 使用 GPT-4o-mini 模型
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什麼是Java",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'

# 使用 Gemini 1.5 Flash 模型
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "如何實現多線程",
    "model_name": "gemini-1.5-flash",
    "sync": true,
    "use_knowledge_base": true
  }'

# 使用 Qwen Turbo 模型
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Python 裝飾器是什麼",
    "model_name": "gpt-4.1-nano",
    "sync": true,
    "use_knowledge_base": true
  }'

curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "想多了解你",
    "model_name": "gpt-4.1-nano",
    "sync": true,
    "use_knowledge_base": true
  }'

# 測試知識庫功能（當找不到相關內容時會明確說明）
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什麼是量子計算機？",
    "model_name": "gpt-4.1-nano",
    "sync": true,
    "use_knowledge_base": true
  }'
```

### 獲取對話歷史
```bash
curl -X GET "http://127.0.0.1:8000/maya-v2/chat-history/{session_id}/"
```

### 知識庫功能
系統支援知識庫搜索功能，當 `use_knowledge_base=true` 時：

- **找到相關內容**：AI 會基於知識庫內容回答，並提供引用資訊
- **未找到相關內容**：AI 會明確說明「無法從知識庫中找到相關的資訊來回答您的問題。以下回答基於我的訓練資料。」

回應中的 `knowledge_used` 欄位表示是否使用了知識庫內容：
- `true`：使用了知識庫內容
- `false`：未使用知識庫內容（會顯示說明訊息）

### 傳統對話 API（已棄用）
```bash
# 創建對話
curl -X POST "http://127.0.0.1:8000/maya-v2/conversations/" \
  -H "Content-Type: application/json" \
  -d '{"title": "新對話"}'

# 發送訊息
curl -X POST "http://127.0.0.1:8000/maya-v2/conversations/{conversation_id}/send_message/" \
  -H "Content-Type: application/json" \
  -d '{"content": "你好，請幫我解答問題"}'

# 獲取對話訊息
curl -X GET "http://127.0.0.1:8000/maya-v2/conversations/{conversation_id}/messages/"
```

## 部署

### Docker 部署
```bash
# 構建映像
docker build -t maya-sawa-v2 .

# 運行容器
docker run -d \
  --name maya-sawa-v2 \
  -p 8000:8000 \
  --env-file .env \
  maya-sawa-v2
```

### 生產環境配置
```bash
# 設置生產環境變數
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_DEBUG=false
DJANGO_ADMIN_URL=your_admin_url

# 資料庫連線池配置
DB_CONNECTION=pgsql
DB_HOST=your_db_host
DB_PORT=5432
DB_DATABASE=your_db_name
DB_USERNAME=your_db_user
DB_PASSWORD=your_db_password
DB_SSLMODE=require

# Redis 配置
REDIS_URL=redis://:password@host:port/0
CELERY_BROKER_URL=redis://:password@host:port/0
CELERY_RESULT_BACKEND=redis://:password@host:port/0
```

## 開發

### 代碼品質
```bash
# 運行測試
poetry run pytest

# 代碼格式化
poetry run ruff format .

# 代碼檢查
poetry run ruff check .

# 類型檢查
poetry run mypy maya_sawa_v2/
```

### 管理命令
```bash
# 設置 AI 模型
poetry run python manage.py setup_ai_models

# 切換 API 安全設置
poetry run python manage.py toggle_api_security

# 查看可用模型
poetry run python manage.py shell
>>> from maya_sawa_v2.ai_processing.models import AIModel
>>> AIModel.objects.filter(is_active=True).values('name', 'provider', 'model_id')
```

## 授權

MIT License
