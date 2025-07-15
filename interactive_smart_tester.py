#!/usr/bin/env python3
"""
互動式智能 RAG 測試器
"""

import os
import sys
from pathlib import Path

# 添加路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'config'))

from config.test_config import RAGTestConfig
from smart_tester import SmartRAGTester

class InteractiveSmartTester:
    """互動式智能測試器"""
    
    def __init__(self):
        """初始化"""
        self.smart_tester = SmartRAGTester()
    
    def display_welcome(self):
        """顯示歡迎訊息"""
        print("=" * 60)
        print("🧠 智能 RAG 測試系統 v2.0")
        print("=" * 60)
        print("✨ 支援兩種輸入模式:")
        print("   📁 資料夾模式: 自動找圖片生成問題並測試")
        print("   📊 Excel 模式: 直接回應問題並評分")
        print("=" * 60)
    
    def get_user_input(self):
        """獲取用戶輸入"""
        while True:
            path = input("\n📝 請輸入路徑 (資料夾或 Excel 文件): ").strip()

            if not path:
                print("❌ 路徑不能為空")
                continue

            # 檢查退出指令
            if path.lower() in ['exit', 'quit', '退出', 'q']:
                print("👋 再見！")
                return None, None

            # 展開用戶目錄
            path = os.path.expanduser(path)

            if not os.path.exists(path):
                print(f"❌ 路徑不存在: {path}")
                continue

            # 自動檢測輸入類型
            return "3", path
    
    def get_folder_options(self, folder_path):
        """獲取資料夾模式的選項"""
        print("\n📁 資料夾模式設定:")

        # 先獲取所有可用的類別
        categories = self.smart_tester.image_processor.get_image_categories(folder_path)

        if not categories:
            print("❌ 資料夾中沒有找到圖片")
            return None

        print(f"\n📂 找到 {len(categories)} 個類別:")
        category_list = list(categories.keys())
        for i, (category, images) in enumerate(categories.items(), 1):
            print(f"   {i}. {category}: {len(images)} 張圖片")

        # 讓用戶選擇要測試的類別
        print(f"\n🎯 請選擇要測試的類別:")
        print("   輸入選項:")
        print("   - 'all' 或 '全部': 測試所有類別")
        print("   - 數字 (如 '1,3,5'): 測試指定類別")
        print("   - 範圍 (如 '1-3'): 測試範圍內的類別")

        while True:
            selection = input(f"請選擇類別 (預設: all): ").strip()
            if not selection:
                selection = "all"

            try:
                selected_categories = self._parse_category_selection(selection, category_list)
                if selected_categories:
                    break
                else:
                    print("❌ 無效的選擇，請重新輸入")
            except Exception as e:
                print(f"❌ 選擇格式錯誤: {e}")

        print(f"\n✅ 已選擇 {len(selected_categories)} 個類別:")
        for category in selected_categories:
            print(f"   - {category}: {len(categories[category])} 張圖片")

        # 設定每個類別的圖片數量
        while True:
            try:
                max_images = input(f"\n每個類別最多測試幾張圖片? (預設: 5): ").strip()
                if not max_images:
                    max_images = 5
                else:
                    max_images = int(max_images)

                if max_images <= 0:
                    print("❌ 數量必須大於 0")
                    continue

                break
            except ValueError:
                print("❌ 請輸入有效數字")

        return {
            "max_images_per_category": max_images,
            "selected_categories": selected_categories
        }

    def _parse_category_selection(self, selection, category_list):
        """解析類別選擇"""
        if selection.lower() in ['all', '全部', 'a']:
            return category_list

        selected_indices = set()

        # 處理逗號分隔的選擇
        parts = [part.strip() for part in selection.split(',')]

        for part in parts:
            if '-' in part:
                # 處理範圍選擇 (如 1-3)
                try:
                    start, end = map(int, part.split('-'))
                    if start < 1 or end > len(category_list) or start > end:
                        raise ValueError(f"範圍 {part} 無效")
                    selected_indices.update(range(start-1, end))
                except ValueError as e:
                    raise ValueError(f"範圍格式錯誤 '{part}': {e}")
            else:
                # 處理單個數字
                try:
                    index = int(part) - 1
                    if index < 0 or index >= len(category_list):
                        raise ValueError(f"類別編號 {part} 超出範圍 (1-{len(category_list)})")
                    selected_indices.add(index)
                except ValueError as e:
                    raise ValueError(f"數字格式錯誤 '{part}': {e}")

        return [category_list[i] for i in sorted(selected_indices)]
    
    def get_excel_options(self):
        """獲取 Excel 模式的選項"""
        print("\n📊 Excel 模式設定:")
        print("💡 Excel 文件應包含以下列:")
        print("   - 'question' 或 '問題': 問題內容")
        print("   - 'image_path' 或 '圖片路徑' (可選): 相關圖片路徑")
        
        confirm = input("\n確認 Excel 格式正確? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("❌ 請先確保 Excel 格式正確")
            return None
        
        return {}
    
    def run(self):
        """運行互動式測試"""
        try:
            self.display_welcome()
            
            while True:
                choice, path = self.get_user_input()

                if choice is None:  # 用戶選擇退出
                    break

                # 自動檢測輸入類型
                input_type = self.smart_tester.detect_input_type(path)
                print(f"\n🔍 檢測結果: {input_type}")

                if input_type == "folder":
                    print("📁 檢測為資料夾，使用資料夾模式")
                    options = self.get_folder_options(path)
                    if options is None:
                        continue
                    print(f"\n🚀 開始處理資料夾: {path}")

                elif input_type == "excel":
                    print("📊 檢測為 Excel 文件，使用 Excel 模式")
                    options = self.get_excel_options()
                    if options is None:
                        continue
                    print(f"\n🚀 開始處理 Excel: {path}")

                else:
                    print(f"❌ 不支援的輸入類型: {input_type}")
                    print("💡 支援的格式：")
                    print("   📁 資料夾：包含圖片的資料夾")
                    print("   📊 Excel：.xlsx 或 .xls 文件")
                    continue
                
                # 執行測試
                try:
                    report_path = self.smart_tester.run_smart_test(path, **options)
                    
                    if report_path:
                        print(f"\n🎉 測試完成！")
                        print(f"📄 報告路徑: {report_path}")
                        
                        # 詢問是否繼續
                        continue_test = input("\n是否繼續測試其他輸入? (y/N): ").strip().lower()
                        if continue_test not in ['y', 'yes', '是']:
                            break
                    else:
                        print("\n❌ 測試失敗，請檢查輸入")
                        
                except Exception as e:
                    print(f"\n❌ 測試過程中發生錯誤: {e}")
                    continue
                
        except KeyboardInterrupt:
            print("\n\n⚠️ 用戶中斷測試")
        except Exception as e:
            print(f"\n❌ 系統錯誤: {e}")

def main():
    """主函數"""
    try:
        tester = InteractiveSmartTester()
        tester.run()
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        print("請檢查配置文件和依賴項")

if __name__ == "__main__":
    main()
