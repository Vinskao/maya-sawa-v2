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
        B --> A4[add-model]
        B --> A5[healthz]
        B --> A6[legacy-chat-history]
    end

    subgraph "Agent 服務層"
        AS[MayaAgentService<br/>LangGraph 整合]
    end

    subgraph "LangGraph 工作流層"
        WF[MayaAgentWorkflow<br/>圖形化工作流]
        N1[意圖分類節點<br/>FilterChain]
        N2[知識檢索節點<br/>KMSourceManager]
        N3[工具選擇節點<br/>智能工具選擇]
        N4[工具執行節點<br/>PDF/OCR/計算/搜索]
        N5[AI 回應生成節點<br/>LLM 調用]
        N6[結果保存節點<br/>資料持久化]
        N7[錯誤處理節點<br/>異常處理]
    end

    subgraph "能力支撐層"
        LLM[LLM 能力<br/>OpenAI/Gemini/Qwen]
        TOOLS[工具能力<br/>PDF/OCR/計算/搜索]
        MEMORY[記憶能力<br/>Redis/向量記憶]
        RAG[RAG 能力<br/>pgvector/混合檢索]
    end

    subgraph "資料層"
        D1[(PostgreSQL<br/>Conversations/Articles)]
        D2[(Redis<br/>Cache/Memory)]
        D3[(RabbitMQ<br/>Celery Broker)]
    end

    subgraph "外部系統"
        E1[Paprika API]
        E2[OpenAI API]
        E3[Google Gemini API]
        E4[Qwen API]
    end

    %% API 到 Agent 服務層
    A1 --> AS

    %% Agent 服務層到工作流層
    AS --> WF

    %% 工作流節點連接
    WF --> N1
    WF --> N2
    WF --> N3
    WF --> N4
    WF --> N5
    WF --> N6
    WF --> N7

    %% 工作流節點到能力層
    N1 --> LLM
    N2 --> RAG
    N3 --> TOOLS
    N4 --> TOOLS
    N5 --> LLM
    N6 --> MEMORY

    %% 能力層到資料層
    LLM --> D1
    TOOLS --> D1
    MEMORY --> D2
    RAG --> D1

    %% 外部系統連接
    LLM --> E2
    LLM --> E3
    LLM --> E4
    RAG --> E1

    %% 樣式定義
    classDef api fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef agent fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef workflow fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef capability fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    classDef data fill:#f1f8e9,stroke:#43a047,stroke-width:2px
    classDef external fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px

    class A1,A2,A3,A4,A5,A6 api
    class AS agent
    class WF,N1,N2,N3,N4,N5,N6,N7 workflow
    class LLM,TOOLS,MEMORY,RAG capability
    class D1,D2,D3 data
    class E1,E2,E3,E4 external
```

## 對話流程圖 (LangGraph 工作流)

```mermaid
sequenceDiagram
    participant U as 用戶
    participant F as 前端
    participant A as API
    participant AS as Agent Service
    participant WF as LangGraph Workflow
    participant N1 as 意圖分類節點
    participant N2 as 知識檢索節點
    participant N3 as 工具選擇節點
    participant N4 as 工具執行節點
    participant N5 as AI 回應生成節點
    participant N6 as 結果保存節點
    participant DB as PostgreSQL
    participant R as Redis

    U->>F: 發送問題
    F->>A: POST /maya-v2/ask-with-model/
    A->>AS: 處理請求 (保持 API 格式兼容)
    AS->>DB: 建立 Conversation, Message
    
    Note over AS,WF: LangGraph 工作流執行
    AS->>WF: 初始化 AgentState
    WF->>N1: 意圖分類 (FilterChain)
    N1-->>WF: 返回意圖和置信度
    
    WF->>N2: 知識檢索 (KMSourceManager)
    N2->>DB: 混合檢索 (trigram + pgvector)
    DB-->>N2: Top-K 相關內容
    N2-->>WF: 返回知識上下文
    
    WF->>N3: 工具選擇 (智能分析)
    N3-->>WF: 返回需要使用的工具列表
    
    alt 需要工具
        WF->>N4: 工具執行
        N4-->>WF: 返回工具執行結果
    end
    
    WF->>N5: AI 回應生成 (LLM 調用)
    N5-->>WF: 返回 AI 回應
    
    WF->>N6: 結果保存
    N6->>DB: 保存對話記錄
    N6->>R: 更新聊天歷史
    N6-->>WF: 保存完成
    
    WF-->>AS: 返回 WorkflowResult
    AS->>DB: 建立 AI Message
    AS-->>A: 返回 API 回應 (保持格式兼容)
    A-->>F: 回傳 AI 回應 + 工作流元數據
    F-->>U: 顯示回應

    Note over F,R: 可用 GET /maya-sawa/qa/chat-history/{session_id}
