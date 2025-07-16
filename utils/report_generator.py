#!/usr/bin/env python3
"""
測試報告生成器
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

# 添加配置路徑
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
config_dir = os.path.join(os.path.dirname(current_dir), 'config')
utils_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(config_dir)
sys.path.append(utils_dir)

from test_config import RAGTestConfig
from image_utils import ImageProcessor

class ReportGenerator:
    """測試報告生成器"""
    
    def __init__(self):
        self.config = RAGTestConfig
        self.image_processor = ImageProcessor()
    
    def save_json_report(self, results: List[Dict], timestamp: str) -> str:
        """保存 JSON 格式報告"""
        filename = Path(self.config.RESULTS_DIR) / f"rag_test_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON 報告已保存: {filename}")
            return str(filename)
            
        except Exception as e:
            print(f"❌ 保存 JSON 報告失敗: {e}")
            return ""
    
    def generate_html_report(self, results: List[Dict], timestamp: str) -> str:
        """生成 HTML 測試報告"""
        if not results:
            return self._generate_empty_report()
        
        # 計算統計數據
        stats = self._calculate_statistics(results)
        
        # 生成 HTML 內容
        html_content = self._generate_html_template(results, stats, timestamp)
        
        # 保存 HTML 報告
        filename = Path(self.config.RESULTS_DIR) / f"rag_test_report_{timestamp}.html"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ HTML 報告已保存: {filename}")
        except Exception as e:
            print(f"❌ 保存 HTML 報告失敗: {e}")

        # 返回 HTML 內容而不是文件名
        return html_content
    
    def _calculate_statistics(self, results: List[Dict]) -> Dict:
        """計算測試統計數據"""
        total_tests = len(results)
        successful_results = [r for r in results if r.get('success', True)]
        
        if not successful_results:
            return {
                'total_tests': total_tests,
                'success_rate': 0.0,
                'overall_avg': 0.0,
                'technical_avg': 0.0,
                'completeness_avg': 0.0,
                'clarity_avg': 0.0,
                'avg_response_time': 0.0,
                'image_ref_rate': 0.0,
                'total_cost': 0.0,
                'avg_cost_per_test': 0.0,
                'claude_question_cost': 0.0,
                'claude_evaluation_cost': 0.0,
                'openai_cost': 0.0,
                'category_stats': {}
            }
        
        # 基本統計
        overall_scores = [r['overall_score'] for r in successful_results]

        # 從 evaluation_scores 中提取分數，如果不存在則從頂層提取（向後兼容）
        technical_scores = []
        completeness_scores = []
        clarity_scores = []

        for r in successful_results:
            eval_scores = r.get('evaluation_scores', {})
            technical_scores.append(eval_scores.get('technical_accuracy', r.get('technical_accuracy', 0.0)))
            completeness_scores.append(eval_scores.get('completeness', r.get('completeness', 0.0)))
            clarity_scores.append(eval_scores.get('clarity', r.get('clarity', 0.0)))
        response_times = [r['response_time'] for r in successful_results]
        image_references = sum(1 for r in successful_results if r.get('has_image_reference', False))
        
        # 成本統計
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
        
        # 類別統計
        category_stats = defaultdict(list)
        for result in successful_results:
            category_stats[result['category']].append(result['overall_score'])
        
        return {
            'total_tests': total_tests,
            'success_rate': len(successful_results) / total_tests * 100,
            'overall_avg': sum(overall_scores) / len(overall_scores),
            'technical_avg': sum(technical_scores) / len(technical_scores),
            'completeness_avg': sum(completeness_scores) / len(completeness_scores),
            'clarity_avg': sum(clarity_scores) / len(clarity_scores),
            'avg_response_time': sum(response_times) / len(response_times),
            'image_ref_rate': image_references / len(successful_results) * 100,
            'total_cost': total_cost,
            'avg_cost_per_test': total_cost / len(successful_results),
            'claude_question_cost': total_claude_question_cost,
            'claude_evaluation_cost': total_claude_evaluation_cost,
            'openai_cost': total_openai_cost,
            'category_stats': dict(category_stats)
        }
    
    def _generate_empty_report(self) -> str:
        """生成空報告"""
        return """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>RAG測試報告</title>
        </head>
        <body>
            <h1>沒有測試結果</h1>
        </body>
        </html>
        """
    
    def _format_answer_with_images(self, answer: str) -> str:
        """將答案中的圖片URL轉換成HTML圖片標籤"""
        import re
        
        # 統一的圖片樣式
        img_style = f"""max-width: {self.config.HTML_TEMPLATE_STYLE['max_image_width']}; 
                        height: auto; margin: 5px; border: 1px solid #ddd; 
                        border-radius: 5px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
                        cursor: pointer; object-fit: contain; display: inline-block; 
                        vertical-align: top;"""
        
        # 檢查是否有📷相關圖片區塊
        if "📷 相關圖片：" in answer:
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
                    images_html = '<div style="display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; justify-content: flex-start; align-items: flex-start;">'
                    for number, url in urls:
                        images_html += f'<div style="text-align: center;"><small>{number.strip()}</small><br><img src="{url}" alt="相關圖片 {number.strip()}" style="{img_style}" onclick="openModal(this)"></div>'
                    images_html += '</div>'
                    
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
        
        for i, source in enumerate(sources[:5], 1):
            page_num = source.get('page_num', '未知')
            topic = source.get('topic', '未知主題')
            sub_topic = source.get('sub_topic', '未知子主題')
            content = source.get('content', '無內容')
            similarity_score = source.get('similarity_score', 0.0)
            content_type = source.get('content_type', '未知類型')
            
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

    def _generate_html_template(self, results: List[Dict], stats: Dict, timestamp: str) -> str:
        """生成完整的 HTML 模板"""
        # 基本樣式和腳本
        html_head = f"""
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
            border-bottom: 3px solid {self.config.HTML_TEMPLATE_STYLE['primary_color']};
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid {self.config.HTML_TEMPLATE_STYLE['primary_color']};
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
            border-left: 4px solid {self.config.HTML_TEMPLATE_STYLE['primary_color']};
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
        .test-result {{
            background-color: #fafafa;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin: 20px 0;
            padding: 20px;
        }}
        .test-header {{
            background-color: {self.config.HTML_TEMPLATE_STYLE['primary_color']};
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
        .score.high {{ color: {self.config.HTML_TEMPLATE_STYLE['success_color']}; }}
        .score.medium {{ color: {self.config.HTML_TEMPLATE_STYLE['warning_color']}; }}
        .score.low {{ color: {self.config.HTML_TEMPLATE_STYLE['error_color']}; }}
        .image-container {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            align-items: flex-start;
            flex-wrap: wrap;
        }}
        .test-image {{
            max-width: {self.config.HTML_TEMPLATE_STYLE['max_image_width']};
            max-height: {self.config.HTML_TEMPLATE_STYLE['max_image_height']};
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
            border-color: {self.config.HTML_TEMPLATE_STYLE['primary_color']};
            box-shadow: 0 6px 20px rgba(52, 152, 219, 0.3);
        }}
        .answer {{
            background-color: #f0f8f0;
            padding: 12px;
            border-left: 4px solid {self.config.HTML_TEMPLATE_STYLE['success_color']};
            margin: 10px 0;
            border-radius: 0 5px 5px 0;
            position: relative;
        }}
        .answer-content {{
            max-height: {self.config.HTML_TEMPLATE_STYLE['answer_max_height']};
            overflow: hidden;
            transition: max-height 0.3s ease;
            line-height: 1.6;
            word-wrap: break-word;
            padding-bottom: 40px;
        }}
        .answer-content.expanded {{
            max-height: none;
            padding-bottom: 40px;
        }}
        .answer-toggle {{
            position: absolute;
            bottom: 5px;
            right: 10px;
            background: {self.config.HTML_TEMPLATE_STYLE['success_color']};
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            z-index: 10;
        }}
        .collapsible-header {{
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 2px solid {self.config.HTML_TEMPLATE_STYLE['primary_color']};
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }}
        .collapsible-toggle {{
            font-size: 18px;
            font-weight: bold;
            color: {self.config.HTML_TEMPLATE_STYLE['primary_color']};
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

        /* 圖片模態框樣式 */
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
            border-radius: 8px;
        }}
        .close {{
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
            transition: color 0.3s;
        }}
        .close:hover,
        .close:focus {{
            color: #bbb;
            text-decoration: none;
        }}
    </style>
    <script>
        function toggleAnswer(button) {{
            const content = button.parentElement.querySelector('.answer-content');
            const isExpanded = content.classList.contains('expanded');

            if (isExpanded) {{
                content.classList.remove('expanded');
                button.textContent = '展開完整回答';
            }} else {{
                content.classList.add('expanded');
                button.textContent = '收起';
            }}
        }}

        function toggleCollapse(headerId, contentId) {{
            const header = document.getElementById(headerId);
            const content = document.getElementById(contentId);
            const toggle = header.querySelector('.collapsible-toggle');

            if (content.classList.contains('collapsed')) {{
                content.classList.remove('collapsed');
                toggle.classList.remove('collapsed');
                toggle.textContent = '▼';
            }} else {{
                content.classList.add('collapsed');
                toggle.classList.add('collapsed');
                toggle.textContent = '▶';
            }}
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            const answers = document.querySelectorAll('.answer');
            answers.forEach(answer => {{
                const content = answer.querySelector('.answer-content');
                if (content) {{
                    const button = document.createElement('button');
                    button.className = 'answer-toggle';
                    button.textContent = '展開完整回答';
                    button.onclick = () => toggleAnswer(button);

                    answer.style.position = 'relative';
                    answer.appendChild(button);
                }}
            }});
        }});
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 RAG系統測試報告</h1>
        """

        # 統計摘要部分
        html_summary = f"""
        <div class="summary">
            <h2>📊 測試總結</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="value">{stats['overall_avg']:.3f}</div>
                    <div class="label">總體平均得分</div>
                </div>
                <div class="summary-item">
                    <div class="value">{stats['technical_avg']:.3f}</div>
                    <div class="label">技術準確性平均</div>
                </div>
                <div class="summary-item">
                    <div class="value">{stats['completeness_avg']:.3f}</div>
                    <div class="label">完整性平均</div>
                </div>
                <div class="summary-item">
                    <div class="value">{stats['clarity_avg']:.3f}</div>
                    <div class="label">清晰度平均</div>
                </div>
                <div class="summary-item">
                    <div class="value">{stats['total_tests']}</div>
                    <div class="label">測試圖片數</div>
                </div>
                <div class="summary-item">
                    <div class="value">{stats['avg_response_time']:.2f}s</div>
                    <div class="label">平均響應時間</div>
                </div>
                <div class="summary-item">
                    <div class="value">{stats['image_ref_rate']:.1f}%</div>
                    <div class="label">圖片引用率</div>
                </div>
                <div class="summary-item">
                    <div class="value">{stats['success_rate']:.1f}%</div>
                    <div class="label">成功率</div>
                </div>
            </div>
        </div>
        """

        # 成本分析部分
        html_cost = f"""
        <div class="cost-summary">
            <div class="collapsible-header" id="cost-overview-header" onclick="toggleCollapse('cost-overview-header', 'cost-overview-content')">
                <h2 style="margin: 0;">💰 成本分析總覽</h2>
                <span class="collapsible-toggle">▼</span>
            </div>
            <div class="collapsible-content" id="cost-overview-content">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 20px; margin: 20px 0; color: white;">
                    <div style="text-align: center;">
                        <div style="font-size: 36px; font-weight: 700; margin-bottom: 10px;">${stats['total_cost']:.6f}</div>
                        <div style="font-size: 18px; margin-bottom: 15px;">總測試成本</div>
                        <div style="font-size: 14px; opacity: 0.8;">平均每次: ${stats['avg_cost_per_test']:.6f}</div>
                    </div>
                    <div style="display: flex; gap: 20px; margin-top: 20px; flex-wrap: wrap;">
                        <div style="flex: 1; background: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 8px; min-width: 200px;">
                            <div style="font-weight: 600; margin-bottom: 10px;">🤖 Claude 3.7 Sonnet</div>
                            <div>問題生成: ${stats['claude_question_cost']:.6f}</div>
                            <div>答案評估: ${stats['claude_evaluation_cost']:.6f}</div>
                            <div style="border-top: 1px solid rgba(255,255,255,0.3); margin-top: 8px; padding-top: 8px; font-weight: 600;">
                                小計: ${(stats['claude_question_cost'] + stats['claude_evaluation_cost']):.6f}
                            </div>
                        </div>
                        <div style="flex: 1; background: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 8px; min-width: 200px;">
                            <div style="font-weight: 600; margin-bottom: 10px;">🧠 OpenAI GPT-4o</div>
                            <div>RAG 回答生成: ${stats['openai_cost']:.6f}</div>
                            <div style="border-top: 1px solid rgba(255,255,255,0.3); margin-top: 8px; padding-top: 8px; font-weight: 600;">
                                小計: ${stats['openai_cost']:.6f}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """

        # 類別統計部分
        html_categories = "<h2>📂 類別統計</h2>"
        for category, scores in stats['category_stats'].items():
            if scores:
                avg_cat_score = sum(scores) / len(scores)
                score_class = "high" if avg_cat_score >= 0.8 else "medium" if avg_cat_score >= 0.6 else "low"

                html_categories += f"""
        <div style="background-color: #f8f9fa; padding: 10px 15px; margin: 5px 0; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;">
            <span>{category}</span>
            <div>
                <span class="score {score_class}">{avg_cat_score:.3f}</span>
                <span style="color: #7f8c8d; margin-left: 10px;">({len(scores)} 張成功)</span>
            </div>
        </div>"""

        # 詳細測試結果部分
        html_results = "<h2>🖼️ 詳細測試結果</h2>"

        for i, result in enumerate(results, 1):
            score_class = "high" if result['overall_score'] >= 0.8 else "medium" if result['overall_score'] >= 0.6 else "low"

            # 生成圖片 URL（使用 main.py 的圖片服務端點）
            image_url = ""
            image_display_html = ""
            if 'image_path' in result and result['image_path'] and os.path.exists(result['image_path']):
                from pathlib import Path
                from urllib.parse import quote

                image_name = Path(result['image_path']).name
                encoded_image_name = quote(image_name)

                # 使用配置中的 API URL 構建圖片 URL
                # 從 RAG API URL 中提取基礎 URL，移除端點路徑
                api_base_url = self.config.RAG_API_URL
                if '/query-with-memory' in api_base_url:
                    api_base_url = api_base_url.replace('/query-with-memory', '')
                elif '/chat' in api_base_url:
                    api_base_url = api_base_url.replace('/chat', '')

                image_url = f"{api_base_url}/images/{encoded_image_name}"

                print(f"🖼️ 生成圖片 URL: {image_url}")

                # 創建圖片顯示 HTML，包含錯誤處理
                image_display_html = f"""
                <img class='test-image' src='{image_url}' alt='{image_name}' onclick='openModal(this)'
                     onerror="console.error('圖片載入失敗:', this.src); this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; padding:20px; border:2px dashed #ccc; text-align:center; color:#666; border-radius:8px; max-width: 350px;">
                    <div style="font-size:16px; margin-bottom:5px;">📷 圖片載入失敗</div>
                    <small style="color:#999;">{image_name}</small><br>
                    <small style="color:#999; word-break: break-all;">URL: {image_url}</small><br>
                    <small style="color:#999;">請確保 main.py 服務器正在運行</small><br>
                    <button onclick="window.open('{image_url}', '_blank')" style="margin-top:10px; padding:5px 10px; background:#007bff; color:white; border:none; border-radius:3px; cursor:pointer;">
                        直接測試圖片URL
                    </button>
                </div>
                """
            else:
                # 檢查是否是 Excel 模式（category 包含 Excel_Row）
                category = result.get('category', '')
                if 'Excel_Row' not in category:
                    # 只有在非 Excel 模式且確實需要圖片時才顯示警告
                    print(f"⚠️ 圖片路徑不存在或為空: {result.get('image_path', 'None')}")

                # Excel 模式顯示不同的佔位符
                if 'Excel_Row' in category:
                    image_display_html = "<div style='width: 350px; height: 200px; background-color: #e8f4fd; display: flex; align-items: center; justify-content: center; border: 2px dashed #3498db; border-radius: 8px; color: #2980b9; font-weight: bold;'>📊 Excel 問題模式<br><small style='color: #7fb3d3;'>無需圖片</small></div>"
                else:
                    image_display_html = "<div style='width: 350px; height: 200px; background-color: #f0f0f0; display: flex; align-items: center; justify-content: center; border: 2px dashed #ccc; border-radius: 8px; color: #666;'>圖片路徑不存在</div>"

            # 格式化答案中的圖片
            formatted_answer = self._format_answer_with_images(result.get('rag_answer', ''))

            # 生成參考段落
            sources_html = self._generate_sources_section(result, i)

            # 獲取圖片名稱
            image_name = "未知圖片"
            if 'image_path' in result and result['image_path']:
                image_name = Path(result['image_path']).name
            elif 'image_name' in result:
                image_name = result['image_name']

            html_results += f"""
        <div class="test-result">
            <div class="test-header">
                <span>測試 {i}: {image_name}</span>
                <span class="score {score_class}">{result.get('overall_score', 0.0):.3f}</span>
            </div>

            <div class="image-container">
                {image_display_html}
                <div style="flex: 1; padding: 15px; background-color: #f8f9fa; border-radius: 8px; min-width: 300px;">
                    <div><strong>類別:</strong> {result.get('category', '未知')}</div>
                    <div><strong>技術準確性:</strong> {result.get('technical_accuracy', 0.0):.3f}</div>
                    <div><strong>完整性:</strong> {result.get('completeness', 0.0):.3f}</div>
                    <div><strong>清晰度:</strong> {result.get('clarity', 0.0):.3f}</div>
                    <div><strong>圖片引用:</strong> {'是' if result.get('has_image_reference', False) else '否'}</div>
                    <div><strong>響應時間:</strong> {result.get('response_time', 0.0):.2f}s</div>
                    <div><strong>成本:</strong> ${result.get('cost_info', {}).get('total_cost', 0.0):.6f}</div>
                </div>
            </div>

            <div style="background-color: #e8f4fd; padding: 12px; border-left: 4px solid {self.config.HTML_TEMPLATE_STYLE['primary_color']}; margin: 10px 0; border-radius: 0 5px 5px 0;">
                <strong>🤔 生成問題:</strong><br>
                {result.get('generated_question', '無問題')}
            </div>

            <div class="answer">
                <strong>🤖 RAG回答:</strong><br>
                <div class="answer-content">
                    {formatted_answer}
                </div>
            </div>

            {sources_html}
        </div>"""

        # 結尾部分
        html_footer = f"""
        <div style="text-align: center; color: #7f8c8d; font-size: 14px; margin-top: 30px; border-top: 1px solid #ecf0f1; padding-top: 15px;">
            報告生成時間: {timestamp}<br>
            RAG測試模組 v1.0
        </div>
    </div>

    <!-- 圖片模態框 -->
    <div id="imageModal" class="modal">
        <span class="close">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        // 圖片模態框功能
        function openModal(img) {{
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modal.style.display = 'block';
            modalImg.src = img.src;
        }}

        // 關閉模態框
        document.querySelector('.close').onclick = function() {{
            document.getElementById('imageModal').style.display = 'none';
        }}

        // 點擊模態框外部關閉
        window.onclick = function(event) {{
            const modal = document.getElementById('imageModal');
            if (event.target == modal) {{
                modal.style.display = 'none';
            }}
        }}

        // 收合功能
        function toggleCollapse(headerId, contentId) {{
            const header = document.getElementById(headerId);
            const content = document.getElementById(contentId);
            const toggle = header.querySelector('.collapsible-toggle') || header.querySelector('.section-toggle');

            if (content.classList.contains('collapsed')) {{
                content.classList.remove('collapsed');
                if (toggle) {{
                    toggle.classList.remove('collapsed');
                    toggle.textContent = '▼';
                }}
            }} else {{
                content.classList.add('collapsed');
                if (toggle) {{
                    toggle.classList.add('collapsed');
                    toggle.textContent = '▶';
                }}
            }}
        }}
    </script>
</body>
</html>"""

        return html_head + html_summary + html_cost + html_categories + html_results + html_footer
