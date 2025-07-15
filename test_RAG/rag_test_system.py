#!/usr/bin/env python3
"""
RAG 系統測試框架
基於圖片生成問題 → main.py回答 → Claude評分的流程
"""

import os
import sys
import json
import time
import logging
import requests
import base64
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

# 設置日誌（需要在其他導入之前）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加父目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(current_dir, 'config'))

# 載入環境變數
load_dotenv(os.path.join(parent_dir, '.env'))

# 導入配置
try:
    from test_config import RAGTestConfig
    USE_CONFIG = True
    logger.info("✅ 成功載入測試配置")
except ImportError as e:
    USE_CONFIG = False
    logger.warning(f"無法導入測試配置，使用預設值: {e}")

@dataclass
class CostInfo:
    """成本資訊數據類"""
    claude_question_generation_cost: float = 0.0  # Claude 問題生成成本
    claude_evaluation_cost: float = 0.0           # Claude 評估成本
    openai_rag_cost: float = 0.0                  # OpenAI RAG 回答成本
    total_cost: float = 0.0                       # 總成本

    def calculate_total(self):
        """計算總成本"""
        self.total_cost = self.claude_question_generation_cost + self.claude_evaluation_cost + self.openai_rag_cost
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

    # Claude 3.7 Sonnet 定價 (USD per token) - 更新至最新定價
    CLAUDE_INPUT_COST_PER_TOKEN = 0.000003   # $3 per 1M input tokens
    CLAUDE_OUTPUT_COST_PER_TOKEN = 0.000015  # $15 per 1M output tokens

    # OpenAI GPT-4o 定價 (USD per token) - 更新至最新定價
    OPENAI_INPUT_COST_PER_TOKEN = 0.0000025   # $2.5 per 1M input tokens
    OPENAI_OUTPUT_COST_PER_TOKEN = 0.00001    # $10 per 1M output tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """估算文本的 token 數量 (粗略估算: 1 token ≈ 4 字符)"""
        return len(text) // 4

    @staticmethod
    def calculate_claude_cost(input_text: str, output_text: str) -> float:
        """計算 Claude 使用成本"""
        input_tokens = CostCalculator.estimate_tokens(input_text)
        output_tokens = CostCalculator.estimate_tokens(output_text)

        input_cost = input_tokens * CostCalculator.CLAUDE_INPUT_COST_PER_TOKEN
        output_cost = output_tokens * CostCalculator.CLAUDE_OUTPUT_COST_PER_TOKEN

        return input_cost + output_cost

    @staticmethod
    def calculate_openai_cost(input_text: str, output_text: str) -> float:
        """計算 OpenAI 使用成本"""
        input_tokens = CostCalculator.estimate_tokens(input_text)
        output_tokens = CostCalculator.estimate_tokens(output_text)

        input_cost = input_tokens * CostCalculator.OPENAI_INPUT_COST_PER_TOKEN
        output_cost = output_tokens * CostCalculator.OPENAI_OUTPUT_COST_PER_TOKEN

        return input_cost + output_cost

