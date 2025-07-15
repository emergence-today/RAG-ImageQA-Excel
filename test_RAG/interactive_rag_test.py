#!/usr/bin/env python3
"""
RAG 系統測試工具
支援選擇圖片類別和數量進行測試，生成詳細的HTML報告
使用方法: python3 interactive_rag_test.py
"""

import os
import sys
import json
import time
import random
import base64
from typing import Dict, List
from collections import defaultdict
from pathlib import Path

# 添加父目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)

from rag_test_system import RAGTestSystem, RAGTestResult

class InteractiveRAGTester:
    """互動式RAG測試器"""
    
    def __init__(self):
        self.rag_test = RAGTestSystem()

    def display_categories(self, categories: Dict[str, List[str]]):
        """顯示圖片類別"""
        print("\n📂 可用的圖片類別:")
        print("=" * 60)
        
        for i, (category, images) in enumerate(categories.items(), 1):
            print(f"{i:2d}. {category:<30} ({len(images)} 張圖片)")
        
        print("=" * 60)

    def get_user_selection(self, categories: Dict[str, List[str]]) -> Dict[str, int]:
        """獲取用戶選擇"""
        selection = {}
        category_list = list(categories.keys())
        
        print("\n🎯 請選擇要測試的類別和數量:")
        print("📝 注意: 每張圖片會生成1個問題，然後用RAG系統回答並評分")
        print("格式: 類別編號:數量 (例如: 1:3 表示第1個類別測試3張)")
        print("多個選擇用空格分隔 (例如: 1:3 2:2)")
        print("輸入 'all:N' 表示每個類別都測試N張")
        print("直接按 Enter 使用預設 (每個類別1張)")
        
        user_input = input("\n請輸入選擇: ").strip()
        
        if not user_input:
            # 預設每個類別1張
            for category in categories.keys():
                selection[category] = 1
            print("✅ 使用預設設定: 每個類別測試 1 張圖片")
        elif user_input.startswith('all:') or user_input.startswith('all '):
            # 所有類別相同數量
            try:
                if ':' in user_input:
                    count = int(user_input.split(':')[1])
                else:
                    count = int(user_input.split()[1])

                for category in categories.keys():
                    max_images = len(categories[category])
                    selection[category] = min(count, max_images)
                print(f"✅ 所有類別都測試 {count} 張圖片")
            except (ValueError, IndexError):
                print("❌ 格式錯誤，使用預設設定")
                for category in categories.keys():
                    selection[category] = 1
        else:
            # 解析用戶輸入
            try:
                for item in user_input.split():
                    if ':' in item:
                        idx_str, count_str = item.split(':')
                        idx = int(idx_str) - 1  # 轉換為0基索引
                        count = int(count_str)
                        
                        if 0 <= idx < len(category_list):
                            category = category_list[idx]
                            max_images = len(categories[category])
                            selection[category] = min(count, max_images)
                            print(f"✅ {category}: 測試 {selection[category]} 張圖片")
                        else:
                            print(f"❌ 類別編號 {idx + 1} 超出範圍")
            except ValueError:
                print("❌ 格式錯誤，使用預設設定")
                for category in categories.keys():
                    selection[category] = 1
        
        return selection

    def run_interactive_test(self, selection: Dict[str, int], categories: Dict[str, List[str]]):
        """執行互動式測試"""
        print("\n🚀 開始執行RAG互動式測試...")
        print("=" * 60)
        
        all_results = []
        total_images = sum(selection.values())
        current_image = 0
        
        for category, count in selection.items():
            if count == 0:
                continue
                
            print(f"\n📁 測試類別: {category}")
            print("-" * 40)
            
            # 隨機選擇圖片
            available_images = categories[category]
            selected_images = random.sample(available_images, min(count, len(available_images)))
            
            category_scores = []
            
            for image_path in selected_images:
                current_image += 1
                image_name = Path(image_path).name
                
                print(f"[{current_image}/{total_images}] 測試圖片: {image_name}")
                
                try:
                    # 執行RAG測試
                    result = self.rag_test.test_single_image(image_path)

                    if result.error_message:
                        print(f"  ❌ 測試失敗: {result.error_message}")
                        category_scores.append(0.0)
                    else:
                        score = result.overall_score
                        category_scores.append(score)
                        
                        print(f"  ✅ 總體得分: {score:.3f}")
                        print(f"     📝 生成問題: {result.generated_question[:60]}...")
                        print(f"     🎯 技術準確性: {result.technical_accuracy:.3f}")
                        print(f"     📋 完整性: {result.completeness:.3f}")
                        print(f"     🖼️ 圖片引用: {'是' if result.has_image_reference else '否'}")
                        print(f"     ⏱️ 響應時間: {result.response_time:.2f}s")
                    
                    # 轉換為字典格式以便保存
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
                        'success': result.error_message is None,
                        'error_message': result.error_message,
                        'cost_info': {
                            'claude_question_generation_cost': result.cost_info.claude_question_generation_cost if result.cost_info else 0.0,
                            'claude_evaluation_cost': result.cost_info.claude_evaluation_cost if result.cost_info else 0.0,
                            'openai_rag_cost': result.cost_info.openai_rag_cost if result.cost_info else 0.0,
                            'total_cost': result.cost_info.total_cost if result.cost_info else 0.0
                        },
                        'api_response': result.api_response  # 添加 api_response 字段
                    }

                    # 調試：檢查 api_response
                    print(f"🔍 調試 - api_response 存在: {result.api_response is not None}")
                    if result.api_response:
                        print(f"🔍 調試 - api_response 類型: {type(result.api_response)}")
                        print(f"🔍 調試 - api_response keys: {list(result.api_response.keys()) if isinstance(result.api_response, dict) else 'Not a dict'}")
                    all_results.append(result_dict)
                    
                except Exception as e:
                    print(f"  ❌ 測試出錯: {e}")
                    category_scores.append(0.0)
                
                # 避免API限制
                if current_image < total_images:
                    print("  ⏳ 等待2秒避免API限制...")
                    time.sleep(2)
            
            # 顯示類別統計
            if category_scores:
                avg_score = sum(category_scores) / len(category_scores)
                print(f"📊 {category} 平均得分: {avg_score:.3f}")
        
        # 顯示總結
        self.display_summary(all_results)
        
        # 保存結果
        self.save_results(all_results)
        
        return all_results

    def display_summary(self, results: List[Dict]):
        """顯示測試總結"""
        print("\n" + "=" * 60)
        print("📈 RAG測試結果總結")
        print("=" * 60)
        
        if not results:
            print("❌ 沒有測試結果")
            return
        
        # 按類別統計
        category_stats = defaultdict(list)
        for result in results:
            if result['success']:
                category_stats[result['category']].append(result['overall_score'])
        
        print("\n📂 類別統計:")
        for category, scores in category_stats.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"{category:<20} 平均: {avg_score:.3f} ({len(scores)} 張成功)")
        
        # 總體統計
        successful_results = [r for r in results if r['success']]
        if successful_results:
            overall_scores = [r['overall_score'] for r in successful_results]
            technical_scores = [r['technical_accuracy'] for r in successful_results]
            completeness_scores = [r['completeness'] for r in successful_results]
            clarity_scores = [r['clarity'] for r in successful_results]
            response_times = [r['response_time'] for r in successful_results]
            image_references = sum(1 for r in successful_results if r['has_image_reference'])
            
            print("\n📊 總體統計:")
            print(f"總體平均得分: {sum(overall_scores) / len(overall_scores):.3f}")
            print(f"技術準確性平均: {sum(technical_scores) / len(technical_scores):.3f}")
            print(f"完整性平均: {sum(completeness_scores) / len(completeness_scores):.3f}")
            print(f"清晰度平均: {sum(clarity_scores) / len(clarity_scores):.3f}")
            print(f"圖片引用率: {image_references / len(successful_results) * 100:.1f}%")
            print(f"平均響應時間: {sum(response_times) / len(response_times):.2f} 秒")
            print(f"成功率: {len(successful_results) / len(results) * 100:.1f}%")

    def save_results(self, results: List[Dict]):
        """保存測試結果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 確保結果目錄存在
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        json_filename = results_dir / f"rag_interactive_test_{timestamp}.json"
        html_filename = results_dir / f"rag_interactive_test_{timestamp}.html"

        try:
            # 保存 JSON 格式
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            # 生成 HTML 報告
            html_content = self.generate_html_report_with_images(results, timestamp)
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"\n📄 測試結果已保存:")
            print(f"   JSON: {json_filename}")
            print(f"   HTML: {html_filename}")
            print(f"🖼️ HTML 報告包含圖片展示功能")

        except Exception as e:
            print(f"❌ 保存結果失敗: {e}")

    def encode_image_to_base64(self, image_path: str) -> str:
        """將圖片編碼為 base64 用於 HTML 嵌入，如果圖片太大則壓縮"""
        try:
            from PIL import Image
            import io
            import os

            # 檢查文件是否存在
            if not os.path.exists(image_path):
                print(f"⚠️ 圖片文件不存在: {image_path}")
                return ""

            # 檢查文件大小
            file_size = os.path.getsize(image_path)
            print(f"🖼️ 處理圖片: {Path(image_path).name} (大小: {file_size} bytes)")

            # 打開圖片
            with Image.open(image_path) as img:
                print(f"🖼️ 原始圖片尺寸: {img.size}, 模式: {img.mode}")

                # 如果圖片太大，進行壓縮
                max_size = (600, 400)  # 降低最大尺寸以減少文件大小
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    print(f"🔄 壓縮圖片從 {img.size} 到最大 {max_size}")
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    print(f"✅ 壓縮後尺寸: {img.size}")

                # 轉換為RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    print(f"🔄 轉換圖片模式從 {img.mode} 到 RGB")
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    print(f"🔄 轉換圖片模式從 {img.mode} 到 RGB")
                    img = img.convert('RGB')

                # 保存到內存中，使用較低的品質以減少大小
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=60, optimize=True)
                buffer.seek(0)

                # 檢查壓縮後的大小
                compressed_size = len(buffer.getvalue())
                print(f"📦 壓縮後大小: {compressed_size} bytes")

                # 如果壓縮後仍然太大，進一步降低品質
                if compressed_size > 500 * 1024:  # 500KB
                    print("🔄 文件仍然太大，進一步壓縮...")
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=40, optimize=True)
                    buffer.seek(0)
                    compressed_size = len(buffer.getvalue())
                    print(f"📦 二次壓縮後大小: {compressed_size} bytes")

                # 編碼為base64
                encoded = base64.b64encode(buffer.read()).decode('utf-8')
                print(f"✅ Base64 編碼成功，長度: {len(encoded)} 字符")
                return f"data:image/jpeg;base64,{encoded}"

        except Exception as e:
            print(f"❌ PIL 處理失敗 {image_path}: {e}")
            # 如果PIL處理失敗，嘗試原始方法但限制文件大小
            try:
                import os
                file_size = os.path.getsize(image_path)
                if file_size > 500 * 1024:  # 降低到500KB限制
                    print(f"⚠️ 圖片文件太大 ({file_size} bytes)，跳過嵌入")
                    return ""

                print(f"🔄 嘗試備用方法處理圖片...")
                with open(image_path, "rb") as image_file:
                    encoded = base64.b64encode(image_file.read()).decode('utf-8')
                    ext = Path(image_path).suffix.lower()
                    mime_type = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif'
                    }.get(ext, 'image/png')
                    print(f"✅ 備用方法編碼成功")
                    return f"data:{mime_type};base64,{encoded}"
            except Exception as e2:
                print(f"❌ 備用方法也失敗 {image_path}: {e2}")
                return ""

    def _format_answer_with_images(self, answer: str) -> str:
        """將所有圖片URL轉換成橫向排列的小尺寸圖片顯示"""
        import re

        # 統一的圖片樣式 - 橫向排列
        img_style = 'max-width: 200px; height: auto; margin: 5px; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; object-fit: contain; display: inline-block; vertical-align: top;'

        # 檢查是否有📷相關圖片區塊，如果有，特殊處理使其橫向排列
        if "📷 相關圖片：" in answer:
            # 分割文字部分和圖片區塊
            parts = answer.split("📷 相關圖片：")
            if len(parts) == 2:
                text_part = parts[0]
                image_part = "📷 相關圖片：" + parts[1]

                # 處理文字部分的單獨URL
                remaining_url_pattern = r'(?<!src=")(?<!src=\')https?://[^\s<>"\']+\.(?:png|jpg|jpeg|gif|bmp)(?![^<]*>)'
                def replace_remaining_url_with_img(match):
                    url = match.group(0)
                    return f'<br><img src="{url}" alt="相關圖片" style="{img_style}" onclick="openModal(this)">'

                formatted_text = re.sub(remaining_url_pattern, replace_remaining_url_with_img, text_part)

                # 處理📷相關圖片區塊 - 創建橫向容器
                numbered_url_pattern = r'(\d+\.\s*)(https?://[^\s]+\.(?:png|jpg|jpeg|gif|bmp))'
                urls = re.findall(numbered_url_pattern, image_part)

                if urls:
                    # 創建橫向排列的圖片容器
                    images_html = '<div style="display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; justify-content: flex-start; align-items: flex-start;">'
                    for number, url in urls:
                        images_html += f'<div style="text-align: center;"><small>{number.strip()}</small><br><img src="{url}" alt="相關圖片 {number.strip()}" style="{img_style}" onclick="openModal(this)"></div>'
                    images_html += '</div>'

                    # 替換原來的編號URL
                    formatted_image_part = re.sub(numbered_url_pattern, '', image_part)
                    formatted_image_part = formatted_image_part.replace("📷 相關圖片：", f"📷 相關圖片：{images_html}")
                else:
                    formatted_image_part = image_part

                return formatted_text + formatted_image_part

        # 如果沒有📷相關圖片區塊，處理所有URL
        remaining_url_pattern = r'(?<!src=")(?<!src=\')https?://[^\s<>"\']+\.(?:png|jpg|jpeg|gif|bmp)(?![^<]*>)'
        def replace_remaining_url_with_img(match):
            url = match.group(0)
            return f'<br><img src="{url}" alt="相關圖片" style="{img_style}" onclick="openModal(this)">'

        result = re.sub(remaining_url_pattern, replace_remaining_url_with_img, answer)

        return result

    def _generate_sources_section(self, result: Dict, test_index: int = 0) -> str:
        """生成參考段落區塊的HTML"""
        api_response = result.get('api_response', {})
        if not api_response:
            return ""

        # sources 在 api_response 的根級別，不是在 raw_response 中
        sources = api_response.get('sources', [])

        if not sources:
            return ""

        html = f"""
            <div style="background-color: #fff8e1; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #ff9800;">
                <div class="section-header" id="sources-header-{test_index}" onclick="toggleCollapse('sources-header-{test_index}', 'sources-content-{test_index}')">
                    <strong>📚 參考段落:</strong>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="collapsible-content" id="sources-content-{test_index}">
                    <div style="margin-top: 10px;">"""

        for i, source in enumerate(sources[:5], 1):  # 最多顯示5個來源
            page_num = source.get('page_num', '未知')
            topic = source.get('topic', '未知主題')
            sub_topic = source.get('sub_topic', '未知子主題')
            content = source.get('content', '無內容')
            similarity_score = source.get('similarity_score', 0.0)
            content_type = source.get('content_type', '未知類型')

            # 截取內容，避免太長
            if len(content) > 150:
                content = content[:150] + "..."

            html += f"""
                    <div style="background-color: #f5f5f5; padding: 10px; margin: 8px 0; border-radius: 3px; border-left: 3px solid #ff9800;">
                        <div style="font-weight: bold; color: #e65100; margin-bottom: 5px;">
                            📄 來源 {i}: {topic} > {sub_topic} (第{page_num}頁)
                        </div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                            相似度: {similarity_score:.3f} | 類型: {content_type}
                        </div>
                        <div style="font-size: 13px; line-height: 1.4;">
                            {content}
                        </div>
                    </div>"""

        html += """
                    </div>
                </div>
            </div>"""

        return html

    async def run_single_test(self, image_path: str, question: str) -> Dict:
        """執行單個測試"""
        try:
            # 獲取圖片資訊
            image_name = Path(image_path).name
            category = Path(image_path).parent.name

            # 執行測試
            result = self.rag_test.test_single_image(image_path, question)

            # 將 RAGTestResult 對象轉換為字典
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
                'success': result.error_message is None,
                'error_message': result.error_message,
                'cost_info': {
                    'claude_question_generation_cost': result.cost_info.claude_question_generation_cost,
                    'claude_evaluation_cost': result.cost_info.claude_evaluation_cost,
                    'openai_rag_cost': result.cost_info.openai_rag_cost,
                    'total_cost': result.cost_info.total_cost
                },
            }

            # 處理 api_response，確保能被JSON序列化
            if result.api_response:
                try:
                    # 嘗試序列化 api_response 來檢查是否有問題
                    import json
                    json.dumps(result.api_response)
                    result_dict['api_response'] = result.api_response
                    print(f"✅ api_response 成功添加到結果中")
                except Exception as e:
                    print(f"⚠️ api_response 序列化失敗: {e}")
                    # 如果序列化失敗，嘗試提取關鍵信息
                    if isinstance(result.api_response, dict):
                        safe_api_response = {}
                        for key, value in result.api_response.items():
                            try:
                                json.dumps(value)
                                safe_api_response[key] = value
                            except:
                                safe_api_response[key] = str(value)
                        result_dict['api_response'] = safe_api_response
                    else:
                        result_dict['api_response'] = str(result.api_response)
            else:
                print(f"⚠️ api_response 為空或None")
                result_dict['api_response'] = None

            # 調試：檢查最終的 api_response
            print(f"🔍 最終 api_response: {result_dict.get('api_response', 'NOT_FOUND')}")

            # 添加額外資訊
            result_dict['image_name'] = image_name
            result_dict['category'] = category
            result_dict['question'] = question

            return result_dict

        except Exception as e:
            print(f"⚠️ 測試失敗 {image_path}: {e}")
            return {
                'image_name': Path(image_path).name,
                'category': Path(image_path).parent.name,
                'question': question,
                'rag_answer': f"測試失敗: {str(e)}",
                'technical_accuracy': 0.0,
                'completeness': 0.0,
                'clarity': 0.0,
                'image_reference': 0.0,
                'overall_score': 0.0,
                'cost_info': {'total_cost': 0.0}
            }

    async def run_question_only_test(self, question: str) -> Dict:
        """執行純問題測試（無圖片）- 直接調用 RAG 系統"""
        try:
            import time
            import sys
            import os

            # 記錄開始時間
            start_time = time.time()

            # 直接導入並使用 RAG 系統（避免 HTTP 循環調用）
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from src.core.langchain_rag_system import LangChainParentChildRAG
            from config.config import Config

            # 初始化 RAG 系統
            collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'JH-圖紙認識-langchain')
            rag_system = LangChainParentChildRAG(collection_name)

            # 直接查詢 RAG 系統
            session_id = f"test_session_{int(time.time())}"

            # 構建查詢請求
            query_request = {
                "user_query": question,
                "streaming": False,
                "sessionId": session_id
            }

            # 執行查詢
            rag_result = rag_system.generate_answer(
                query=question,
                top_k=3
            )

            if rag_result and "answer" in rag_result:
                rag_answer = rag_result["answer"]

                # 計算處理時間
                processing_time = time.time() - start_time

                # 使用 Claude 評估回答品質（無圖片版本）
                evaluation = self.rag_test.evaluate_answer_quality_no_image(question, rag_answer)

                # 計算成本
                cost_info = self.rag_test.calculate_test_cost(
                    question_tokens=len(question.split()) * 1.3,  # 估算 token 數
                    answer_tokens=len(rag_answer.split()) * 1.3,
                    evaluation_tokens=200  # 評估用的 token 數
                )

                return {
                    'image_name': 'no_image',
                    'category': 'question_only',
                    'question': question,
                    'rag_answer': rag_answer,
                    'technical_accuracy': evaluation.get('technical_accuracy', 0.0),
                    'completeness': evaluation.get('completeness', 0.0),
                    'clarity': evaluation.get('clarity', 0.0),
                    'image_reference': 0.0,  # 無圖片模式固定為 0
                    'overall_score': evaluation.get('overall_score', 0.0),
                    'cost_info': cost_info,
                    'processing_time': processing_time
                }
            else:
                raise Exception("RAG 系統沒有返回有效回答")

        except Exception as e:
            print(f"⚠️ 純問題測試失敗: {e}")
            return {
                'image_name': 'no_image',
                'category': 'question_only',
                'question': question,
                'rag_answer': f"測試失敗: {str(e)}",
                'technical_accuracy': 0.0,
                'completeness': 0.0,
                'clarity': 0.0,
                'image_reference': 0.0,
                'overall_score': 0.0,
                'cost_info': {'total_cost': 0.0},
                'processing_time': 0.0
            }

    def generate_html_report_with_images(self, results: List[Dict], timestamp: str) -> str:
        """生成包含圖片的 HTML 測試報告"""

        # 計算統計數據
        total_tests = len(results)
        if total_tests == 0:
            return "<html><body><h1>沒有測試結果</h1></body></html>"

        successful_results = [r for r in results if r['success']]
        if successful_results:
            overall_scores = [r['overall_score'] for r in successful_results]
            technical_scores = [r['technical_accuracy'] for r in successful_results]
            completeness_scores = [r['completeness'] for r in successful_results]
            clarity_scores = [r['clarity'] for r in successful_results]
            response_times = [r['response_time'] for r in successful_results]
            image_references = sum(1 for r in successful_results if r['has_image_reference'])

            overall_avg = sum(overall_scores) / len(overall_scores)
            technical_avg = sum(technical_scores) / len(technical_scores)
            completeness_avg = sum(completeness_scores) / len(completeness_scores)
            clarity_avg = sum(clarity_scores) / len(clarity_scores)
            avg_response_time = sum(response_times) / len(response_times)
            image_ref_rate = image_references / len(successful_results) * 100
            success_rate = len(successful_results) / total_tests * 100

            # 計算成本統計
            total_claude_question_cost = 0.0
            total_claude_evaluation_cost = 0.0
            total_openai_cost = 0.0
            total_cost = 0.0

            for r in successful_results:
                if 'cost_info' in r and r['cost_info']:
                    cost_info = r['cost_info']
                    total_claude_question_cost += cost_info.get('claude_question_generation_cost', 0.0)
                    total_claude_evaluation_cost += cost_info.get('claude_evaluation_cost', 0.0)
                    total_openai_cost += cost_info.get('openai_rag_cost', 0.0)
                    total_cost += cost_info.get('total_cost', 0.0)

            avg_cost_per_test = total_cost / len(successful_results) if successful_results else 0.0
        else:
            overall_avg = technical_avg = completeness_avg = clarity_avg = 0.0
            avg_response_time = 0.0
            image_ref_rate = success_rate = 0.0
            total_claude_question_cost = total_claude_evaluation_cost = total_openai_cost = total_cost = avg_cost_per_test = 0.0

        # 按類別統計
        category_stats = defaultdict(list)
        for result in successful_results:
            category_stats[result['category']].append(result['overall_score'])

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG系統測試報告 - {timestamp}</title>
    <style>
        body {{
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
        }}
        .summary {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .summary-item {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        .summary-item .value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .summary-item .label {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        .category-item {{
            background-color: #f8f9fa;
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .test-result {{
            background-color: #fafafa;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin: 20px 0;
            padding: 20px;
        }}
        .test-header {{
            background-color: #3498db;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .score {{
            font-size: 18px;
            font-weight: bold;
        }}
        .score.high {{ color: #27ae60; }}
        .score.medium {{ color: #f39c12; }}
        .score.low {{ color: #e74c3c; }}
        .image-container {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            align-items: flex-start;
            flex-wrap: wrap;
        }}
        .test-image {{
            max-width: 350px;
            max-height: 300px;
            width: auto;
            height: auto;
            border: 3px solid #2c3e50;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            object-fit: contain;
        }}
        .test-image:hover {{
            transform: scale(1.05);
            border-color: #3498db;
            box-shadow: 0 6px 20px rgba(52, 152, 219, 0.3);
        }}
        .image-info {{
            flex: 1;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            min-width: 300px;
        }}
        .question {{
            background-color: #e8f4fd;
            padding: 12px;
            border-left: 4px solid #3498db;
            margin: 10px 0;
            border-radius: 0 5px 5px 0;
        }}
        .answer {{
            background-color: #f0f8f0;
            padding: 12px;
            border-left: 4px solid #27ae60;
            margin: 10px 0;
            border-radius: 0 5px 5px 0;
            position: relative;
        }}
        .answer-content {{
            max-height: 200px;
            overflow: hidden;
            transition: max-height 0.3s ease;
            line-height: 1.6;
            word-wrap: break-word;
            padding-bottom: 40px; /* 為按鈕留出空間 */
        }}
        .answer-content.expanded {{
            max-height: none;
            padding-bottom: 40px; /* 展開時也保持底部空間 */
        }}
        .answer-toggle {{
            position: absolute;
            bottom: 5px;
            right: 10px;
            background: #27ae60;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            z-index: 10;
        }}
        .answer-toggle:hover {{
            background: #219a52;
        }}
        .answer-fade {{
            position: absolute;
            bottom: 30px;
            left: 0;
            right: 0;
            height: 30px;
            background: linear-gradient(transparent, #f0f8f0);
            pointer-events: none;
        }}
        .answer-content.expanded + .answer-fade {{
            display: none;
        }}
        .evaluation {{
            background-color: #fff3cd;
            padding: 12px;
            border-left: 4px solid #ffc107;
            margin: 10px 0;
            border-radius: 0 5px 5px 0;
        }}
        .progress-bar {{
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            height: 20px;
            margin: 5px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #e74c3c 0%, #f39c12 50%, #27ae60 100%);
            transition: width 0.3s ease;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }}
        .modal-content {{
            margin: auto;
            display: block;
            width: 80%;
            max-width: 700px;
            max-height: 80%;
            margin-top: 5%;
        }}
        .close {{
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }}
        .timestamp {{
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 30px;
            border-top: 1px solid #ecf0f1;
            padding-top: 15px;
        }}

        /* 成本分析樣式 */
        .cost-breakdown {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            color: white;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        }}

        .cost-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .cost-icon {{
            font-size: 24px;
            margin-right: 10px;
        }}

        .cost-title {{
            font-size: 18px;
            font-weight: 600;
            flex: 1;
        }}

        .cost-total {{
            font-size: 24px;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 16px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }}

        .cost-details {{
            display: grid;
            gap: 12px;
        }}

        .cost-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255, 255, 255, 0.1);
            padding: 12px 16px;
            border-radius: 8px;
            backdrop-filter: blur(5px);
            transition: all 0.3s ease;
        }}

        .cost-item:hover {{
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }}

        .cost-label {{
            display: flex;
            align-items: center;
            font-weight: 500;
        }}

        .cost-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 10px;
        }}

        .claude-dot {{
            background: #ff6b6b;
        }}

        .openai-dot {{
            background: #4ecdc4;
        }}

        .cost-value {{
            font-family: 'Courier New', monospace;
            font-weight: 600;
            font-size: 16px;
        }}

        /* 成本總覽樣式 */
        .cost-summary {{
            margin: 30px 0;
        }}

        .cost-overview {{
            display: flex;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}

        .cost-total-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 30px;
            color: white;
            text-align: center;
            min-width: 250px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }}

        .cost-total-amount {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 10px;
            font-family: 'Courier New', monospace;
        }}

        .cost-total-label {{
            font-size: 18px;
            font-weight: 500;
            margin-bottom: 15px;
            opacity: 0.9;
        }}

        .cost-per-test {{
            font-size: 14px;
            opacity: 0.8;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
        }}

        .cost-breakdown-cards {{
            display: flex;
            gap: 20px;
            flex: 1;
            flex-wrap: wrap;
        }}

        /* 收合功能樣式 */
        .collapsible-header {{
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 2px solid #3498db;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }}

        .collapsible-header:hover {{
            background-color: rgba(52, 152, 219, 0.1);
            padding-left: 10px;
            padding-right: 10px;
            border-radius: 5px;
        }}

        .collapsible-toggle {{
            font-size: 18px;
            font-weight: bold;
            color: #3498db;
            transition: transform 0.3s ease;
        }}

        .collapsible-toggle.collapsed {{
            transform: rotate(-90deg);
        }}

        .collapsible-content {{
            overflow: hidden;
            transition: max-height 0.3s ease;
        }}

        .collapsible-content.collapsed {{
            max-height: 0;
            margin: 0;
            padding: 0;
        }}

        .section-header {{
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 8px;
            margin-bottom: 10px;
            transition: all 0.3s ease;
            border-left: 4px solid #3498db;
        }}

        .section-header:hover {{
            background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
            transform: translateX(5px);
        }}

        .section-toggle {{
            font-size: 16px;
            color: #3498db;
            transition: transform 0.3s ease;
        }}

        .section-toggle.collapsed {{
            transform: rotate(-90deg);
        }}

        .cost-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            flex: 1;
            min-width: 280px;
            border-top: 4px solid;
        }}

        .claude-card {{
            border-top-color: #ff6b6b;
        }}

        .openai-card {{
            border-top-color: #4ecdc4;
        }}

        .cost-card-header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #f0f0f0;
        }}

        .cost-card-icon {{
            font-size: 24px;
            margin-right: 12px;
        }}

        .cost-card-title {{
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
        }}

        .cost-card-body {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .cost-card-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
        }}

        .cost-card-total {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0 10px 0;
            border-top: 2px solid #f0f0f0;
            font-weight: 600;
            color: #2c3e50;
        }}

        .cost-card-desc {{
            color: #7f8c8d;
            font-size: 14px;
        }}

        .cost-card-total .cost-card-desc {{
            color: #2c3e50;
            font-size: 16px;
        }}

        .cost-card-value {{
            font-family: 'Courier New', monospace;
            font-weight: 600;
            color: #2c3e50;
        }}

        .cost-card-total .cost-card-value {{
            font-size: 18px;
            color: #e74c3c;
        }}
    </style>
    <script>
        function toggleAnswer(button) {{
            const content = button.parentElement.querySelector('.answer-content');
            const fade = button.parentElement.querySelector('.answer-fade');
            const isExpanded = content.classList.contains('expanded');

            if (isExpanded) {{
                content.classList.remove('expanded');
                button.textContent = '展開完整回答';
                if (fade) fade.style.display = 'block';
            }} else {{
                content.classList.add('expanded');
                button.textContent = '收起';
                if (fade) fade.style.display = 'none';
            }}
        }}

        // 初始化所有答案區塊
        document.addEventListener('DOMContentLoaded', function() {{
            const answers = document.querySelectorAll('.answer');
            answers.forEach(answer => {{
                const content = answer.querySelector('.answer-content');
                if (content) {{
                    // 總是創建展開按鈕，不管內容長度如何
                    const button = document.createElement('button');
                    button.className = 'answer-toggle';
                    button.textContent = '展開完整回答';
                    button.onclick = () => toggleAnswer(button);

                    // 創建漸變遮罩
                    const fade = document.createElement('div');
                    fade.className = 'answer-fade';

                    answer.style.position = 'relative';
                    answer.appendChild(fade);
                    answer.appendChild(button);
                }}
            }});
        }});
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 RAG系統測試報告</h1>

        <div class="summary">
            <h2>📊 測試總結</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="value">{overall_avg:.3f}</div>
                    <div class="label">總體平均得分</div>
                </div>
                <div class="summary-item">
                    <div class="value">{technical_avg:.3f}</div>
                    <div class="label">技術準確性平均</div>
                </div>
                <div class="summary-item">
                    <div class="value">{completeness_avg:.3f}</div>
                    <div class="label">完整性平均</div>
                </div>
                <div class="summary-item">
                    <div class="value">{clarity_avg:.3f}</div>
                    <div class="label">清晰度平均</div>
                </div>
                <div class="summary-item">
                    <div class="value">{total_tests}</div>
                    <div class="label">測試圖片數</div>
                </div>
                <div class="summary-item">
                    <div class="value">{avg_response_time:.2f}s</div>
                    <div class="label">平均響應時間</div>
                </div>
                <div class="summary-item">
                    <div class="value">{image_ref_rate:.1f}%</div>
                    <div class="label">圖片引用率</div>
                </div>
                <div class="summary-item">
                    <div class="value">{success_rate:.1f}%</div>
                    <div class="label">成功率</div>
                </div>
            </div>
        </div>

        <div class="cost-summary">
            <div class="collapsible-header" id="cost-overview-header" onclick="toggleCollapse('cost-overview-header', 'cost-overview-content')">
                <h2 style="margin: 0;">💰 成本分析總覽</h2>
                <span class="collapsible-toggle">▼</span>
            </div>
            <div class="collapsible-content" id="cost-overview-content">
                <div class="cost-overview">
                <div class="cost-total-card">
                    <div class="cost-total-amount">${total_cost:.6f}</div>
                    <div class="cost-total-label">總測試成本</div>
                    <div class="cost-per-test">平均每次: ${avg_cost_per_test:.6f}</div>
                </div>
                <div class="cost-breakdown-cards">
                    <div class="cost-card claude-card">
                        <div class="cost-card-header">
                            <span class="cost-card-icon">🤖</span>
                            <span class="cost-card-title">Claude 3.7 Sonnet</span>
                        </div>
                        <div class="cost-card-body">
                            <div class="cost-card-item">
                                <span class="cost-card-desc">問題生成</span>
                                <span class="cost-card-value">${total_claude_question_cost:.6f}</span>
                            </div>
                            <div class="cost-card-item">
                                <span class="cost-card-desc">答案評估</span>
                                <span class="cost-card-value">${total_claude_evaluation_cost:.6f}</span>
                            </div>
                            <div class="cost-card-total">
                                <span class="cost-card-desc">小計</span>
                                <span class="cost-card-value">${(total_claude_question_cost + total_claude_evaluation_cost):.6f}</span>
                            </div>
                        </div>
                    </div>
                    <div class="cost-card openai-card">
                        <div class="cost-card-header">
                            <span class="cost-card-icon">🧠</span>
                            <span class="cost-card-title">OpenAI GPT-4o</span>
                        </div>
                        <div class="cost-card-body">
                            <div class="cost-card-item">
                                <span class="cost-card-desc">RAG 回答生成</span>
                                <span class="cost-card-value">${total_openai_cost:.6f}</span>
                            </div>
                            <div class="cost-card-total">
                                <span class="cost-card-desc">小計</span>
                                <span class="cost-card-value">${total_openai_cost:.6f}</span>
                            </div>
                        </div>
                    </div>
                </div>
                </div>
            </div>
        </div>

        <h2>📂 類別統計</h2>"""

        # 添加類別統計
        for category, scores in category_stats.items():
            if scores:
                avg_cat_score = sum(scores) / len(scores)
                score_class = "high" if avg_cat_score >= 0.8 else "medium" if avg_cat_score >= 0.6 else "low"

                html_content += f"""
        <div class="category-item">
            <span>{category}</span>
            <div>
                <span class="score {score_class}">{avg_cat_score:.3f}</span>
                <span style="color: #7f8c8d; margin-left: 10px;">({len(scores)} 張成功)</span>
            </div>
        </div>"""

        html_content += """
        <h2>🖼️ 詳細測試結果</h2>"""

        # 添加每個測試的詳細結果
        for i, result in enumerate(results, 1):
            score_class = "high" if result['overall_score'] >= 0.8 else "medium" if result['overall_score'] >= 0.6 else "low"

            # 使用圖片URL而不是base64編碼
            image_name = Path(result['image_path']).name
            # 生成圖片URL - 使用localhost API，需要URL編碼中文檔名
            from urllib.parse import quote
            encoded_image_name = quote(image_name)
            image_url = f"http://localhost:8006/api/v1/JH/images/{encoded_image_name}"

            html_content += f"""
        <div class="test-result">
            <div class="test-header">
                <div>
                    <strong>測試 #{i}: {result['category']}</strong>
                </div>
                <div>
                    <span class="score {score_class}">得分: {result['overall_score']:.3f}</span>
                    <span style="margin-left: 15px;">⏱️ {result['response_time']:.2f}s</span>
                </div>
            </div>

            <div class="progress-bar">
                <div class="progress-fill" style="width: {result['overall_score']*100}%"></div>
            </div>

            <div class="image-container">
                <img src="{image_url}" alt="{image_name}" class="test-image" onclick="openModal(this)"
                     onerror="console.error('圖片載入失敗:', this.src); this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; padding:20px; border:2px dashed #ccc; text-align:center; color:#666; border-radius:8px;">
                    <div style="font-size:16px; margin-bottom:5px;">📷 圖片載入失敗</div>
                    <small style="color:#999;">{image_name}</small><br>
                    <small style="color:#999;">URL: {image_url}</small><br>
                    <small style="color:#999;">請確保 main.py 服務器正在運行</small><br>
                    <button onclick="window.open('{image_url}', '_blank')" style="margin-top:10px; padding:5px 10px; background:#007bff; color:white; border:none; border-radius:3px; cursor:pointer;">
                        直接測試圖片URL
                    </button>
                </div>
                <div class="image-info">
                    <strong>檔案:</strong> {image_name}<br>
                    <strong>類別:</strong> {result['category']}<br>
                    <strong>技術準確性:</strong> {result['technical_accuracy']:.3f}<br>
                    <strong>完整性:</strong> {result['completeness']:.3f}<br>
                    <strong>清晰度:</strong> {result['clarity']:.3f}<br>
                    <strong>圖片引用:</strong> {'是' if result['has_image_reference'] else '否'}<br>
                    <strong>💰 測試成本:</strong> ${result.get('cost_info', {}).get('total_cost', 0.0):.6f}
                </div>
            </div>

            <div style="background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                <strong>🔄 測試流程:</strong> Claude 生成問題 → main.py RAG回答 → Claude 評估
            </div>

            <div class="question">
                <strong>🔍 生成問題:</strong> {result['generated_question']}
            </div>

            <div class="answer">
                <strong>💬 RAG回答:</strong>
                <div class="answer-content">
                    {self._format_answer_with_images(result['rag_answer'])}
                </div>
            </div>

            <div class="evaluation">
                <strong>⭐ Claude評估:</strong><br>
                技術準確性: {result['technical_accuracy']:.3f} |
                完整性: {result['completeness']:.3f} |
                圖片引用: {result.get('evaluation_scores', {}).get('image_reference', 0):.3f} |
                清晰度: {result['clarity']:.3f}
            </div>

            <div class="cost-breakdown">
                <div class="section-header" id="cost-header-{i}" onclick="toggleCollapse('cost-header-{i}', 'cost-content-{i}')">
                    <div style="display: flex; align-items: center;">
                        <i class="cost-icon">💰</i>
                        <span class="cost-title">成本分析</span>
                        <div class="cost-total" style="margin-left: 15px;">${result.get('cost_info', {}).get('total_cost', 0.0):.6f}</div>
                    </div>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="collapsible-content" id="cost-content-{i}">
                    <div class="cost-details">
                    <div class="cost-item claude-question">
                        <div class="cost-label">
                            <span class="cost-dot claude-dot"></span>
                            Claude 問題生成
                        </div>
                        <div class="cost-value">${result.get('cost_info', {}).get('claude_question_generation_cost', 0.0):.6f}</div>
                    </div>
                    <div class="cost-item claude-eval">
                        <div class="cost-label">
                            <span class="cost-dot claude-dot"></span>
                            Claude 評估
                        </div>
                        <div class="cost-value">${result.get('cost_info', {}).get('claude_evaluation_cost', 0.0):.6f}</div>
                    </div>
                    <div class="cost-item openai-rag">
                        <div class="cost-label">
                            <span class="cost-dot openai-dot"></span>
                            OpenAI RAG
                        </div>
                        <div class="cost-value">${result.get('cost_info', {}).get('openai_rag_cost', 0.0):.6f}</div>
                    </div>
                    </div>
                </div>
            </div>

            {self._generate_sources_section(result, i)}
        </div>"""

        # 添加頁腳和 JavaScript
        html_content += f"""
        <div class="timestamp">
            📅 報告生成時間: {time.strftime('%Y-%m-%d %H:%M:%S')}
            <br>
            🤖 RAG系統測試框架 v1.0 - 基於 Claude Bedrock 視覺模型
        </div>
    </div>

    <!-- 圖片放大模態框 -->
    <div id="imageModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        function openModal(img) {{
            var modal = document.getElementById("imageModal");
            var modalImg = document.getElementById("modalImage");
            modal.style.display = "block";
            modalImg.src = img.src;
        }}

        function closeModal() {{
            document.getElementById("imageModal").style.display = "none";
        }}

        // 點擊模態框外部關閉
        window.onclick = function(event) {{
            var modal = document.getElementById("imageModal");
            if (event.target == modal) {{
                modal.style.display = "none";
            }}
        }}

        // ESC 鍵關閉模態框
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                closeModal();
            }}
        }});

        // 收合功能
        function toggleCollapse(headerId, contentId) {{
            var header = document.getElementById(headerId);
            var content = document.getElementById(contentId);
            var toggle = header.querySelector('.collapsible-toggle, .section-toggle');

            if (content.classList.contains('collapsed')) {{
                content.classList.remove('collapsed');
                content.style.maxHeight = content.scrollHeight + "px";
                toggle.classList.remove('collapsed');
            }} else {{
                content.classList.add('collapsed');
                content.style.maxHeight = "0";
                toggle.classList.add('collapsed');
            }}
        }}

        // 頁面載入後初始化收合狀態
        document.addEventListener('DOMContentLoaded', function() {{
            // 預設收合成本分析總覽和參考段落
            var defaultCollapsed = ['cost-overview-content'];
            defaultCollapsed.forEach(function(contentId) {{
                var content = document.getElementById(contentId);
                var headerId = contentId.replace('-content', '-header');
                var header = document.getElementById(headerId);
                if (content && header) {{
                    var toggle = header.querySelector('.collapsible-toggle, .section-toggle');
                    content.classList.add('collapsed');
                    content.style.maxHeight = "0";
                    if (toggle) toggle.classList.add('collapsed');
                }}
            }});

            // 為每個測試結果的參考段落添加收合功能
            var sourceSections = document.querySelectorAll('[id^="sources-content-"]');
            sourceSections.forEach(function(content) {{
                var headerId = content.id.replace('content', 'header');
                var header = document.getElementById(headerId);
                if (header) {{
                    var toggle = header.querySelector('.section-toggle');
                    content.classList.add('collapsed');
                    content.style.maxHeight = "0";
                    if (toggle) toggle.classList.add('collapsed');
                }}
            }});

            // 為每個測試結果的成本分析添加收合功能
            var costSections = document.querySelectorAll('[id^="cost-content-"]');
            costSections.forEach(function(content) {{
                var headerId = content.id.replace('content', 'header');
                var header = document.getElementById(headerId);
                if (header) {{
                    var toggle = header.querySelector('.section-toggle');
                    content.classList.add('collapsed');
                    content.style.maxHeight = "0";
                    if (toggle) toggle.classList.add('collapsed');
                }}
            }});
        }});
    </script>
</body>
</html>"""

        return html_content

def main():
    """主函數"""
    print("🤖 RAG系統互動式測試工具")
    print("📝 流程: 圖片 → Claude生成問題 → main.py RAG回答 → Claude評分")
    print("=" * 60)
    
    try:
        tester = InteractiveRAGTester()
        
        # 獲取圖片分類
        categories = tester.rag_test.get_image_categories()
        if not categories:
            print("❌ 沒有找到圖片檔案")
            return
        
        # 顯示類別
        tester.display_categories(categories)
        
        # 獲取用戶選擇
        selection = tester.get_user_selection(categories)
        
        if not any(selection.values()):
            print("❌ 沒有選擇任何圖片進行測試")
            return
        
        # 檢查main.py服務器
        print("\n🔍 檢查main.py服務器狀態...")
        if not tester.rag_test.start_main_py_server():
            print("❌ 無法啟動或連接到main.py服務器")
            print("💡 請手動啟動main.py服務器: python main.py")
            return
        
        # 執行測試
        tester.run_interactive_test(selection, categories)
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
