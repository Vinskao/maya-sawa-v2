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

<!-- 依現況精簡，移除未必要圖表 -->


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
    A->>AI: 調用指定模型(OpenAI/Gemini/Qwen)
    AI-->>A: 回傳 AI 回應
    A->>R: 追加 AI 訊息(chat:session)
    A->>DB: 建立 AI Message
    A-->>F: 回傳 AI 回應 + 引用

    Note over F,R: 可用 GET /maya-v2/qa/chat-history/{session_id}
```

<!-- 移除 ER 與安全圖以符合現況精簡需求 -->

## 快速開始

```bash
# 複製環境變量模板
cp .env.example .env

# 編輯 .env 文件，填入你的配置

# 安裝依賴
poetry install

# 數據庫遷移
poetry run python manage.py migrate
poetry run python manage.py setup_ai_models

# 創建超級用戶
poetry run python manage.py createsuperuser

# 啟動服務
poetry run python manage.py runserver

# Celery Worker（新終端）
poetry run celery -A config worker -l info -Q maya_v2
```

## API 使用

### 獲取可用模型列表
```bash
curl -X GET "http://127.0.0.1:8000/maya-v2/available-models/"
```

### 使用指定模型進行對話
```bash
# 使用 GPT-4.1-nano 模型
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什麼是Java",
    "model_name": "gpt-4.1-nano",
    "sync": true,
    "use_knowledge_base": true
  }'

# 使用 GPT-4o-mini 模型
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "如何實現多線程",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'
```

### 添加新的 AI 模型
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/add-model/"
```

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

## 授權

MIT License
