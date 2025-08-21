# Maya Sawa V2 - Pod 內多容器架構

## 整體 Pod 架構圖

```mermaid
graph TB
    subgraph "maya-sawa-v2 Pod"
        subgraph "Init Containers (初始化階段)"
            IC1["migrate<br/>Init Container<br/>python manage.py migrate"]
            IC2["collectstatic<br/>Init Container<br/>python manage.py collectstatic"]
        end
        
        subgraph "Main Containers (運行階段)"
            WC["web<br/>Container<br/>gunicorn config.wsgi:application<br/>Port: 8000"]
            WKC["worker<br/>Container<br/>celery -A config worker<br/>-l info -Q maya_v2"]
        end
        
        subgraph "Shared Resources"
            ENV["環境變數<br/>DJANGO_SETTINGS_MODULE<br/>DATABASE_URL<br/>REDIS_URL<br/>CELERY_BROKER_URL"]
            SECRETS["Secrets<br/>MAYA_V2_SECRET_KEY<br/>OPENAI_API_KEY<br/>DJANGO_ADMIN_URL"]
        end
    end
    
    subgraph "External Services"
        DB[(PostgreSQL<br/>Database)]
        REDIS[(Redis<br/>Cache + Broker)]
        AI[OpenAI API]
    end
    
    %% 連接關係
    IC1 --> DB
    WC --> DB
    WKC --> DB
    WC --> REDIS
    WKC --> REDIS
    WC --> AI
    WKC --> AI
    
    %% 資源共享
    WC -.-> ENV
    WKC -.-> ENV
    WC -.-> SECRETS
    WKC -.-> SECRETS
    
    %% 樣式
    classDef initContainer fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef mainContainer fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef sharedResource fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef externalService fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    
    class IC1,IC2 initContainer
    class WC,WKC mainContainer
    class ENV,SECRETS sharedResource
    class DB,REDIS,AI externalService
```

## 容器詳細配置

### Init Containers (初始化容器)

#### 1. migrate 容器
```yaml
- name: migrate
  image: papakao/maya-sawa-v2:latest
  command: ["bash", "-lc", "python manage.py migrate --noinput"]
  env:
    - name: DJANGO_SETTINGS_MODULE
      value: config.settings.production
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: app-config
          key: DATABASE_URL
    - name: MAYA_V2_SECRET_KEY
      valueFrom:
        secretKeyRef:
          name: django-secrets
          key: MAYA_V2_SECRET_KEY
```

#### 2. collectstatic 容器
```yaml
- name: collectstatic
  image: papakao/maya-sawa-v2:latest
  command: ["bash", "-lc", "python manage.py collectstatic --noinput"]
  env:
    - name: DJANGO_SETTINGS_MODULE
      value: config.settings.production
    - name: MAYA_V2_SECRET_KEY
      valueFrom:
        secretKeyRef:
          name: django-secrets
          key: MAYA_V2_SECRET_KEY
```

### Main Containers (主要容器)

#### 1. web 容器 (Django + Gunicorn)
```yaml
- name: web
  image: papakao/maya-sawa-v2:latest
  ports:
    - containerPort: 8000
  resources:
    requests:
      cpu: 25m
      memory: 128Mi
    limits:
      cpu: 100m
      memory: 256Mi
  env:
    - name: DJANGO_SETTINGS_MODULE
      value: config.settings.production
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: app-config
          key: DATABASE_URL
    - name: REDIS_URL
      valueFrom:
        secretKeyRef:
          name: app-config
          key: REDIS_URL
    - name: CELERY_BROKER_URL
      valueFrom:
        secretKeyRef:
          name: app-config
          key: CELERY_BROKER_URL
    - name: OPENAI_API_KEY
      valueFrom:
        secretKeyRef:
          name: django-secrets
          key: OPENAI_API_KEY
  readinessProbe:
    httpGet:
      path: /healthz
      port: 8000
    initialDelaySeconds: 20
    periodSeconds: 10
  livenessProbe:
    httpGet:
      path: /healthz
      port: 8000
    initialDelaySeconds: 45
    periodSeconds: 30
```

#### 2. worker 容器 (Celery)
```yaml
- name: worker
  image: papakao/maya-sawa-v2:latest
  command: ["bash", "-lc", "celery -A config worker -l info -Q maya_v2"]
  resources:
    requests:
      cpu: 25m
      memory: 128Mi
    limits:
      cpu: 100m
      memory: 256Mi
  env:
    - name: DJANGO_SETTINGS_MODULE
      value: config.settings.production
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: app-config
          key: DATABASE_URL
    - name: REDIS_URL
      valueFrom:
        secretKeyRef:
          name: app-config
          key: REDIS_URL
    - name: CELERY_BROKER_URL
      valueFrom:
        secretKeyRef:
          name: app-config
          key: CELERY_BROKER_URL
    - name: OPENAI_API_KEY
      valueFrom:
        secretKeyRef:
          name: django-secrets
          key: OPENAI_API_KEY
```