```

## 傳統流程圖 (對比)

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
    
    alt 找到相關內容
        A->>AI: 調用指定模型 + 知識庫內容
        AI-->>A: 回傳 AI 回應 + 引用資訊
    else 未找到相關內容
        A->>AI: 調用指定模型
        AI-->>A: 回傳 AI 回應 + 無法找到知識庫說明
    end
    
    A->>R: 追加 AI 訊息(chat:session)
    A->>DB: 建立 AI Message
    A-->>F: 回傳 AI 回應 + 知識庫狀態

    Note over F,R: 可用 GET /maya-sawa/qa/chat-history/{session_id}
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
  AI --> RESP["Answer + Citations/No Knowledge Notice"]
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

## LangGraph 工作流架構圖

```mermaid
graph TB
    subgraph "工作流入口"
        START[用戶請求] --> AS[MayaAgentService]
    end

    subgraph "LangGraph 工作流"
        AS --> WF[MayaAgentWorkflow]
        
        subgraph "工作流節點"
            WF --> N1[意圖分類節點<br/>classify_intent_node]
            N1 --> N2[知識檢索節點<br/>retrieve_knowledge_node]
            N2 --> N3[工具選擇節點<br/>select_tools_node]
            N3 --> N4[工具執行節點<br/>execute_tools_node]
            N4 --> N5[AI 回應生成節點<br/>generate_response_node]
            N5 --> N6[結果保存節點<br/>save_result_node]
        end
        
        subgraph "錯誤處理"
            N1 --> ERROR[錯誤處理節點<br/>error_handler_node]
            N2 --> ERROR
            N3 --> ERROR
            N4 --> ERROR
            N5 --> ERROR
            N6 --> ERROR
        end
    end

    subgraph "能力支撐層"
        N1 --> LLM[LLM 能力<br/>OpenAI/Gemini/Qwen]
        N2 --> RAG[RAG 能力<br/>pgvector/混合檢索]
        N3 --> TOOLS[工具能力<br/>PDF/OCR/計算/搜索]
        N4 --> TOOLS
        N5 --> LLM
        N6 --> MEMORY[記憶能力<br/>Redis/向量記憶]
    end

    subgraph "資料存儲"
        LLM --> DB[(PostgreSQL)]
        RAG --> DB
        TOOLS --> DB
        MEMORY --> REDIS[(Redis)]
    end

    subgraph "外部系統"
        LLM --> OPENAI[OpenAI API]
        LLM --> GEMINI[Gemini API]
        LLM --> QWEN[Qwen API]
        RAG --> PAPRIKA[Paprika API]
    end

    %% 樣式定義
    classDef entry fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef workflow fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef node fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef capability fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    classDef storage fill:#f1f8e9,stroke:#43a047,stroke-width:2px
    classDef external fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px

    class START,AS entry
    class WF workflow
    class N1,N2,N3,N4,N5,N6,ERROR node
    class LLM,RAG,TOOLS,MEMORY capability
    class DB,REDIS storage
    class OPENAI,GEMINI,QWEN,PAPRIKA external
```

## 快速開始
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

# 9. 啟動服務（同時啟動 Django 和 Celery Worker）
lsof -ti:8000 | xargs kill -9 2>/dev/null; poetry run python manage.py runserver & poetry run celery -A config worker -l info -Q maya_v2

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

# 資料庫連接池設置（限制最多 5 個連接）
CONN_MAX_AGE=60
DB_MAX_CONNS=5
```

#### AI 提供者配置
目前本專案主要使用 OpenAI，其他提供者（Gemini、Qwen）已配置但需要額外設置：
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

**注意：**
- 目前系統預設只啟用 OpenAI 提供者
- 如需使用 Gemini，請設置 `GOOGLE_API_KEY` 並在 `ENABLED_PROVIDERS` 中加入 `gemini`
- 如需使用 Qwen，請設置 `QWEN_API_KEY` 並在 `ENABLED_PROVIDERS` 中加入 `qwen`
- 所有提供者都支援 Mock 模式用於測試

