#!/usr/bin/env python3
"""
RAG 測試模組
一個完整的 RAG 系統測試框架，支援圖片測試、問題生成、答案評估和報告生成
"""

__version__ = "1.0.0"
__author__ = "RAG Test Module"
__description__ = "RAG 系統測試模組 - 支援互動式測試和自動化報告生成"

# 導入主要類別
from .core.rag_tester import RAGTester, RAGTestResult, CostInfo
from .utils.image_utils import ImageProcessor
from .utils.report_generator import ReportGenerator
from .config.test_config import RAGTestConfig
from .smart_tester import SmartRAGTester
from .interactive_smart_tester import InteractiveSmartTester

__all__ = [
    'RAGTester',
    'RAGTestResult',
    'CostInfo',
    'ImageProcessor',
    'ReportGenerator',
    'RAGTestConfig',
    'SmartRAGTester',
    'InteractiveSmartTester'
]