class RAGTestSystem:
    """RAG系統測試框架 - 基於圖片生成問題測試流程"""

    def __init__(self,
                 images_dir: str = None,
                 main_py_path: str = None,
                 api_base_url: str = None):
        """初始化RAG測試系統"""
        # 使用配置文件或預設值
        if USE_CONFIG:
            self.images_dir = Path(images_dir) if images_dir else RAGTestConfig.IMAGES_DIR
            self.main_py_path = Path(main_py_path) if main_py_path else RAGTestConfig.MAIN_PY_PATH
            self.api_base_url = api_base_url if api_base_url else RAGTestConfig.get_api_base_url()
            RAGTestConfig.ensure_directories()
        else:
            self.images_dir = Path(images_dir) if images_dir else Path("/home/chun/heph-dev/JH/outputs/images/zerox_output")
            self.main_py_path = Path(main_py_path) if main_py_path else Path("/home/chun/heph-dev/JH/main.py")
            self.api_base_url = api_base_url if api_base_url else "http://localhost:8000"

        self.query_endpoint = f"{self.api_base_url}/query-with-memory"

        # 檢查路徑是否存在
        if not self.images_dir.exists():
            raise ValueError(f"圖片目錄不存在: {self.images_dir}")
        if not self.main_py_path.exists():
            raise ValueError(f"main.py 不存在: {self.main_py_path}")

        # 初始化Claude (用於生成問題和評分)
        self._init_claude()

        # 評分標準
        if USE_CONFIG:
            self.evaluation_criteria = RAGTestConfig.EVALUATION_WEIGHTS
            self.scoring_criteria = RAGTestConfig.SCORING_CRITERIA
            self.image_keywords = RAGTestConfig.IMAGE_REFERENCE_KEYWORDS
            self.technical_terms = RAGTestConfig.TECHNICAL_TERMS
        else:
            self.evaluation_criteria = {
                "technical_accuracy": 0.4,
                "completeness": 0.3,
                "image_reference": 0.2,
                "clarity": 0.1
            }
            self.image_keywords = ["圖片", "圖像", "圖面", "圖表", "如圖", "見圖", "https://", "http://"]
            self.technical_terms = ["材料", "連接器", "線束", "測試", "規格", "設計"]

    def _init_claude(self):
        """初始化Claude客戶端"""
        try:
            # 直接使用Anthropic Bedrock（跳過不存在的claude_image_qa_test模組）
            self._init_bedrock_claude()
            logger.info("✅ 使用Bedrock Claude系統")
        except Exception as e:
            logger.error(f"Bedrock Claude初始化失敗: {e}")
            try:
                from image_qa_test_system import ImageQATestSystem
                self.claude_system = ImageQATestSystem()
                self.use_claude = False
                logger.info("⚠️ 使用OpenAI系統作為備選")
            except ImportError as e2:
                logger.error(f"所有系統初始化失敗: {e2}")
                # 創建一個簡化的問題生成器
                self.claude_system = None
                self.use_claude = False
                logger.warning("⚠️ 使用簡化的問題生成器")

    def _init_bedrock_claude(self):
        """初始化Bedrock Claude客戶端"""
        try:
            from anthropic import AnthropicBedrock

            # 從環境變數讀取配置
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_region = os.getenv("AWS_REGION", "us-east-1")
            model = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")

            if not aws_access_key or not aws_secret_key:
                raise ValueError("AWS憑證未設定")

            self.bedrock_client = AnthropicBedrock(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_region=aws_region
            )
            self.bedrock_model = model
            self.claude_system = self  # 使用自己作為Claude系統
            self.use_claude = True

        except ImportError:
            logger.warning("Anthropic Bedrock SDK 未安裝")
            raise ValueError("請安裝 anthropic[bedrock]: pip install 'anthropic[bedrock]'")
        except Exception as e:
            logger.error(f"Bedrock Claude初始化失敗: {e}")
            raise ValueError(f"Bedrock Claude初始化失敗: {e}")

    def get_image_categories(self) -> Dict[str, List[str]]:
        """從images目錄獲取圖片分類"""
        categories = defaultdict(list)

        if not self.images_dir.exists():
            logger.error(f"圖片目錄不存在: {self.images_dir}")
            return {}

        for image_file in self.images_dir.glob("*.png"):
            # 從檔名提取類別 (例如: 材料介紹._page_1.png -> 材料介紹)
            filename = image_file.name
            if "_page_" in filename:
                category = filename.split("_page_")[0].rstrip(".")
                categories[category].append(str(image_file))

        logger.info(f"找到 {len(categories)} 個圖片類別，共 {sum(len(imgs) for imgs in categories.values())} 張圖片")
        return dict(categories)

    def generate_question_from_image(self, image_path: str) -> Dict[str, Any]:
        """使用Claude從圖片生成測試問題"""
        try:
            logger.info(f"🖼️ 從圖片生成問題: {Path(image_path).name}")

            if self.claude_system is None:
                # 使用簡化的問題生成器
                return self._generate_simple_question(image_path)

            # 檢查是否使用Bedrock Claude
            if hasattr(self, 'bedrock_client'):
                result = self.generate_questions_with_bedrock(image_path, 1)
            else:
                # 使用原有的Claude系統
                result = self.claude_system.generate_questions_from_image(image_path, 1)

            if result["success"]:
                questions = self.parse_questions(result["response"])
                if questions:
                    return {
                        "success": True,
                        "question": questions[0],
                        "raw_response": result["response"],
                        "input_text": result.get("input_text", ""),
                        "output_text": result.get("output_text", result["response"])
                    }
                else:
                    return {
                        "success": False,
                        "error": "無法解析生成的問題"
                    }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "問題生成失敗")
                }

        except Exception as e:
            logger.error(f"生成問題失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_simple_question(self, image_path: str) -> Dict[str, Any]:
        """簡化的問題生成器（當Claude不可用時）"""
        filename = Path(image_path).name
        category = self._extract_category_from_path(image_path)

        # 根據類別生成預設問題
        category_questions = {
            "材料介紹": "這張圖片中介紹了什麼材料？請詳細說明其特性和應用。",
            "材料认识": "圖片中展示的材料有哪些特點？請說明其用途和重要性。",
            "連接器": "這個連接器的結構和功能是什麼？",
            "線束": "圖片中的線束設計有什麼特點？",
            "測試": "這個測試程序的目的和步驟是什麼？"
        }

        # 選擇合適的問題
        question = category_questions.get(category, f"請描述圖片中關於{category}的技術內容。")

        return {
            "success": True,
            "question": question,
            "raw_response": f"簡化問題生成器為{category}類別生成的問題"
        }

    def encode_image(self, image_path: str) -> str:
        """編碼圖片為base64（Bedrock Claude使用）"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"圖片編碼失敗: {e}")
            raise

    def generate_questions_with_bedrock(self, image_path: str, num_questions: int = 1) -> Dict[str, Any]:
        """使用Bedrock Claude生成問題"""
        try:
            if not hasattr(self, 'bedrock_client'):
                return {"success": False, "error": "Bedrock客戶端未初始化"}

            # 編碼圖片
            base64_image = self.encode_image(image_path)

            prompt = f"""這是一張工程技術文件圖片，請根據圖片內容生成 {num_questions} 個相關的技術問題。

要求：
1. 問題應該基於圖片中實際可見的技術內容
2. 問題應該具體且可以通過觀察圖片來回答
3. 問題應該涵蓋材料特性、技術規格、設計要點等方面

請嚴格按以下格式輸出：
1. [第一個問題]
{f"2. [第二個問題]" if num_questions > 1 else ""}
{f"3. [第三個問題]" if num_questions > 2 else ""}"""

            response = self.bedrock_client.messages.create(
                model=self.bedrock_model,
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ]
            )

            response_content = response.content[0].text if response.content else ""

            return {
                "success": True,
                "response": response_content,
                "input_text": prompt,
                "output_text": response_content,
                "usage": getattr(response, 'usage', None)
            }

        except Exception as e:
            logger.error(f"Bedrock問題生成失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def parse_questions(self, response_text: str) -> List[str]:
        """解析問題文本，提取各個問題"""
        questions = []
        lines = response_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 檢查是否是問題格式 (格式: "1. " 或 "2. " 等)
            if line.startswith(tuple(f"{i}. " for i in range(1, 21))):  # 支援最多20個問題
                question = line[3:].strip()  # 移除 "1. " 部分
                if question:
                    questions.append(question)

        # 如果沒有找到格式化的問題，嘗試按行分割
        if not questions:
            for line in lines:
                line = line.strip()
                if line and line.endswith('?'):  # 以問號結尾的可能是問題
                    questions.append(line)

        return questions

    def get_rag_sources(self, query: str) -> List[Dict[str, Any]]:
        """直接調用RAG系統獲取來源信息"""
        try:
            # 導入RAG系統
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

            from src.core.langchain_rag_system import LangChainParentChildRAG

            # 直接讀取.env文件獲取集合名稱
            import os
            from dotenv import load_dotenv
            load_dotenv()
            collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'JH-圖紙認識-langchain')

            # 初始化RAG系統 - 使用.env中的集合名稱
            rag_system = LangChainParentChildRAG(collection_name)

            # 檢索相關文件段落
            retrieval_results = rag_system.retrieve_relevant_chunks(query=query, top_k=5)

            sources = []
            for result in retrieval_results:
                # 獲取父子chunk信息
                parent_chunk = result.document
                child_chunk = result.child_chunk

                source_info = {
                    "page_num": child_chunk.page_num,
                    "topic": parent_chunk.metadata.get('topic', '未知主題'),
                    "sub_topic": child_chunk.sub_topic,
                    "content": child_chunk.content,
                    "content_type": child_chunk.content_type,
                    "keywords": child_chunk.keywords or [],
                    "similarity_score": result.similarity_score,
                    "relevance_reason": result.relevance_reason,
                    "has_images": child_chunk.has_images,
                    "image_path": child_chunk.image_path,
                    "image_analysis": getattr(child_chunk, 'image_analysis', '')
                }
                sources.append(source_info)

            logger.info(f"✅ 獲取到 {len(sources)} 個來源段落")
            return sources

        except Exception as e:
            logger.error(f"❌ 獲取RAG來源信息失敗: {e}")
            return []

    def call_main_py_api(self, query: str, session_id: str = "rag_test_session") -> Dict[str, Any]:
        """調用main.py的RAG API"""
        try:
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }
            data = {
                "user_query": query,
                "streaming": False,
                "sessionId": session_id
            }

            logger.info(f"🔄 調用main.py API: {query[:50]}...")
            start_time = time.time()

            response = requests.post(self.query_endpoint, headers=headers, json=data, timeout=60)
            response_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ main.py API 回應成功 (耗時: {response_time:.2f}s)")

                # 提取回應內容
                answer = result.get("reply", result.get("response", "無回應內容"))

                return {
                    "success": True,
                    "answer": answer,
                    "response_time": response_time,
                    "raw_response": result
                }
            else:
                logger.error(f"❌ main.py API 回應錯誤: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "answer": f"API 調用失敗 (狀態碼: {response.status_code})",
                    "response_time": response_time
                }

        except requests.exceptions.Timeout:
            logger.error(f"⏰ main.py API 調用超時")
            return {
                "success": False,
                "error": "請求超時",
                "answer": "API 調用超時，無法獲得回答",
                "response_time": 60.0
            }
        except Exception as e:
            logger.error(f"❌ main.py API 調用異常: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": f"API 調用失敗: {str(e)}",
                "response_time": 0.0
            }

    def evaluate_answer_with_claude(self, image_path: str, question: str, answer: str) -> Dict[str, float]:
        """使用Claude評估答案品質，基於圖片內容"""
        if self.claude_system is None:
            # 使用簡化的評估器
            return self._evaluate_answer_simple(question, answer)

        try:
            # 檢查是否使用Bedrock Claude
            if hasattr(self, 'bedrock_client'):
                return self._evaluate_with_bedrock(image_path, question, answer)

            # 編碼圖片
            base64_image = self.claude_system.encode_image(image_path)

            evaluation_prompt = f"""請根據圖片內容評估以下RAG系統回答的品質。

問題: {question}
回答: {answer}

請從以下四個維度評估，每個維度給出0-1之間的分數：

1. **技術準確性 (40%權重)**:
   - 1.0: 技術內容完全正確，與圖片內容完全吻合
   - 0.8: 大部分技術內容正確，有少量細節差異
   - 0.6: 基本技術概念正確，但有部分錯誤
   - 0.4: 技術內容有明顯錯誤
   - 0.0: 技術內容完全錯誤

2. **完整性 (30%權重)**:
   - 1.0: 完整回答了問題的所有要點
   - 0.8: 回答了主要要點，遺漏少量細節
   - 0.6: 回答了部分要點
   - 0.4: 回答不完整，遺漏重要內容
   - 0.0: 完全沒有回答問題

3. **圖片引用 (20%權重)**:
   - 1.0: 明確提及圖片內容或相關圖片URL
   - 0.8: 暗示或描述了圖片中的內容
   - 0.6: 回答與圖片內容相關但沒有明確引用
   - 0.0: 完全沒有引用圖片內容

4. **清晰度 (10%權重)**:
   - 1.0: 回答結構清晰，邏輯性強
   - 0.8: 回答基本清晰
   - 0.6: 回答一般清晰
   - 0.4: 回答不夠清晰
   - 0.0: 回答混亂難懂

請嚴格按照以下JSON格式回答，不要包含其他內容：
{{
    "technical_accuracy": 0.xxx,
    "completeness": 0.xxx,
    "image_reference": 0.xxx,
    "clarity": 0.xxx
}}"""

            # 檢查是否使用Bedrock Claude
            if hasattr(self.claude_system, 'client') and hasattr(self.claude_system.client, 'messages'):
                # 使用Bedrock Claude
                response = self.claude_system.client.messages.create(
                    model=self.claude_system.model,
                    max_tokens=200,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"你是一位專業的技術文件評估專家。{evaluation_prompt}"
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": base64_image
                                    }
                                }
                            ]
                        }
                    ]
                )
                response_text = response.content[0].text.strip() if response.content else ""
            else:
                # 使用OpenAI格式
                response = self.claude_system.client.chat.completions.create(
                    model=self.claude_system.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位專業的技術文件評估專家，能夠根據圖片內容準確評估RAG系統回答的品質。請嚴格按照JSON格式回答。"
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": evaluation_prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=200,
                    temperature=0.1
                )
                response_text = response.choices[0].message.content.strip()

            logger.info(f"Claude評估回應: {response_text}")

            try:
                # 嘗試解析JSON
                scores = json.loads(response_text)

                # 驗證分數格式
                required_keys = ["technical_accuracy", "completeness", "image_reference", "clarity"]
                for key in required_keys:
                    if key not in scores:
                        scores[key] = 0.5
                    else:
                        scores[key] = max(0.0, min(1.0, float(scores[key])))

                return scores

            except json.JSONDecodeError:
                logger.warning(f"無法解析Claude評估結果，使用簡化評估")
                return self._evaluate_answer_simple(question, answer)

        except Exception as e:
            logger.error(f"Claude評估失敗: {e}")
            return self._evaluate_answer_simple(question, answer)

    def _evaluate_with_bedrock(self, image_path: str, question: str, answer: str) -> Dict[str, float]:
        """使用Bedrock Claude評估答案品質"""
        try:
            base64_image = self.encode_image(image_path)

            evaluation_prompt = f"""請根據圖片內容評估以下RAG系統回答的品質。

問題: {question}
回答: {answer}

請從以下四個維度評估，每個維度給出0-1之間的分數：

1. **技術準確性**: 技術內容是否正確，與圖片內容是否吻合
2. **完整性**: 是否完整回答了問題的所有要點
3. **圖片引用**: 是否明確提及或引用了圖片內容
4. **清晰度**: 回答是否結構清晰，邏輯性強

請嚴格按照以下JSON格式回答：
{{
    "technical_accuracy": 0.xxx,
    "completeness": 0.xxx,
    "image_reference": 0.xxx,
    "clarity": 0.xxx
}}"""

            response = self.bedrock_client.messages.create(
                model=self.bedrock_model,
                max_tokens=200,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": evaluation_prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ]
            )

            response_text = response.content[0].text.strip() if response.content else ""
            logger.info(f"Bedrock Claude評估回應: {response_text}")

            try:
                # 嘗試解析JSON
                scores = json.loads(response_text)

                # 驗證分數格式
                required_keys = ["technical_accuracy", "completeness", "image_reference", "clarity"]
                for key in required_keys:
                    if key not in scores:
                        scores[key] = 0.5
                    else:
                        scores[key] = max(0.0, min(1.0, float(scores[key])))

                return scores

            except json.JSONDecodeError:
                logger.warning(f"無法解析Bedrock評估結果，使用簡化評估")
                return self._evaluate_answer_simple(question, answer)

        except Exception as e:
            logger.error(f"Bedrock評估失敗: {e}")
            return self._evaluate_answer_simple(question, answer)

    def evaluate_answer_with_claude_detailed(self, image_path: str, question: str, answer: str) -> Dict[str, Any]:
        """使用Claude評估答案品質，返回詳細資訊包括成本計算所需的文本"""
        if self.claude_system is None:
            # 使用簡化的評估器
            return {
                "scores": self._evaluate_answer_simple(question, answer),
                "input_text": "",
                "output_text": ""
            }

        try:
            # 檢查是否使用Bedrock Claude
            if hasattr(self, 'bedrock_client'):
                return self._evaluate_with_bedrock_detailed(image_path, question, answer)

            # 使用原有的評估邏輯但返回詳細資訊
            scores = self.evaluate_answer_with_claude(image_path, question, answer)
            return {
                "scores": scores,
                "input_text": f"問題: {question}\n回答: {answer}",
                "output_text": str(scores)
            }

        except Exception as e:
            logger.error(f"詳細評估失敗: {e}")
            return {
                "scores": self._evaluate_answer_simple(question, answer),
                "input_text": "",
                "output_text": ""
            }

    def _evaluate_with_bedrock_detailed(self, image_path: str, question: str, answer: str) -> Dict[str, Any]:
        """使用Bedrock Claude進行詳細評估"""
        try:
            # 編碼圖片
            base64_image = self.encode_image(image_path)

            evaluation_prompt = f"""請根據圖片內容評估以下RAG系統回答的品質。

問題: {question}
回答: {answer}

請從以下四個維度評估，每個維度給出0-1之間的分數：

1. **技術準確性 (40%權重)**:
   - 1.0: 技術內容完全正確，與圖片內容完全吻合
   - 0.8: 大部分技術內容正確，有少量細節差異
   - 0.6: 基本技術概念正確，但有部分錯誤
   - 0.4: 技術內容有明顯錯誤
   - 0.0: 技術內容完全錯誤

2. **完整性 (30%權重)**:
   - 1.0: 完整回答了問題的所有要點
   - 0.8: 回答了主要要點，遺漏少量細節
   - 0.6: 回答了部分要點
   - 0.4: 回答不完整，遺漏重要內容
   - 0.0: 完全沒有回答問題

3. **圖片引用 (20%權重)**:
   - 1.0: 明確提及圖片內容或相關圖片URL
   - 0.8: 暗示或描述了圖片中的內容
   - 0.6: 回答與圖片內容相關但沒有明確引用
   - 0.0: 完全沒有引用圖片內容

4. **清晰度 (10%權重)**:
   - 1.0: 回答結構清晰，邏輯性強
   - 0.8: 回答基本清晰
   - 0.6: 回答一般清晰
   - 0.4: 回答不夠清晰
   - 0.0: 回答混亂難懂

請嚴格按照以下JSON格式回答，不要包含其他內容：
{{
    "technical_accuracy": 0.xxx,
    "completeness": 0.xxx,
    "image_reference": 0.xxx,
    "clarity": 0.xxx
}}"""

            response = self.bedrock_client.messages.create(
                model=self.bedrock_model,
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": evaluation_prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ]
            )

            response_text = response.content[0].text.strip() if response.content else ""
            logger.info(f"Bedrock Claude評估回應: {response_text}")

            try:
                # 嘗試解析JSON
                scores = json.loads(response_text)

                # 驗證分數格式
                required_keys = ["technical_accuracy", "completeness", "image_reference", "clarity"]
                for key in required_keys:
                    if key not in scores:
                        scores[key] = 0.5
                    else:
                        scores[key] = max(0.0, min(1.0, float(scores[key])))

                return {
                    "scores": scores,
                    "input_text": evaluation_prompt,
                    "output_text": response_text
                }

            except json.JSONDecodeError:
                logger.warning(f"無法解析Bedrock評估結果，使用簡化評估")
                return {
                    "scores": self._evaluate_answer_simple(question, answer),
                    "input_text": evaluation_prompt,
                    "output_text": response_text
                }

        except Exception as e:
            logger.error(f"Bedrock詳細評估失敗: {e}")
            return {
                "scores": self._evaluate_answer_simple(question, answer),
                "input_text": "",
                "output_text": ""
            }

    def _evaluate_answer_simple(self, question: str, answer: str) -> Dict[str, float]:
        """簡化的答案評估器（當Claude不可用時）"""
        if not answer or answer.strip() == "":
            return {
                "technical_accuracy": 0.0,
                "completeness": 0.0,
                "image_reference": 0.0,
                "clarity": 0.0
            }

        # 基礎評估邏輯
        answer_length = len(answer.strip())

        # 技術準確性 - 基於技術術語的出現
        technical_terms = ["材料", "連接器", "線束", "測試", "規格", "設計", "結構", "功能", "特性", "應用"]
        term_count = sum(1 for term in technical_terms if term in answer)
        technical_accuracy = min(0.3 + term_count * 0.1, 1.0)

        # 完整性 - 基於答案長度和結構
        if answer_length > 200:
            completeness = 0.8
        elif answer_length > 100:
            completeness = 0.6
        elif answer_length > 50:
            completeness = 0.4
        else:
            completeness = 0.2

        # 圖片引用 - 檢查是否有圖片相關詞彙
        has_image_ref = self.check_image_reference(answer)
        image_reference = 0.8 if has_image_ref else 0.0

        # 清晰度 - 基於結構化內容
        structure_indicators = ["1.", "2.", "•", "-", "：", "。"]
        structure_count = sum(1 for indicator in structure_indicators if indicator in answer)
        clarity = min(0.4 + structure_count * 0.1, 1.0)

        return {
            "technical_accuracy": technical_accuracy,
            "completeness": completeness,
            "image_reference": image_reference,
            "clarity": clarity
        }

    def check_image_reference(self, answer: str) -> bool:
        """檢查回答中是否有圖片引用"""
        if USE_CONFIG:
            image_indicators = self.image_keywords
        else:
            image_indicators = [
                "圖片", "圖像", "圖面", "圖表", "圖示",
                "如圖", "見圖", "參考圖",
                "https://", "http://",
                "相關圖片", "教材圖片", "示意圖"
            ]

        return any(indicator in answer for indicator in image_indicators)

    def test_single_image(self, image_path: str, session_id: str = None) -> RAGTestResult:
        """測試單張圖片的完整流程：圖片→問題→RAG回答→評分"""
        if session_id is None:
            session_id = f"rag_test_{int(time.time())}"

        start_time = time.time()
        category = self._extract_category_from_path(image_path)

        try:
            logger.info(f"🖼️ 開始測試圖片: {Path(image_path).name}")

            # 初始化成本追蹤
            cost_info = CostInfo()

            # 步驟1: 從圖片生成問題
            logger.info("📝 步驟1: 從圖片生成測試問題...")
            question_result = self.generate_question_from_image(image_path)

            if not question_result["success"]:
                return RAGTestResult(
                    image_path=image_path,
                    category=category,
                    generated_question="",
                    rag_answer="",
                    evaluation_scores={},
                    overall_score=0.0,
                    response_time=time.time() - start_time,
                    has_image_reference=False,
                    technical_accuracy=0.0,
                    completeness=0.0,
                    clarity=0.0,
                    cost_info=cost_info,
                    error_message=f"問題生成失敗: {question_result.get('error', '未知錯誤')}"
                )

            question = question_result["question"]
            logger.info(f"✅ 生成問題: {question}")

            # 計算問題生成成本 (Claude)
            if "input_text" in question_result and "output_text" in question_result:
                cost_info.claude_question_generation_cost = CostCalculator.calculate_claude_cost(
                    question_result["input_text"], question_result["output_text"]
                )

            # 步驟2: 使用main.py RAG系統回答問題
            logger.info("🤖 步驟2: 使用RAG系統回答問題...")
            api_result = self.call_main_py_api(question, session_id)

            if not api_result["success"]:
                return RAGTestResult(
                    image_path=image_path,
                    category=category,
                    generated_question=question,
                    rag_answer=api_result["answer"],
                    evaluation_scores={},
                    overall_score=0.0,
                    response_time=time.time() - start_time,
                    has_image_reference=False,
                    technical_accuracy=0.0,
                    completeness=0.0,
                    clarity=0.0,
                    cost_info=cost_info,
                    error_message=f"RAG回答失敗: {api_result.get('error', '未知錯誤')}"
                )

            answer = api_result["answer"]
            logger.info(f"✅ RAG回答: {answer[:100]}...")

            # 計算 RAG 回答成本 (OpenAI) - 估算
            cost_info.openai_rag_cost = CostCalculator.calculate_openai_cost(question, answer)

            # 步驟2.5: 直接調用RAG系統獲取來源信息
            logger.info("📚 獲取RAG來源信息...")
            sources_info = self.get_rag_sources(question)

            # 步驟3: 使用Claude評估答案品質
            logger.info("⭐ 步驟3: 使用Claude評估答案品質...")
            evaluation_result = self.evaluate_answer_with_claude_detailed(image_path, question, answer)
            evaluation_scores = evaluation_result["scores"]

            # 計算評估成本 (Claude)
            if "input_text" in evaluation_result and "output_text" in evaluation_result:
                cost_info.claude_evaluation_cost = CostCalculator.calculate_claude_cost(
                    evaluation_result["input_text"], evaluation_result["output_text"]
                )

            # 計算總成本
            cost_info.calculate_total()

            # 檢查圖片引用
            has_image_reference = self.check_image_reference(answer)

            # 計算總體分數
            if USE_CONFIG:
                overall_score = (
                    evaluation_scores["technical_accuracy"] * self.evaluation_criteria["technical_accuracy"] +
                    evaluation_scores["completeness"] * self.evaluation_criteria["completeness"] +
                    evaluation_scores["image_reference"] * self.evaluation_criteria["image_reference"] +
                    evaluation_scores["clarity"] * self.evaluation_criteria["clarity"]
                )
            else:
                overall_score = (
                    evaluation_scores["technical_accuracy"] * 0.4 +
                    evaluation_scores["completeness"] * 0.3 +
                    evaluation_scores["image_reference"] * 0.2 +
                    evaluation_scores["clarity"] * 0.1
                )

            total_time = time.time() - start_time

            logger.info(f"✅ 測試完成！")
            logger.info(f"   技術準確性: {evaluation_scores['technical_accuracy']:.3f}")
            logger.info(f"   完整性: {evaluation_scores['completeness']:.3f}")
            logger.info(f"   圖片引用: {evaluation_scores['image_reference']:.3f}")
            logger.info(f"   清晰度: {evaluation_scores['clarity']:.3f}")
            logger.info(f"   總體得分: {overall_score:.3f}")
            logger.info(f"   總耗時: {total_time:.2f}s")

            return RAGTestResult(
                image_path=image_path,
                category=category,
                generated_question=question,
                rag_answer=answer,
                evaluation_scores=evaluation_scores,
                overall_score=overall_score,
                response_time=total_time,
                has_image_reference=has_image_reference,
                technical_accuracy=evaluation_scores["technical_accuracy"],
                completeness=evaluation_scores["completeness"],
                clarity=evaluation_scores["clarity"],
                cost_info=cost_info,
                api_response={
                    **api_result,
                    "sources": sources_info  # 添加來源信息
                }
            )

        except Exception as e:
            logger.error(f"❌ 測試圖片時發生錯誤: {e}")
            return RAGTestResult(
                image_path=image_path,
                category=category,
                generated_question="",
                rag_answer="",
                evaluation_scores={},
                overall_score=0.0,
                response_time=time.time() - start_time,
                has_image_reference=False,
                technical_accuracy=0.0,
                completeness=0.0,
                clarity=0.0,
                error_message=str(e)
            )

    def _extract_category_from_path(self, image_path: str) -> str:
        """從圖片路徑提取類別名稱"""
        filename = Path(image_path).name
        if "_page_" in filename:
            return filename.split("_page_")[0].rstrip(".")
        return "未知類別"

    def batch_test_images(self, image_paths: List[str], session_id: str = None) -> List[RAGTestResult]:
        """批量測試多張圖片"""
        if session_id is None:
            session_id = f"batch_rag_test_{int(time.time())}"

        results = []
        total_images = len(image_paths)

        logger.info(f"🚀 開始批量測試 {total_images} 張圖片")

        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"處理第 {i}/{total_images} 張圖片: {Path(image_path).name}")

            result = self.test_single_image(image_path, f"{session_id}_{i}")
            results.append(result)

            # 避免API限制，添加延遲
            if i < total_images:
                time.sleep(2)  # RAG測試需要更長的延遲

        logger.info(f"✅ 批量測試完成，成功處理 {len(results)}/{total_images} 張圖片")
        return results

    def start_main_py_server(self) -> bool:
        """啟動main.py服務器"""
        try:
            # 檢查服務器是否已經運行
            try:
                response = requests.get(f"{self.api_base_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ main.py 服務器已經在運行")
                    return True
            except:
                pass

            logger.info("🚀 啟動 main.py 服務器...")

            # 啟動服務器
            cmd = ["python", str(self.main_py_path)]
            process = subprocess.Popen(
                cmd,
                cwd=self.main_py_path.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 等待服務器啟動
            for i in range(30):  # 等待最多30秒
                try:
                    response = requests.get(f"{self.api_base_url}/health", timeout=2)
                    if response.status_code == 200:
                        logger.info("✅ main.py 服務器啟動成功")
                        return True
                except:
                    time.sleep(1)

            logger.error("❌ main.py 服務器啟動失敗")
            return False

        except Exception as e:
            logger.error(f"❌ 啟動 main.py 服務器時發生錯誤: {e}")
            return False

if __name__ == "__main__":
    # 測試範例
    try:
        rag_test = RAGTestSystem()

        # 獲取圖片分類
        categories = rag_test.get_image_categories()
        if not categories:
            print("❌ 沒有找到圖片檔案")
            exit(1)

        print(f"找到 {len(categories)} 個類別:")
        for category, images in categories.items():
            print(f"  {category}: {len(images)} 張圖片")

        # 測試第一張圖片
        first_category = list(categories.keys())[0]
        first_image = categories[first_category][0]

        print(f"\n測試圖片: {first_image}")
        result = rag_test.test_single_image(first_image)

        print(f"\n測試結果:")
        print(f"類別: {result.category}")
        print(f"生成問題: {result.generated_question}")
        print(f"技術準確性: {result.technical_accuracy:.3f}")
        print(f"完整性: {result.completeness:.3f}")
        print(f"圖片引用: {result.has_image_reference}")
        print(f"總體得分: {result.overall_score:.3f}")
        print(f"回應時間: {result.response_time:.2f}s")
        print(f"RAG回答: {result.rag_answer[:200]}...")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")

    def evaluate_answer_quality_no_image(self, question: str, rag_answer: str) -> Dict[str, float]:
        """評估回答品質（無圖片版本）"""
        try:
            evaluation_prompt = f"""
請評估以下RAG系統回答的品質：

問題: {question}

RAG回答: {rag_answer}

請從以下四個維度評分（0.0-1.0）：

1. 技術準確性 (technical_accuracy): 回答的技術內容是否正確
2. 完整性 (completeness): 回答是否完整回應了問題
3. 清晰度 (clarity): 回答是否清晰易懂
4. 相關性 (relevance): 回答是否與問題相關

請以JSON格式回應：
{{
    "technical_accuracy": 0.8,
    "completeness": 0.7,
    "clarity": 0.9,
    "relevance": 0.8,
    "overall_score": 0.8,
    "feedback": "評估說明"
}}
"""

            # 使用 Bedrock Claude 進行評估
            if hasattr(self, 'bedrock_client'):
                response = self.bedrock_client.messages.create(
                    model=self.bedrock_model,
                    max_tokens=1000,
                    messages=[{
                        "role": "user",
                        "content": evaluation_prompt
                    }]
                )

                # 解析回應
                evaluation_text = response.content[0].text

                # 提取 JSON
                import json
                import re
                json_match = re.search(r'\{.*\}', evaluation_text, re.DOTALL)
                if json_match:
                    evaluation_data = json.loads(json_match.group())

                    return {
                        'technical_accuracy': float(evaluation_data.get('technical_accuracy', 0.0)),
                        'completeness': float(evaluation_data.get('completeness', 0.0)),
                        'clarity': float(evaluation_data.get('clarity', 0.0)),
                        'image_reference': 0.0,  # 無圖片模式固定為 0
                        'overall_score': float(evaluation_data.get('overall_score', 0.0)),
                        'feedback': evaluation_data.get('feedback', '')
                    }
                else:
                    print("⚠️ 無法解析評估結果")
                    return self._get_default_evaluation_no_image()
            else:
                # 使用簡化評估
                return self._evaluate_answer_simple(question, rag_answer)

        except Exception as e:
            print(f"⚠️ 無圖片評估失敗: {e}")
            return self._get_default_evaluation_no_image()

    def _get_default_evaluation_no_image(self) -> Dict[str, float]:
        """獲取預設評估結果（無圖片版本）"""
        return {
            'technical_accuracy': 0.5,
            'completeness': 0.5,
            'clarity': 0.5,
            'image_reference': 0.0,
            'overall_score': 0.5,
            'feedback': '評估失敗，使用預設分數'
        }

    def calculate_test_cost(self, question_tokens: float, answer_tokens: float, evaluation_tokens: float) -> Dict[str, float]:
        """計算測試成本"""
        try:
            # 使用 CostCalculator 計算成本
            claude_question_cost = 0.0  # 無圖片模式沒有問題生成成本
            claude_evaluation_cost = CostCalculator.calculate_claude_cost("", "x" * int(evaluation_tokens))
            openai_rag_cost = CostCalculator.calculate_openai_cost("x" * int(question_tokens), "x" * int(answer_tokens))

            total_cost = claude_question_cost + claude_evaluation_cost + openai_rag_cost

            return {
                'claude_question_cost': claude_question_cost,
                'claude_evaluation_cost': claude_evaluation_cost,
                'openai_rag_cost': openai_rag_cost,
                'total_cost': total_cost
            }
        except Exception as e:
            logger.error(f"成本計算失敗: {e}")
            return {
                'claude_question_cost': 0.0,
                'claude_evaluation_cost': 0.0,
                'openai_rag_cost': 0.0,
                'total_cost': 0.0
            }