#### CORS 配置
```bash
# 允許的來源
CORS_ALLOWED_ORIGINS=http://localhost:4321,http://127.0.0.1:4321

# API 安全配置
API_REQUIRE_AUTHENTICATION=false
API_REQUIRE_CSRF=false
API_RATE_LIMIT_ENABLED=false
```

## API 使用與測試

### 📋 完整 API 查詢過程記錄

#### **方式一：同步處理（推薦用於簡單問題）**

##### 1. 健康檢查
```bash
curl -X GET "http://127.0.0.1:8000/healthz"
```
**預期回應：**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-25T10:30:00Z"
}
```

##### 2. 獲取可用模型列表
```bash
curl -X GET "http://127.0.0.1:8000/maya-v2/available-models/"
```
**預期回應：**
```json
[
  {
    "id": 6,
    "name": "GPT-4o Mini",
    "provider": "openai",
    "is_active": true
  },
  {
    "id": 7,
    "name": "GPT-4o",
    "provider": "openai",
    "is_active": true
  }
]
```

##### 3. 提交同步問題
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "你好，這是一個測試問題。請簡單介紹一下你自己。",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'
```
**預期回應：**
```json
{
  "session_id": "qa-1f44cbba",
  "conversation_id": "de71a9c9-c932-4735-bf0e-4bf3a8c477dc",
  "question": "你好，這是一個測試問題。請簡單介紹一下你自己。",
  "ai_model": {
    "id": 6,
    "name": "GPT-4o Mini",
    "provider": "openai"
  },
  "status": "completed",
  "ai_response": "你好！我是一個 AI 助手...",
  "knowledge_used": true,
  "knowledge_citations": [
    {
      "article_id": 16,
      "title": "相關文章標題",
      "file_path": "article.md",
      "source": "paprika_16",
      "source_url": "https://example.com/article.md",
      "provider": "Paprika"
    }
  ],
  "message": "AI回答已完成"
}
```

---

#### **方式二：異步處理（推薦用於複雜問題）**

##### 1. 提交異步問題
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Java 中的多線程是什麼？請詳細解釋並提供代碼範例。",
    "model_name": "gpt-4o-mini",
    "sync": false,
    "use_knowledge_base": true
  }'
```
**立即回應：**
```json
{
  "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
  "status": "queued",
  "message": "Task has been queued for processing",
  "conversation_id": "461daa00-29ad-45c0-bb95-5170a6bbbe3c",
  "question": "Java 中的多線程是什麼？請詳細解釋並提供代碼範例。",
  "ai_model": {
    "id": 6,
    "name": "GPT-4o Mini",
    "provider": "openai"
  }
}
```

##### 2. 查詢任務狀態（輪詢）
```bash
curl -X GET "http://127.0.0.1:8000/maya-v2/task-status/a7e35f8e-c09d-4a25-868b-dd97173c00c6"
```

**任務執行中：**
```json
{
  "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
  "status": "STARTED",
  "message": "Task is currently being processed"
}
```

**任務完成：**
```json
{
  "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
  "status": "SUCCESS",
  "ai_response": "Java 中的多線程是指...",
  "conversation_id": "461daa00-29ad-45c0-bb95-5170a6bbbe3c",
  "question": "Java 中的多線程是什麼？請詳細解釋並提供代碼範例。",
  "ai_model": {
    "id": 6,
    "name": "GPT-4o Mini",
    "provider": "openai"
  },
  "processing_time": 2.5,
  "completed_at": "2025-08-25T10:52:40Z",
  "knowledge_used": true,
  "knowledge_citations": [
    {
      "article_id": 16,
      "title": "Java 多線程指南",
      "file_path": "java-multithreading.md",
      "source": "paprika_16",
      "source_url": "https://example.com/java-multithreading.md",
      "provider": "Paprika"
    }
  ],
  "metadata": {
    "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
    "status": "completed"
  }
}
```

**任務失敗：**
```json
{
  "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
  "status": "FAILURE",
  "error": "處理失敗的詳細錯誤訊息",
  "traceback": "錯誤堆疊追蹤"
}
```

---

#### **方式三：特定功能測試**

##### 1. 測試工具選擇功能（計算器）
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "請幫我計算 123 + 456 等於多少？",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'
```

