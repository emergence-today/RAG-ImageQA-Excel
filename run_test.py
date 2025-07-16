#!/usr/bin/env python3
"""
RAG 測試模組啟動腳本
使用方法: python3 run_test.py
"""

import os
import sys

# 確保在正確的目錄中運行
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

# 添加必要的路徑
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'config'))
sys.path.insert(0, os.path.join(current_dir, 'core'))
sys.path.insert(0, os.path.join(current_dir, 'utils'))

def main():
    """主函數"""
    print("=" * 60)
    print("🧠 智能 RAG 測試系統 v2.0")
    print("=" * 60)
    print("✨ 自動識別輸入類型:")
    print("   📁 資料夾 → 找圖片生成問題並測試")
    print("   📊 Excel → 直接回應問題並評分")
    print("=" * 60)

    try:
        from interactive_smart_tester import InteractiveSmartTester
        tester = InteractiveSmartTester()
        tester.run()

    except KeyboardInterrupt:
        print("\n\n⚠️ 用戶中斷測試")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        print("請檢查 .env 配置文件中的設定")
        print("\n💡 提示:")
        print("1. 確認 CLAUDE_API_KEY 已正確設定")
        print("2. 確認 RAG_TEST_IMAGE_DIR 路徑存在")
        print("3. 確認 RAG_TEST_API_URL 可以訪問")
        print("4. 如果使用 Excel 模式，請確保安裝了 pandas: uv add pandas openpyxl")

if __name__ == "__main__":
    main()
