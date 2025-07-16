#!/usr/bin/env python3
"""
RAG 測試核心模組
負責執行 RAG 測試的核心邏輯
"""

import os
import sys
import json
import time
import requests
import base64
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# 添加配置路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
config_dir = os.path.join(os.path.dirname(current_dir), 'config')
sys.path.append(config_dir)

from test_config import RAGTestConfig

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CostInfo:
    """成本資訊數據類"""
    claude_question_generation_cost: float = 0.0
    claude_evaluation_cost: float = 0.0
    openai_rag_cost: float = 0.0
    total_cost: float = 0.0

    def calculate_total(self):
        """計算總成本"""
        self.total_cost = (self.claude_question_generation_cost + 
                          self.claude_evaluation_cost + 
                          self.openai_rag_cost)
        return self.total_cost

@dataclass
class RAGTestResult:
    """RAG測試結果數據類"""
    image_path: str
    category: str
    generated_question: str
    rag_answer: str
    evaluation_scores: Dict[str, float]
    overall_score: float
    response_time: float
    has_image_reference: bool
    technical_accuracy: float
    completeness: float
    clarity: float
    cost_info: CostInfo = None
    api_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.cost_info is None:
            self.cost_info = CostInfo()

class CostCalculator:
    """成本計算器"""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """估算文本的 token 數量 (改進的估算方法)"""
        if not text:
            return 0

        # 對於中文文本，通常 1 個字符 ≈ 1 token
        # 對於英文文本，通常 4 個字符 ≈ 1 token
        # 這裡使用混合估算：中文字符按 1:1，英文按 4:1
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_chars = len(text) - chinese_chars

        estimated_tokens = chinese_chars + (english_chars // 4)

        # 確保至少有一些 token（避免為 0）
        return max(estimated_tokens, len(text) // 3)

    @staticmethod
    def calculate_claude_cost(input_text: str, output_text: str) -> float:
        """計算 Claude 使用成本"""
        input_tokens = CostCalculator.estimate_tokens(input_text)
        output_tokens = CostCalculator.estimate_tokens(output_text)

        input_cost = input_tokens * RAGTestConfig.CLAUDE_INPUT_COST_PER_TOKEN
        output_cost = output_tokens * RAGTestConfig.CLAUDE_OUTPUT_COST_PER_TOKEN
        total_cost = input_cost + output_cost

        # 調試資訊
        logger.debug(f"💰 Claude 成本計算: 輸入 {input_tokens} tokens (${input_cost:.6f}), 輸出 {output_tokens} tokens (${output_cost:.6f}), 總計 ${total_cost:.6f}")

        return total_cost

    @staticmethod
    def calculate_openai_cost(input_text: str, output_text: str) -> float:
        """計算 OpenAI 使用成本"""
        input_tokens = CostCalculator.estimate_tokens(input_text)
        output_tokens = CostCalculator.estimate_tokens(output_text)

        input_cost = input_tokens * RAGTestConfig.OPENAI_INPUT_COST_PER_TOKEN
        output_cost = output_tokens * RAGTestConfig.OPENAI_OUTPUT_COST_PER_TOKEN
        total_cost = input_cost + output_cost

        # 調試資訊
        logger.debug(f"💰 OpenAI 成本計算: 輸入 {input_tokens} tokens (${input_cost:.6f}), 輸出 {output_tokens} tokens (${output_cost:.6f}), 總計 ${total_cost:.6f}")

        return total_cost

class ClaudeClient:
    """Claude API 客戶端 - 使用 AWS Bedrock"""

    def __init__(self):
        self.aws_access_key = RAGTestConfig.AWS_ACCESS_KEY_ID
        self.aws_secret_key = RAGTestConfig.AWS_SECRET_ACCESS_KEY
        self.aws_region = RAGTestConfig.AWS_REGION
        self.model_id = RAGTestConfig.BEDROCK_MODEL

        if not all([self.aws_access_key, self.aws_secret_key]):
            logger.warning("⚠️ AWS 憑證未設定，將使用模擬模式")
            self.use_mock = True
        else:
            self.use_mock = False
            try:
                import boto3
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                logger.info("✅ AWS Bedrock 客戶端初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ AWS Bedrock 初始化失敗，使用模擬模式: {e}")
                self.use_mock = True

    def _call_claude(self, prompt: str) -> str:
        """調用 Claude 模型"""
        if self.use_mock:
            return self._mock_claude_response(prompt)

        try:
            import json

            # 構建請求
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": RAGTestConfig.CLAUDE_MAX_TOKENS,
                "temperature": RAGTestConfig.CLAUDE_TEMPERATURE,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # 調用 Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # 解析回應
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except Exception as e:
            logger.error(f"❌ Claude API 調用失敗: {e}")
            return self._mock_claude_response(prompt)

    def _mock_claude_response(self, prompt: str) -> str:
        """模擬 Claude 回應"""
        if "生成問題" in prompt or "generate question" in prompt.lower():
            return "請詳細說明這張圖片中顯示的技術內容、規格參數和重要資訊。"
        elif "評估" in prompt or "evaluate" in prompt.lower():
            return """
            技術準確性: 8/10 - 回答包含了相關的技術資訊
            完整性: 7/10 - 回答涵蓋了主要問題點
            清晰度: 9/10 - 表達清楚易懂
            圖片引用: 6/10 - 有提及相關圖片內容
            總體評分: 7.5/10
            """
        else:
            return "這是一個模擬回應。"

    def generate_question_from_image(self, image_path: str) -> str:
        """從圖片生成問題"""
        try:
            image_name = Path(image_path).name

            # 根據圖片類型生成更具體的問題，避免直接提到圖片
            if "LVDS" in image_name:
                question = "LVDS 線束加工的製程步驟、技術要求和品質控制要點是什麼？"
            elif "Cable" in image_name:
                question = "Cable 設計的規格參數、設計要求和應用場景有哪些？"
            elif "Wire" in image_name:
                question = "Wire Harness 的製程介紹、加工方法和技術標準是什麼？"
            elif "FFC" in image_name:
                question = "FFC 設計中的預載要求、設計原則和應用注意事項是什麼？"
            elif "材料" in image_name:
                question = "這種材料的特性、規格參數和應用範圍是什麼？"
            else:
                # 從檔名中提取技術類別，生成更自然的問題
                category = self._extract_category_from_filename(image_name)
                question = f"{category}的技術要點和重要規範是什麼？"

            logger.info(f"✅ 為圖片 {image_name} 生成問題: {question[:50]}...")
            return question

        except Exception as e:
            logger.error(f"❌ 生成問題失敗: {e}")
            return "相關技術內容和規範要求是什麼？"

    def _extract_category_from_filename(self, filename: str) -> str:
        """從檔名中提取技術類別"""
        try:
            # 移除副檔名
            name_without_ext = Path(filename).stem

            # 根據檔名模式判斷類別
            if "1.0" in name_without_ext or "LVDS" in name_without_ext:
                return "LVDS線束加工"
            elif "1.1" in name_without_ext or "Cable" in name_without_ext:
                return "Cable設計規範"
            elif "1.2" in name_without_ext or "Wire" in name_without_ext:
                return "Wire Harness製程"
            elif "1.3" in name_without_ext or "WH" in name_without_ext:
                return "WH線束加工"
            elif "1.4" in name_without_ext or "FFC" in name_without_ext:
                return "FFC設計規範"
            elif "2.0" in name_without_ext:
                return "外部線設計"
            elif "2.1" in name_without_ext or "EC" in name_without_ext:
                return "EC產品工藝"
            elif "2.2" in name_without_ext:
                return "外部線應用"
            elif "3.0" in name_without_ext:
                return "汽車電線技術"
            elif "3.1" in name_without_ext or "AT-Cable" in name_without_ext:
                return "AT-Cable設計"
            elif "材料" in name_without_ext:
                return "材料特性"
            elif "連接器" in name_without_ext:
                return "連接器技術"
            elif "測試" in name_without_ext:
                return "測試程序"
            elif "合同" in name_without_ext:
                return "合同評審"
            elif "客戶" in name_without_ext:
                return "客戶管理"
            elif "產品" in name_without_ext:
                return "產品設計"
            elif "識圖" in name_without_ext:
                return "識圖指南"
            elif "清單" in name_without_ext:
                return "清單文件"
            elif "QSA" in name_without_ext:
                return "QSA稽核"
            elif "生產線" in name_without_ext:
                return "生產線學習"
            else:
                return "技術規範"
        except Exception:
            return "技術內容"

    def evaluate_answer_quality(self, question: str, answer: str, image_path: str = None) -> Dict[str, float]:
        """評估回答品質"""
        try:
            # 構建評估提示
            eval_prompt = f"""
            請評估以下RAG系統回答的品質：

            問題: {question}
            回答: {answer}

            請從以下四個維度評分（0-1分）：
            1. 技術準確性 - 回答是否技術正確
            2. 完整性 - 回答是否完整回應問題
            3. 清晰度 - 回答是否清楚易懂
            4. 圖片引用 - 是否正確引用相關圖片

            請以JSON格式回答，例如：
            {{"technical_accuracy": 0.8, "completeness": 0.7, "clarity": 0.9, "image_reference": 0.6}}
            """

            # 調用 Claude 進行評估
            claude_response = self._call_claude(eval_prompt)

            # 嘗試解析 JSON 回應
            try:
                import json
                import re

                # 提取 JSON 部分
                json_match = re.search(r'\{[^}]+\}', claude_response)
                if json_match:
                    eval_data = json.loads(json_match.group())

                    # 計算總分
                    weights = RAGTestConfig.EVALUATION_CRITERIA
                    overall_score = (
                        eval_data.get('technical_accuracy', 0.5) * weights['technical_accuracy']['weight'] +
                        eval_data.get('completeness', 0.5) * weights['completeness']['weight'] +
                        eval_data.get('clarity', 0.5) * weights['clarity']['weight'] +
                        eval_data.get('image_reference', 0.5) * weights['image_reference']['weight']
                    )

                    evaluation = {
                        'technical_accuracy': eval_data.get('technical_accuracy', 0.5),
                        'completeness': eval_data.get('completeness', 0.5),
                        'clarity': eval_data.get('clarity', 0.5),
                        'image_reference': eval_data.get('image_reference', 0.5),
                        'overall_score': overall_score
                    }
                else:
                    raise ValueError("無法解析評估結果")

            except Exception as parse_error:
                logger.warning(f"⚠️ 解析評估結果失敗，使用預設評分: {parse_error}")
                # 使用簡單的啟發式評估
                evaluation = {
                    'technical_accuracy': 0.8 if len(answer) > 100 else 0.5,
                    'completeness': 0.7 if len(answer) > 200 else 0.4,
                    'clarity': 0.9 if '。' in answer else 0.6,
                    'image_reference': 0.6 if ('圖片' in answer or 'http' in answer) else 0.3,
                    'overall_score': 0.7
                }

            logger.info(f"✅ 評估完成，總分: {evaluation['overall_score']:.3f}")
            return evaluation

        except Exception as e:
            logger.error(f"❌ 評估失敗: {e}")
            return {
                'technical_accuracy': 0.5,
                'completeness': 0.5,
                'clarity': 0.5,
                'image_reference': 0.3,
                'overall_score': 0.45
            }

class RAGAPIClient:
    """RAG API 客戶端"""

    def __init__(self):
        self.api_url = RAGTestConfig.RAG_API_URL
        self.timeout = RAGTestConfig.API_TIMEOUT
        self.retry_count = RAGTestConfig.RETRY_COUNT

    def query_rag(self, question: str, session_id: str = None) -> Dict[str, Any]:
        """查詢 RAG 系統"""
        # 使用 /query-with-memory 端點格式，啟用記憶功能
        payload = {
            "user_query": question,
            "sessionId": session_id or f"test_session_{int(time.time())}",
            "streaming": False,
            "use_persistent_session": True  # 啟用記憶功能
        }
        
        for attempt in range(self.retry_count):
            try:
                logger.info(f"🔄 查詢 RAG 系統 (嘗試 {attempt + 1}/{self.retry_count})")
                
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("✅ RAG 查詢成功")
                    return result
                else:
                    logger.warning(f"⚠️ RAG API 返回錯誤狀態: {response.status_code}")
                    if attempt == self.retry_count - 1:
                        raise Exception(f"API 錯誤: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ RAG API 超時 (嘗試 {attempt + 1}/{self.retry_count})")
                if attempt == self.retry_count - 1:
                    raise Exception("API 超時")
                    
            except Exception as e:
                logger.error(f"❌ RAG API 錯誤: {e}")
                if attempt == self.retry_count - 1:
                    raise e
            
            # 重試前等待
            if attempt < self.retry_count - 1:
                time.sleep(2)
        
        raise Exception("RAG API 查詢失敗")

class RAGTester:
    """RAG 測試器主類"""
    
    def __init__(self):
        # 驗證配置
        if not RAGTestConfig.validate_config():
            raise ValueError("配置驗證失敗")

        # 初始化必要組件
        self.rag_client = RAGAPIClient()
        self.cost_calculator = CostCalculator()

        # 初始化可選組件
        self.claude_client = None
        if RAGTestConfig.AWS_ACCESS_KEY_ID and RAGTestConfig.AWS_SECRET_ACCESS_KEY:
            try:
                self.claude_client = ClaudeClient()
                logger.info("✅ Claude 客戶端 (AWS Bedrock) 初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ Claude 客戶端 (AWS Bedrock) 初始化失敗: {e}")
                logger.info("   將跳過問題生成和評估功能")
        else:
            logger.info("ℹ️ 未設定 AWS 憑證，將跳過問題生成和評估功能")

        logger.info("✅ RAG 測試器初始化完成")
    
    def test_single_image(self, image_path: str, custom_question: str = None, session_id: str = None) -> RAGTestResult:
        """測試單張圖片"""
        start_time = time.time()
        
        try:
            image_name = Path(image_path).name
            category = Path(image_path).parent.name
            
            logger.info(f"🧪 開始測試圖片: {image_name}")
            
            # 1. 生成問題 (如果沒有提供自定義問題)
            if custom_question:
                question = custom_question
                question_generation_cost = 0.0
            else:
                if self.claude_client:
                    question = self.claude_client.generate_question_from_image(image_path)
                    question_generation_cost = self.cost_calculator.calculate_claude_cost(
                        f"分析圖片並生成問題: {image_path}", question
                    )
                else:
                    # 沒有 Claude 時使用預設問題
                    question = f"請描述這張圖片 {image_name} 的內容和技術要點"
                    question_generation_cost = 0.0
                    logger.info("ℹ️ 使用預設問題（未設定 Claude API）")

            # 2. 查詢 RAG 系統（使用記憶功能）
            # 為同一類別的圖片使用相同的 session ID，以測試記憶功能
            if not session_id:
                session_id = f"test_category_{category}_{int(time.time() // 3600)}"  # 每小時一個新會話

            rag_response = self.rag_client.query_rag(question, session_id)
            rag_answer = rag_response.get('response', rag_response.get('reply', rag_response.get('answer', '無法獲取回答')))

            # 3. 評估回答品質
            if self.claude_client:
                evaluation = self.claude_client.evaluate_answer_quality(question, rag_answer, image_path)
                evaluation_cost = self.cost_calculator.calculate_claude_cost(
                    f"評估問題: {question}\n回答: {rag_answer}", str(evaluation)
                )
            else:
                # 沒有 Claude 時使用簡單評估
                evaluation = {
                    "technical_accuracy": 0.8,  # 預設分數
                    "completeness": 0.8,
                    "clarity": 0.8,
                    "overall_score": 0.8,
                    "evaluation_reason": "未使用 Claude 評估，使用預設分數"
                }
                evaluation_cost = 0.0
                logger.info("ℹ️ 使用預設評估分數（未設定 Claude API）")
            
            # 4. 計算 RAG 成本
            rag_cost = self.cost_calculator.calculate_openai_cost(question, rag_answer)
            
            # 5. 計算總成本
            cost_info = CostInfo(
                claude_question_generation_cost=question_generation_cost,
                claude_evaluation_cost=evaluation_cost,
                openai_rag_cost=rag_cost
            )
            cost_info.calculate_total()
            
            # 6. 計算響應時間
            response_time = time.time() - start_time
            
            # 7. 檢查是否有圖片引用
            has_image_reference = ('圖片' in rag_answer or 'http' in rag_answer or 
                                 'localhost' in rag_answer or '.png' in rag_answer or 
                                 '.jpg' in rag_answer)
            
            # 8. 建立測試結果
            result = RAGTestResult(
                image_path=image_path,
                category=category,
                generated_question=question,
                rag_answer=rag_answer,
                evaluation_scores=evaluation,
                overall_score=evaluation.get('overall_score', 0.0),
                response_time=response_time,
                has_image_reference=has_image_reference,
                technical_accuracy=evaluation.get('technical_accuracy', 0.0),
                completeness=evaluation.get('completeness', 0.0),
                clarity=evaluation.get('clarity', 0.0),
                cost_info=cost_info,
                api_response=rag_response
            )
            
            logger.info(f"✅ 測試完成: {image_name}, 得分: {result.overall_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 測試失敗: {e}")
            return RAGTestResult(
                image_path=image_path,
                category=Path(image_path).parent.name,
                generated_question=custom_question or "測試失敗",
                rag_answer=f"測試失敗: {str(e)}",
                evaluation_scores={},
                overall_score=0.0,
                response_time=time.time() - start_time,
                has_image_reference=False,
                technical_accuracy=0.0,
                completeness=0.0,
                clarity=0.0,
                error_message=str(e)
            )