##### 2. 測試編程問題（知識庫檢索）
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Python 中的裝飾器是什麼？",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'
```

##### 3. 測試聊天歷史查詢
```bash
curl -X GET "http://127.0.0.1:8000/maya-sawa/qa/chat-history/test_session_123/"
```
**預期回應：**
```json
{
  "session_id": "test_session_123",
  "meta": {
    "created_at": "2025-08-25T10:30:00Z",
    "message_count": 4
  },
  "messages": [
    {
      "role": "user",
      "content": "你好",
      "timestamp": "2025-08-25T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "你好！我是 AI 助手...",
      "timestamp": "2025-08-25T10:30:05Z"
    }
  ]
}
```

---

### 🔄 前端實現範例

#### **JavaScript 異步處理完整流程**

```javascript
class MayaSawaAPI {
  constructor(baseURL = 'http://127.0.0.1:8000') {
    this.baseURL = baseURL;
  }

  // 提交問題（異步）
  async submitQuestion(question, modelName = 'gpt-4o-mini', useKnowledgeBase = true) {
    const response = await fetch(`${this.baseURL}/maya-v2/ask-with-model/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        model_name: modelName,
        sync: false,
        use_knowledge_base: useKnowledgeBase
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }

  // 查詢任務狀態
  async getTaskStatus(taskId) {
    const response = await fetch(`${this.baseURL}/maya-v2/task-status/${taskId}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }

  // 輪詢任務結果
  async pollTaskResult(taskId, interval = 2000, maxAttempts = 30) {
    let attempts = 0;
    
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getTaskStatus(taskId);
          
          if (status.status === 'SUCCESS') {
            resolve(status);
          } else if (status.status === 'FAILURE') {
            reject(new Error(status.error || 'Task failed'));
          } else if (attempts >= maxAttempts) {
            reject(new Error('Polling timeout'));
          } else {
            attempts++;
            setTimeout(poll, interval);
          }
        } catch (error) {
          reject(error);
        }
      };
      
      poll();
    });
  }

  // 獲取可用模型
  async getAvailableModels() {
    const response = await fetch(`${this.baseURL}/maya-v2/available-models/`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }
}

// 使用範例
const api = new MayaSawaAPI();

// 提交問題並輪詢結果
async function askQuestion(question) {
  try {
    console.log('提交問題:', question);
    
    // 1. 提交問題
    const submitResult = await api.submitQuestion(question);
    console.log('任務已提交:', submitResult.task_id);
    
    // 2. 輪詢結果
    const result = await api.pollTaskResult(submitResult.task_id);
    console.log('AI 回答:', result.ai_response);
    
    return result;
  } catch (error) {
    console.error('錯誤:', error.message);
  }
}

// 使用
askQuestion("Java 中的多線程是什麼？");
```

---

### 📊 API 狀態碼說明

| 狀態碼 | 說明 | 處理方式 |
|--------|------|----------|
| `PENDING` | 任務等待執行 | 繼續輪詢 |
| `STARTED` | 任務正在執行中 | 繼續輪詢 |
| `SUCCESS` | 任務完成成功 | 獲取結果 |
| `FAILURE` | 任務執行失敗 | 查看錯誤信息 |

---

### 🚀 快速測試命令

#### 1. 健康檢查
```bash
curl -X GET "http://127.0.0.1:8000/healthz"
```

#### 2. 獲取可用模型列表
```bash
curl -X GET "http://127.0.0.1:8000/maya-v2/available-models/"
```

#### 3. 測試同步 API (LangGraph 工作流)
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "你好，這是一個測試問題。請簡單介紹一下你自己。",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'
```

#### 4. 測試異步 API (Celery 任務)
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "這是一個異步測試問題。請告訴我今天的日期。",
    "model_name": "gpt-4o-mini",
    "sync": false,
    "use_knowledge_base": true
  }'
```

#### 5. 測試工具選擇功能
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "請幫我計算 123 + 456 等於多少？",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'
```

#### 6. 測試編程問題 (知識庫檢索)
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/ask-with-model/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Python 中的裝飾器是什麼？",
    "model_name": "gpt-4o-mini",
    "sync": true,
    "use_knowledge_base": true
  }'
