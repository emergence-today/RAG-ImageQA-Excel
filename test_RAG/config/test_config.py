"""
RAG測試系統配置文件
只包含測試特定的配置，環境相關配置請使用 .env 文件
"""

import os
from pathlib import Path

class RAGTestConfig:
    """RAG測試配置類"""

    # 路徑配置
    BASE_DIR = Path(__file__).parent.parent.parent
    IMAGES_DIR = BASE_DIR / "outputs" / "images" / "zerox_output"
    MAIN_PY_PATH = BASE_DIR / "main.py"
    RESULTS_DIR = Path(__file__).parent.parent / "results"

    # 測試配置
    DEFAULT_SESSION_ID = "rag_test_session"
    API_DELAY = 2  # 秒，避免API限制
    MAX_RETRIES = 3

    # API配置（從環境變數讀取，這裡只是預設值）
    @classmethod
    def get_api_base_url(cls):
        """從環境變數獲取API基礎URL"""
        return os.getenv("API_BASE_URL", "http://localhost:8006")

    @classmethod
    def get_api_timeout(cls):
        """從環境變數獲取API超時時間"""
        return int(os.getenv("API_TIMEOUT", "60"))
    
    # 評分權重配置
    EVALUATION_WEIGHTS = {
        "technical_accuracy": 0.4,
        "completeness": 0.3,
        "image_reference": 0.2,
        "clarity": 0.1
    }
    
    # 評分標準
    SCORING_CRITERIA = {
        "technical_accuracy": {
            "完全正確": 1.0,
            "大部分正確": 0.8,
            "部分正確": 0.6,
            "有錯誤": 0.4,
            "完全錯誤": 0.0
        },
        "completeness": {
            "完整回答": 1.0,
            "基本完整": 0.8,
            "部分回答": 0.6,
            "不完整": 0.4,
            "未回答": 0.0
        },
        "image_reference": {
            "有明確圖片引用": 1.0,
            "有暗示圖片內容": 0.8,
            "有相關圖片": 0.6,
            "無圖片引用": 0.0
        },
        "clarity": {
            "結構清晰": 1.0,
            "基本清晰": 0.8,
            "一般": 0.6,
            "不清晰": 0.4,
            "混亂": 0.0
        }
    }
    
    # 圖片引用關鍵詞
    IMAGE_REFERENCE_KEYWORDS = [
        "圖片", "圖像", "圖面", "圖表", "圖示",
        "如圖", "見圖", "參考圖", "圖中",
        "https://", "http://",
        "相關圖片", "教材圖片", "示意圖",
        "截圖", "畫面", "頁面"
    ]
    
    # 技術術語列表
    TECHNICAL_TERMS = [
        "Wire", "Cable", "連接器", "線束", "規格", "測試", "設計",
        "材料", "絕緣", "導體", "屏蔽", "接地", "電阻", "電容",
        "電感", "阻抗", "頻率", "信號", "電流", "電壓", "功率",
        "溫度", "濕度", "振動", "衝擊", "彎曲", "扭轉", "拉伸",
        "壓縮", "老化", "腐蝕", "氧化", "絕緣電阻", "耐壓",
        "介電強度", "絕緣位移", "接觸電阻", "插拔力", "保持力"
    ]
    
    @classmethod
    def ensure_directories(cls):
        """確保必要的目錄存在"""
        cls.RESULTS_DIR.mkdir(exist_ok=True)
        
    @classmethod
    def validate_paths(cls):
        """驗證路徑是否存在"""
        if not cls.IMAGES_DIR.exists():
            raise FileNotFoundError(f"圖片目錄不存在: {cls.IMAGES_DIR}")
        if not cls.MAIN_PY_PATH.exists():
            raise FileNotFoundError(f"main.py不存在: {cls.MAIN_PY_PATH}")
    
    @classmethod
    def get_api_endpoint(cls, endpoint: str) -> str:
        """獲取API端點URL"""
        return f"{cls.get_api_base_url()}/{endpoint.lstrip('/')}"
