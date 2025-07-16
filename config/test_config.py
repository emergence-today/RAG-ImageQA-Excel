#!/usr/bin/env python3
"""
RAG 測試模組配置
從 .env 檔案載入所有配置參數
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 載入環境變數 - 從模組內的 .env 檔案
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class RAGTestConfig:
    """RAG 測試配置類"""
    
    # ===========================================
    # API 設定
    # ===========================================
    RAG_API_URL = os.getenv('RAG_TEST_API_URL', 'http://localhost:8006/api/v1/query')
    API_TIMEOUT = int(os.getenv('RAG_TEST_TIMEOUT', '30'))
    RETRY_COUNT = int(os.getenv('RAG_TEST_RETRY_COUNT', '3'))
    
    # ===========================================
    # Claude API 設定
    # ===========================================
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')
    CLAUDE_MAX_TOKENS = int(os.getenv('CLAUDE_MAX_TOKENS', '4000'))
    CLAUDE_TEMPERATURE = float(os.getenv('CLAUDE_TEMPERATURE', '0.7'))
    
    # AWS Bedrock 設定 (作為 Claude 的備選)
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    BEDROCK_MODEL = os.getenv('BEDROCK_MODEL', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')
    
    # ===========================================
    # 測試參數
    # ===========================================
    IMAGE_DIR = os.getenv('RAG_TEST_IMAGE_DIR', '/home/chun/heph-dev/JH/outputs/images/zerox_output')
    RESULTS_DIR = os.getenv('RAG_TEST_RESULTS_DIR', './RAG_test_module/results')
    DELAY_BETWEEN_TESTS = int(os.getenv('RAG_TEST_DELAY_BETWEEN_TESTS', '2'))
    
    # ===========================================
    # 成本計算設定
    # ===========================================
    # Claude 3.7 Sonnet 定價 (USD per token)
    # 官方定價 $0.003 / 1000 字符 → 約 0.000012 USD / token
    # 官方定價 $0.015 / 1000 字符 → 約 0.00006 USD / token
    CLAUDE_INPUT_COST_PER_TOKEN = float(os.getenv('CLAUDE_3_7_SONNET_INPUT_COST_PER_TOKEN', '0.000012'))
    CLAUDE_OUTPUT_COST_PER_TOKEN = float(os.getenv('CLAUDE_3_7_SONNET_OUTPUT_COST_PER_TOKEN', '0.00006'))

    # OpenAI GPT-4o 定價 (USD per token)
    OPENAI_INPUT_COST_PER_TOKEN = float(os.getenv('OPENAI_INPUT_COST_PER_TOKEN', '0.0000025'))
    OPENAI_OUTPUT_COST_PER_TOKEN = float(os.getenv('OPENAI_OUTPUT_COST_PER_TOKEN', '0.00001'))
    
    # ===========================================
    # 測試評估標準
    # ===========================================
    EVALUATION_CRITERIA = {
        'technical_accuracy': {
            'weight': 0.4,
            'description': '技術準確性 - 回答是否技術正確'
        },
        'completeness': {
            'weight': 0.3,
            'description': '完整性 - 回答是否完整回應問題'
        },
        'clarity': {
            'weight': 0.2,
            'description': '清晰度 - 回答是否清楚易懂'
        },
        'image_reference': {
            'weight': 0.1,
            'description': '圖片引用 - 是否正確引用相關圖片'
        }
    }
    
    # ===========================================
    # HTML 報告設定
    # ===========================================
    HTML_TEMPLATE_STYLE = {
        'max_image_width': os.getenv('HTML_MAX_IMAGE_WIDTH', '350px'),
        'max_image_height': os.getenv('HTML_MAX_IMAGE_HEIGHT', '300px'),
        'answer_max_height': os.getenv('HTML_ANSWER_MAX_HEIGHT', '200px'),
        'primary_color': os.getenv('HTML_PRIMARY_COLOR', '#3498db'),
        'success_color': os.getenv('HTML_SUCCESS_COLOR', '#27ae60'),
        'warning_color': os.getenv('HTML_WARNING_COLOR', '#f39c12'),
        'error_color': os.getenv('HTML_ERROR_COLOR', '#e74c3c')
    }
    
    @classmethod
    def validate_config(cls) -> bool:
        """驗證配置是否完整"""
        # 必要配置
        required_fields = [
            'RAG_API_URL',
            'IMAGE_DIR'
        ]

        # 可選配置（用於特定功能）
        optional_fields = {
            'AWS_ACCESS_KEY_ID': '問題生成和評估功能 (AWS Bedrock)',
            'AWS_SECRET_ACCESS_KEY': '問題生成和評估功能 (AWS Bedrock)'
        }

        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ 缺少必要配置: {', '.join(missing_fields)}")
            return False

        # 檢查可選配置並給出提示
        missing_optional = []
        for field, description in optional_fields.items():
            if not getattr(cls, field):
                missing_optional.append(f"{field} ({description})")

        if missing_optional:
            print(f"⚠️  缺少可選配置: {', '.join(missing_optional)}")
            print("   某些功能可能無法使用，但基本測試仍可進行")
        
        # 檢查目錄是否存在
        if not os.path.exists(cls.IMAGE_DIR):
            print(f"❌ 圖片目錄不存在: {cls.IMAGE_DIR}")
            return False
        
        # 確保結果目錄存在
        os.makedirs(cls.RESULTS_DIR, exist_ok=True)
        
        print("✅ 配置驗證通過")
        return True
    
    @classmethod
    def print_config(cls):
        """打印當前配置"""
        print("\n" + "=" * 60)
        print("📋 RAG 測試模組配置")
        print("=" * 60)
        print(f"RAG API URL: {cls.RAG_API_URL}")
        print(f"Claude 模型: {cls.CLAUDE_MODEL}")
        print(f"圖片目錄: {cls.IMAGE_DIR}")
        print(f"結果目錄: {cls.RESULTS_DIR}")
        print(f"API 超時: {cls.API_TIMEOUT}秒")
        print(f"重試次數: {cls.RETRY_COUNT}")
        print(f"測試間隔: {cls.DELAY_BETWEEN_TESTS}秒")
        print("=" * 60)
