# RAG 測試模組

一個完整的 RAG 系統測試框架，支援圖片測試、問題生成、答案評估和報告生成。

## 功能特色

- 🖼️ **圖片測試**: 支援多種圖片格式的測試
- 🤖 **Claude 整合**: 使用 Claude 進行問題生成和答案評估
- 📊 **詳細報告**: 生成包含圖片的 HTML 測試報告
- 💰 **成本追蹤**: 自動計算 API 使用成本
- ⚙️ **靈活配置**: 透過 .env 檔案進行所有配置
- 🎯 **互動式介面**: 支援選擇測試類別和數量

## 安裝需求

```bash
pip install requests pillow python-dotenv
```

## 配置設定

在專案根目錄的 `.env` 檔案中添加以下配置：

```env
# RAG 測試模組設定
RAG_TEST_API_URL=http://localhost:8006/api/v1/query
CLAUDE_API_KEY=your_claude_api_key_here
CLAUDE_MODEL=us.anthropic.claude-3-7-sonnet-20250219-v1:0
RAG_TEST_IMAGE_DIR=/path/to/your/images
RAG_TEST_RESULTS_DIR=./RAG_test_module/results
```

### 必要配置項目

- `RAG_TEST_API_URL`: RAG 系統的 API 端點
- `CLAUDE_API_KEY`: Claude API 金鑰 (用於問題生成和評估)
- `RAG_TEST_IMAGE_DIR`: 測試圖片目錄路徑

### 可選配置項目

- `CLAUDE_MODEL`: Claude 模型名稱 (預設: claude-3-7-sonnet)
- `CLAUDE_MAX_TOKENS`: Claude 最大 token 數 (預設: 4000)
- `CLAUDE_TEMPERATURE`: Claude 溫度參數 (預設: 0.7)
- `RAG_TEST_TIMEOUT`: API 超時時間 (預設: 30秒)
- `RAG_TEST_RETRY_COUNT`: 重試次數 (預設: 3次)
- `RAG_TEST_DELAY_BETWEEN_TESTS`: 測試間隔時間 (預設: 2秒)

## 使用方法

### 1. 互動式智能測試

```bash
cd RAG_test_module
python3 run_test.py
```

### 2. 命令行直接使用

```bash
# Excel 模式
python3 smart_tester.py /path/to/questions.xlsx

# 資料夾模式
python3 smart_tester.py /path/to/images/folder
```

### 3. 程式化使用

```python
from RAG_test_module import SmartRAGTester, InteractiveSmartTester

# 智能測試器
smart_tester = SmartRAGTester()
report_path = smart_tester.run_smart_test("/path/to/input")

# 互動式智能測試
interactive_tester = InteractiveSmartTester()
interactive_tester.run()
```

## 目錄結構

```
RAG_test_module/
├── config/
│   ├── __init__.py
│   └── test_config.py              # 配置管理
├── core/
│   ├── __init__.py
│   └── rag_tester.py              # 核心測試邏輯
├── utils/
│   ├── __init__.py
│   ├── image_utils.py             # 圖片處理工具
│   └── report_generator.py       # 報告生成器
├── results/                       # 測試結果目錄
├── __init__.py
├── smart_tester.py                # 智能測試器核心
├── interactive_smart_tester.py    # 互動式智能測試介面
├── run_test.py                    # 主要入口點
└── README.md
```

## 測試流程

1. **圖片掃描**: 掃描指定目錄中的圖片，按資料夾分類
2. **問題生成**: 使用 Claude 分析圖片並生成相關問題
3. **RAG 查詢**: 將問題發送到 RAG 系統獲取答案
4. **答案評估**: 使用 Claude 評估答案的技術準確性、完整性和清晰度
5. **成本計算**: 計算 API 使用成本
6. **報告生成**: 生成包含圖片的詳細 HTML 報告

## 評估標準

- **技術準確性** (40%): 回答是否技術正確
- **完整性** (30%): 回答是否完整回應問題
- **清晰度** (20%): 回答是否清楚易懂
- **圖片引用** (10%): 是否正確引用相關圖片

## 報告功能

- 📊 測試統計摘要
- 💰 詳細成本分析
- 📂 類別統計
- 🖼️ 圖片展示
- 📚 參考段落顯示
- 🔍 可展開/收合的內容區塊

## 故障排除

### 常見問題

1. **配置驗證失敗**
   - 檢查 `.env` 檔案中的必要配置項目
   - 確認 Claude API 金鑰有效
   - 驗證圖片目錄路徑存在

2. **API 連接失敗**
   - 檢查 RAG API URL 是否正確
   - 確認網路連接正常
   - 檢查 API 服務是否運行

3. **圖片處理錯誤**
   - 確認圖片格式支援 (PNG, JPG, JPEG, GIF, BMP)
   - 檢查圖片檔案是否損壞
   - 確認有足夠的磁碟空間

## 版本資訊

- **版本**: 1.0.0
- **Python 需求**: 3.7+
- **主要依賴**: requests, pillow, python-dotenv

## 授權

此模組為內部使用，請遵循相關使用規範。