## 容器啟動順序

```mermaid
sequenceDiagram
    participant K8s as Kubernetes
    participant IC1 as migrate
    participant IC2 as collectstatic
    participant WC as web
    participant WKC as worker
    participant DB as PostgreSQL
    participant R as Redis

    K8s->>IC1: 啟動 migrate 容器
    IC1->>DB: 執行資料庫遷移
    IC1-->>K8s: 遷移完成
    
    K8s->>IC2: 啟動 collectstatic 容器
    IC2-->>K8s: 靜態文件收集完成
    
    K8s->>WC: 啟動 web 容器
    WC->>DB: 連接資料庫
    WC->>R: 連接 Redis
    WC-->>K8s: Web 服務就緒
    
    K8s->>WKC: 啟動 worker 容器
    WKC->>DB: 連接資料庫
    WKC->>R: 連接 Redis (作為 Celery Broker)
    WKC-->>K8s: Worker 服務就緒
    
    Note over K8s: Pod 完全就緒
```

## 資源分配

### CPU 和記憶體分配
```mermaid
pie title Pod 資源分配
    "web container" : 100m CPU, 256Mi RAM
    "worker container" : 100m CPU, 256Mi RAM
    "init containers" : 臨時使用
```

### 網絡配置
```mermaid
graph LR
    subgraph "Pod Network"
        WC[web:8000]
        WKC[worker:no port]
    end
    
    subgraph "External"
        SVC[Service:80->8000]
        ING[Ingress]
    end
    
    WC --> SVC
    SVC --> ING
    WKC -.->|internal| WC
```

## 故障處理機制

### 容器重啟策略
```mermaid
graph TD
    A[容器故障] --> B{故障類型}
    B -->|Init Container| C[Pod 重啟]
    B -->|Main Container| D[容器重啟]
    
    C --> E[重新執行所有 Init Containers]
    D --> F[保持其他容器運行]
    
    E --> G[重新啟動 Main Containers]
    F --> H[健康檢查]
    
    G --> H
    H --> I{健康檢查通過?}
    I -->|是| J[Pod 就緒]
    I -->|否| K[繼續重啟]
    K --> H
```

### 健康檢查
- **web 容器**: HTTP GET `/healthz`
- **worker 容器**: 無健康檢查 (Celery 內部管理)
- **init 容器**: 命令執行成功即為健康

## 優缺點分析

### 優點 ✅
1. **簡單部署**: 一個 Pod 包含所有組件
2. **共享配置**: 環境變數和 secrets 統一管理
3. **資源共享**: 可以共享 volume 和網絡
4. **故障隔離**: 如果一個容器失敗，其他容器仍可運行
5. **原子性**: 所有組件一起啟動和停止

### 缺點 ⚠️
1. **資源競爭**: Web 和 Worker 競爭 CPU/記憶體
2. **擴展限制**: 無法獨立擴展 Web 或 Worker
3. **單點故障**: Pod 重啟會影響所有服務
4. **資源浪費**: 無法針對不同服務優化資源分配
5. **調試困難**: 多個容器日誌混合在一起

## 建議的改進架構

### 分離部署 (推薦)
```mermaid
graph TB
    subgraph "Web Deployment"
        WC1[web-1]
        WC2[web-2]
        WC3[web-3]
    end
    
    subgraph "Worker Deployment"
        WKC1[worker-1]
        WKC2[worker-2]
        WKC3[worker-3]
        WKC4[worker-4]
    end
    
    subgraph "Shared Services"
        DB[(PostgreSQL)]
        REDIS[(Redis)]
    end
    
    WC1 --> DB
    WC2 --> DB
    WC3 --> DB
    WKC1 --> DB
    WKC2 --> DB
    WKC3 --> DB
    WKC4 --> DB
    
    WC1 --> REDIS
    WC2 --> REDIS
    WC3 --> REDIS
    WKC1 --> REDIS
    WKC2 --> REDIS
    WKC3 --> REDIS
    WKC4 --> REDIS
```

這樣可以：
- **獨立擴展** Web 和 Worker
- **資源優化** 針對不同服務分配資源
- **故障隔離** 更好的容錯能力
- **監控分離** 更清晰的日誌和監控
