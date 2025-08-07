# Maya Sawa V2 API 測試

這個資料夾包含了 Maya Sawa V2 的 API 測試文件。

## 📁 測試文件說明

### 1. `test_conversation_api_simple.py`
- **功能**: 使用 Python 內建模組測試 API
- **依賴**: 僅使用 Python 內建模組（urllib, json）
- **測試內容**:
  - 直接問答 API
  - AI 提供者配置
  - 對話列表
  - 顯示對應的 curl 命令

### 2. `test_traditional_conversation_api.py`
- **功能**: 完整的傳統對話流程測試
- **依賴**: 需要安裝 `requests` 模組
- **測試內容**:
  - 創建對話
  - 發送訊息
  - 等待 AI 處理
  - 查看訊息歷史

### 3. `test_openai_fix.py`
- **功能**: 測試 OpenAI 客戶端修復
- **依賴**: Django 環境
- **測試內容**:
  - OpenAI 提供者配置
  - Mock 提供者測試
  - API 端點驗證

### 4. `run_api_tests.sh`
- **功能**: Shell 腳本自動化測試
- **依賴**: 需要 `curl` 和 `python3`
- **測試內容**: 所有主要 API 端點的快速測試

## 🚀 使用方法

### 方法 1: 使用 Shell 腳本（推薦）
```bash
# 確保服務正在運行
poetry run python manage.py runserver

# 在另一個終端運行測試
./tests/run_api_tests.sh
```

### 方法 2: 使用 Python 測試腳本
```bash
# 運行簡單測試（無外部依賴）
python3 tests/test_conversation_api_simple.py

# 運行完整測試（需要 requests）
pip install requests
python3 tests/test_traditional_conversation_api.py

# 運行 OpenAI 修復測試
python3 tests/test_openai_fix.py
```

### 方法 3: 手動測試
```bash
# 1. 直接問答 API
curl "http://127.0.0.1:8000/maya-v2/conversations/ask/?question=你好，請介紹一下這個系統&sync=true"

# 2. 獲取 AI 提供者
curl "http://127.0.0.1:8000/maya-v2/conversations/ai_providers/"

# 3. 獲取對話列表
curl "http://127.0.0.1:8000/maya-v2/conversations/"

# 4. 創建新對話
curl -X POST "http://127.0.0.1:8000/maya-v2/conversations/" \
  -H "Content-Type: application/json" \
  -d '{"title": "測試對話", "conversation_type": "general", "session_id": "test-123"}'
```

## 📋 API 端點說明

### 直接問答 API（推薦）
- **端點**: `GET /maya-v2/conversations/ask/`
- **參數**: 
  - `question`: 問題內容
  - `sync`: 是否同步處理（true/false）
  - `model`: 指定 AI 模型
- **用途**: 最簡單的 AI 對話方式

### 傳統對話流程
1. **創建對話**: `POST /maya-v2/conversations/`
2. **發送訊息**: `POST /maya-v2/conversations/{id}/send_message/`
3. **查看訊息**: `GET /maya-v2/conversations/{id}/messages/`

### AI 模型相關
- **獲取提供者**: `GET /maya-v2/conversations/ai_providers/`
- **獲取模型列表**: `GET /maya-v2/ai-models/`

## 🔧 故障排除

### OpenAI 客戶端錯誤修復
**問題**: `Client.__init__() got an unexpected keyword argument 'proxies'`

**解決方案**: 
1. 已修復 `maya_sawa_v2/ai_processing/ai_providers.py`
2. 移除了不支援的參數傳遞
3. 改進了錯誤處理

**測試修復**:
```bash
python3 tests/test_openai_fix.py
```

### 連接錯誤
```bash
# 確保服務正在運行
poetry run python manage.py runserver
```

### URL 編碼問題
```bash
# 使用 curl 的 -G 參數
curl -G "http://127.0.0.1:8000/maya-v2/conversations/ask/" \
  --data-urlencode "question=你好，請介紹一下這個系統" \
  --data-urlencode "sync=true"
```

### 權限問題
```bash
# 給腳本執行權限
chmod +x tests/run_api_tests.sh
```

## 📊 測試結果解讀

### 成功回應範例
```json
{
  "session_id": "qa-abc12345",
  "conversation_id": "uuid-here",
  "question": "你的問題",
  "ai_model": {
    "id": 1,
    "name": "GPT-4o Mini",
    "provider": "openai"
  },
  "status": "completed",
  "ai_response": "AI 的回應內容"
}
```

### 錯誤回應範例
```json
{
  "error": "錯誤訊息"
}
```

## 🎯 測試重點

1. **服務連接**: 確保 Django 服務正在運行
2. **API 端點**: 測試所有主要端點是否正常
3. **參數處理**: 測試 URL 編碼和 JSON 數據
4. **回應格式**: 確認回應格式正確
5. **錯誤處理**: 測試錯誤情況的處理
6. **OpenAI 修復**: 驗證客戶端配置修復

## 📝 注意事項

- 測試前請確保服務正在運行
- 開發環境已禁用認證，可直接測試
- 如果使用異步處理，需要等待 AI 回應
- 建議先測試直接問答 API，再測試完整流程
- OpenAI 客戶端錯誤已修復，如果仍有問題請檢查 API Key 配置

## 🔄 最近修復

### OpenAI 客戶端配置問題
- **問題**: `Client.__init__() got an unexpected keyword argument 'proxies'`
- **原因**: 傳遞了不支援的參數給 OpenAI 客戶端
- **修復**: 
  - 只傳遞支援的參數（api_key, base_url, organization）
  - 改進了錯誤處理
  - 添加了更好的參數驗證
- **測試**: 使用 `test_openai_fix.py` 驗證修復