```

#### 7. 測試聊天歷史
```bash
curl -X GET "http://127.0.0.1:8000/maya-sawa/qa/chat-history/test_session_123/"
```

### 📋 預期回應格式

#### **同步 API 成功回應**
```json
{
  "session_id": "qa-1f44cbba",
  "conversation_id": "de71a9c9-c932-4735-bf0e-4bf3a8c477dc",
  "question": "你好，這是一個測試問題。請簡單介紹一下你自己。",
  "ai_model": {
    "id": 6,
    "name": "GPT-4o Mini",
    "provider": "openai"
  },
  "status": "completed",
  "ai_response": "你好！我是一個 AI 助手...",
  "knowledge_used": true,
  "knowledge_citations": [
    {
      "article_id": 16,
      "title": "相關文章標題",
      "file_path": "article.md",
      "source": "paprika_16",
      "source_url": "https://example.com/article.md",
      "provider": "Paprika"
    }
  ],
  "message": "AI回答已完成"
}
```

#### **異步 API 提交回應**
```json
{
  "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
  "status": "queued",
  "message": "Task has been queued for processing",
  "conversation_id": "461daa00-29ad-45c0-bb95-5170a6bbbe3c",
  "question": "Java 中的多線程是什麼？",
  "ai_model": {
    "id": 6,
    "name": "GPT-4o Mini",
    "provider": "openai"
  }
}
```

#### **異步 API 完成回應**
```json
{
  "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
  "status": "SUCCESS",
  "ai_response": "Java 中的多線程是指...",
  "conversation_id": "461daa00-29ad-45c0-bb95-5170a6bbbe3c",
  "question": "Java 中的多線程是什麼？",
  "ai_model": {
    "id": 6,
    "name": "GPT-4o Mini",
    "provider": "openai"
  },
  "processing_time": 2.5,
  "completed_at": "2025-08-25T10:52:40Z",
  "knowledge_used": true,
  "knowledge_citations": [
    {
      "article_id": 16,
      "title": "Java 多線程指南",
      "file_path": "java-multithreading.md",
      "source": "paprika_16",
      "source_url": "https://example.com/java-multithreading.md",
      "provider": "Paprika"
    }
  ],
  "metadata": {
    "task_id": "a7e35f8e-c09d-4a25-868b-dd97173c00c6",
    "status": "completed"
  }
}
```

#### **錯誤回應格式**
```json
{
  "error": "錯誤訊息",
  "details": "詳細錯誤信息（可選）"
}
```

### 完整測試腳本

#### 運行 bash 測試腳本
```bash
# 給腳本執行權限
chmod +x test_curl_api.sh

# 運行測試
./test_curl_api.sh
```

#### 運行 Python 測試
```bash
python test_celery_langgraph.py
```

### 其他 API 端點

#### 添加 AI 模型
```bash
curl -X POST "http://127.0.0.1:8000/maya-v2/add-model/"
```

#### 使用指定模型進行對話
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

```

### 服務啟動檢查

#### 1. Django 服務器未運行
```bash
# 啟動 Django 服務器
poetry run python manage.py runserver
```

#### 2. Celery Worker 未運行
```bash
# 啟動 Celery Worker
poetry run celery -A config worker -l info -Q maya_v2
```

#### 3. RabbitMQ 未運行
```bash
# 啟動 RabbitMQ
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=admin123 \
  rabbitmq:3-management
```

#### 4. 檢查 RabbitMQ 管理界面
```bash
# 訪問管理界面
open http://localhost:15672
# 用戶名: admin
# 密碼: admin123
```

#### 5. 檢查 Celery 狀態
```bash
# 檢查 Celery Worker 狀態
poetry run celery -A config inspect active

# 檢查隊列狀態
poetry run celery -A config inspect stats
```

### 監控和日誌

#### 查看 Django 日誌
```bash
poetry run python manage.py runserver --verbosity=2
```

#### 查看 Celery Worker 日誌
```bash
poetry run celery -A config worker -l debug -Q maya_v2
```

#### 查看 RabbitMQ 日誌
```bash
docker logs rabbitmq
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

### 監控連接使用
```bash
# 檢查當前連接狀態
poetry run python manage.py check_db_connections

# 持續監控連接使用
poetry run python manage.py monitor_connections --interval 10 --count 20
```

### 管理命令
```bash
# 設置 AI 模型
poetry run python manage.py setup_ai_models

# 切換 API 安全設置
poetry run python manage.py toggle_api_security

# 回填文章嵌入向量
poetry run python manage.py backfill_article_embeddings

# 查看可用模型
poetry run python manage.py shell
>>> from maya_sawa_v2.ai_processing.models import AIModel
>>> AIModel.objects.filter(is_active=True).values('name', 'provider', 'model_id')
```

## 授權

MIT License
