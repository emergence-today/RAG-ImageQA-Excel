#!/usr/bin/env python3
"""
智能 RAG 測試器 - 自動識別輸入類型（資料夾或 Excel）
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'config'))
sys.path.append(os.path.join(current_dir, 'core'))
sys.path.append(os.path.join(current_dir, 'utils'))

from config.test_config import RAGTestConfig
from core.rag_tester import RAGTester
from utils.image_utils import ImageProcessor
from utils.report_generator import ReportGenerator

class SmartRAGTester:
    """智能 RAG 測試器 - 支援資料夾和 Excel 輸入"""
    
    def __init__(self):
        """初始化智能測試器"""
        print("🚀 初始化智能 RAG 測試器...")
        
        # 驗證配置
        if not RAGTestConfig.validate_config():
            raise ValueError("配置驗證失敗")
        
        # 初始化組件
        self.rag_tester = RAGTester()
        self.image_processor = ImageProcessor()
        self.report_generator = ReportGenerator()
        
        print("✅ 智能 RAG 測試器初始化完成")
    
    def detect_input_type(self, input_path: str) -> str:
        """檢測輸入類型"""
        if not os.path.exists(input_path):
            return "not_found"
        
        if os.path.isdir(input_path):
            return "folder"
        
        if os.path.isfile(input_path):
            file_ext = Path(input_path).suffix.lower()
            if file_ext in ['.xlsx', '.xls']:
                return "excel"
            else:
                return "unknown_file"
        
        return "unknown"
    
    def process_folder_input(self, folder_path: str, max_images_per_category: int = 5, selected_categories: List[str] = None) -> List[Dict[str, Any]]:
        """處理資料夾輸入 - 找圖片生成問題並測試"""
        print(f"📁 處理資料夾: {folder_path}")

        # 獲取圖片分類
        categories = self.image_processor.get_image_categories(folder_path)

        if not categories:
            print("❌ 資料夾中沒有找到圖片")
            return []

        # 如果有指定類別，只處理選定的類別
        if selected_categories:
            filtered_categories = {}
            for category in selected_categories:
                if category in categories:
                    filtered_categories[category] = categories[category]
                else:
                    print(f"⚠️ 警告: 找不到類別 '{category}'")
            categories = filtered_categories

            if not categories:
                print("❌ 沒有找到任何選定的類別")
                return []

        print(f"📂 將測試 {len(categories)} 個類別:")
        for category, images in categories.items():
            print(f"   - {category}: {len(images)} 張圖片")

        # 執行測試
        results = []
        total_images = sum(min(len(images), max_images_per_category) for images in categories.values())
        current_image = 0

        for category, images in categories.items():
            print(f"\n📁 測試類別: {category}")
            print("-" * 40)
            
            # 限制每個類別的圖片數量
            test_images = images[:max_images_per_category]
            
            for i, image_path in enumerate(test_images, 1):
                current_image += 1
                image_name = Path(image_path).name
                
                print(f"[{current_image}/{total_images}] 測試圖片: {image_name}")
                
                try:
                    # 測試單張圖片（會自動生成問題）
                    result = self.rag_tester.test_single_image(image_path)

                    # 將 RAGTestResult 轉換為字典，但保持 cost_info 為物件
                    result_dict = {
                        'image_path': result.image_path,
                        'category': result.category,
                        'generated_question': result.generated_question,
                        'rag_answer': result.rag_answer,
                        'evaluation_scores': result.evaluation_scores,
                        'overall_score': result.overall_score,
                        'response_time': result.response_time,
                        'has_image_reference': result.has_image_reference,
                        'technical_accuracy': result.technical_accuracy,
                        'completeness': result.completeness,
                        'clarity': result.clarity,
                        'cost_info': result.cost_info,  # 保持為 CostInfo 物件
                        'api_response': result.api_response,
                        'error_message': result.error_message,
                        'success': result.error_message is None
                    }
                    results.append(result_dict)
                    
                    # 顯示結果摘要
                    print(f"  ✅ 總體得分: {result.overall_score:.3f}")
                    print(f"     🎯 技術準確性: {result.evaluation_scores.get('technical_accuracy', 0.0):.3f}")
                    print(f"     📋 完整性: {result.evaluation_scores.get('completeness', 0.0):.3f}")
                    print(f"     🖼️ 圖片引用: {'是' if result.has_image_reference else '否'}")
                    print(f"     ⏱️ 響應時間: {result.response_time:.2f}s")
                    print(f"     💰 成本: ${result.cost_info.total_cost:.6f}")
                    
                except Exception as e:
                    print(f"  ❌ 測試失敗: {e}")
                    continue
                
                # 測試間隔
                if current_image < total_images:
                    time.sleep(RAGTestConfig.DELAY_BETWEEN_TESTS)
        
        return results
    
    def process_excel_input(self, excel_path: str) -> List[Dict[str, Any]]:
        """處理 Excel 輸入 - 直接回應問題並評分"""
        print(f"📊 處理 Excel 文件: {excel_path}")
        
        try:
            import pandas as pd
        except ImportError:
            print("❌ 需要安裝 pandas 來處理 Excel 文件")
            print("請執行: uv add pandas openpyxl")
            return []
        
        try:
            # 讀取 Excel 文件
            df = pd.read_excel(excel_path)
            print(f"📋 Excel 文件包含 {len(df)} 行數據")
            
            # 檢查必要的列
            required_columns = ['question', 'image_path']  # 可以根據需要調整
            available_columns = df.columns.tolist()
            
            print(f"📊 可用列: {available_columns}")
            
            # 嘗試自動識別問題列
            question_col = None
            for col in ['question', 'questions', '問題', 'query', 'user_query']:
                if col in df.columns:
                    question_col = col
                    break
            
            if not question_col:
                print("❌ 無法找到問題列，請確保 Excel 中有 'question' 或 '問題' 列")
                return []
            
            # 嘗試自動識別圖片路徑列（可選）
            image_col = None
            for col in ['image_path', 'image', '圖片路徑', 'image_file']:
                if col in df.columns:
                    image_col = col
                    break
            
            results = []
            
            for index, row in df.iterrows():
                question = str(row[question_col]).strip()
                if not question or question == 'nan':
                    continue
                
                image_path = None
                if image_col and pd.notna(row[image_col]):
                    image_path = str(row[image_col]).strip()
                
                print(f"\n[{index + 1}/{len(df)}] 處理問題: {question[:50]}...")
                
                try:
                    # 直接查詢 RAG 系統
                    rag_response = self.rag_tester.rag_client.query_rag(question)
                    
                    if not rag_response:
                        print("  ❌ RAG 查詢失敗")
                        continue
                    
                    answer = rag_response.get('reply', '')
                    
                    # 評估答案品質
                    evaluation = self.rag_tester.claude_client.evaluate_answer_quality(
                        question, answer, image_path
                    )
                    
                    # 計算成本
                    from core.rag_tester import CostCalculator, CostInfo

                    # 評估成本（Claude）
                    evaluation_cost = CostCalculator.calculate_claude_cost(
                        f"評估問題: {question}\n回答: {answer}", str(evaluation)
                    )

                    # RAG 查詢成本（OpenAI）
                    rag_cost = CostCalculator.calculate_openai_cost(question, answer)

                    # 創建成本資訊
                    cost_info = CostInfo(
                        claude_question_generation_cost=0.0,  # Excel 模式不生成問題
                        claude_evaluation_cost=evaluation_cost,
                        openai_rag_cost=rag_cost
                    )
                    cost_info.calculate_total()
                    
                    # 創建結果
                    result = {
                        'image_path': image_path or '',
                        'category': f'Excel_Row_{index + 1}',
                        'generated_question': question,
                        'rag_answer': answer,
                        'evaluation_scores': evaluation,
                        'overall_score': evaluation.get('overall_score', 0.0),
                        'response_time': 0.0,  # Excel 模式不計算響應時間
                        'has_image_reference': '📷' in answer or 'http' in answer,
                        'success': True,
                        'error_message': None,
                        'cost_info': cost_info,
                        'api_response': rag_response
                    }
                    
                    results.append(result)
                    
                    # 顯示結果摘要
                    print(f"  ✅ 總體得分: {result['overall_score']:.3f}")
                    print(f"     🎯 技術準確性: {evaluation.get('technical_accuracy', 0.0):.3f}")
                    print(f"     📋 完整性: {evaluation.get('completeness', 0.0):.3f}")
                    print(f"     🖼️ 圖片引用: {'是' if result['has_image_reference'] else '否'}")
                    print(f"     💰 成本: ${cost_info.total_cost:.6f}")
                    
                except Exception as e:
                    print(f"  ❌ 處理失敗: {e}")
                    continue
                
                # 測試間隔
                time.sleep(RAGTestConfig.DELAY_BETWEEN_TESTS)
            
            return results
            
        except Exception as e:
            print(f"❌ 讀取 Excel 文件失敗: {e}")
            return []
    
    def run_smart_test(self, input_path: str, **kwargs) -> str:
        """執行智能測試"""
        print("=" * 60)
        print("🧠 智能 RAG 測試系統")
        print("=" * 60)
        
        # 檢測輸入類型
        input_type = self.detect_input_type(input_path)
        
        print(f"🔍 輸入路徑: {input_path}")
        print(f"📋 檢測類型: {input_type}")
        
        if input_type == "not_found":
            print("❌ 輸入路徑不存在")
            return None
        elif input_type == "unknown":
            print("❌ 無法識別的輸入類型")
            return None
        
        # 根據類型執行相應處理
        results = []
        
        if input_type == "folder":
            max_images = kwargs.get('max_images_per_category', 5)
            selected_categories = kwargs.get('selected_categories', None)
            results = self.process_folder_input(input_path, max_images, selected_categories)
        elif input_type == "excel":
            results = self.process_excel_input(input_path)
        else:
            print(f"❌ 不支援的輸入類型: {input_type}")
            return None
        
        if not results:
            print("❌ 沒有生成任何測試結果")
            return None
        
        # 生成報告
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # 生成 HTML 報告
        html_report = self.report_generator.generate_html_report(results, timestamp)
        
        # 保存報告
        os.makedirs(RAGTestConfig.RESULTS_DIR, exist_ok=True)
        
        html_filename = f"{RAGTestConfig.RESULTS_DIR}/smart_test_report_{timestamp}.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        # 顯示統計結果
        self._display_summary(results, input_type)
        
        print(f"\n📄 測試報告已保存: {html_filename}")
        print("🖼️ HTML 報告包含圖片展示功能")
        
        return html_filename
    
    def _display_summary(self, results: List[Dict], input_type: str):
        """顯示測試結果摘要"""
        if not results:
            return
        
        print("\n" + "=" * 60)
        print("📈 智能測試結果總結")
        print("=" * 60)
        
        # 計算統計數據
        total_tests = len(results)
        successful_tests = len([r for r in results if r.get('success', False)])
        
        scores = [r.get('overall_score', 0.0) for r in results if r.get('success', False)]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        technical_scores = [r.get('evaluation_scores', {}).get('technical_accuracy', 0.0) for r in results]
        avg_technical = sum(technical_scores) / len(technical_scores) if technical_scores else 0.0
        
        completeness_scores = [r.get('evaluation_scores', {}).get('completeness', 0.0) for r in results]
        avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
        
        image_references = len([r for r in results if r.get('has_image_reference', False)])
        
        total_cost = sum(getattr(r.get('cost_info'), 'total_cost', 0.0) if r.get('cost_info') else 0.0 for r in results)
        
        print(f"📊 輸入類型: {input_type.upper()}")
        print(f"📊 總體統計:")
        print(f"   總測試數: {total_tests}")
        print(f"   成功測試: {successful_tests}")
        print(f"   成功率: {(successful_tests/total_tests)*100:.1f}%")
        print(f"   總體平均得分: {avg_score:.3f}")
        print(f"   技術準確性平均: {avg_technical:.3f}")
        print(f"   完整性平均: {avg_completeness:.3f}")
        print(f"   圖片引用率: {(image_references/total_tests)*100:.1f}%")
        print(f"   總測試成本: ${total_cost:.6f}")
        print(f"   平均每次成本: ${total_cost/total_tests:.6f}")

def main():
    """主函數 - 命令行介面"""
    if len(sys.argv) < 2:
        print("使用方法: python3 smart_tester.py <資料夾路徑或Excel文件路徑> [選項]")
        print("範例:")
        print("  python3 smart_tester.py /path/to/images/folder")
        print("  python3 smart_tester.py /path/to/questions.xlsx")
        return
    
    input_path = sys.argv[1]
    
    try:
        tester = SmartRAGTester()
        tester.run_smart_test(input_path)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用戶中斷測試")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

if __name__ == "__main__":
    main()
