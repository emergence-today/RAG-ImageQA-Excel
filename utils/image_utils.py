#!/usr/bin/env python3
"""
圖片處理工具模組
"""

import os
import base64
from pathlib import Path
from typing import Dict, List
from PIL import Image
import io

class ImageProcessor:
    """圖片處理器"""
    
    @staticmethod
    def get_image_categories(image_dir: str) -> Dict[str, List[str]]:
        """獲取圖片目錄中的所有類別和圖片"""
        categories = {}

        if not os.path.exists(image_dir):
            print(f"❌ 圖片目錄不存在: {image_dir}")
            return categories

        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}

        # 先檢查根目錄下的圖片
        root_images = []
        for file in os.listdir(image_dir):
            file_path = os.path.join(image_dir, file)
            if os.path.isfile(file_path) and Path(file).suffix.lower() in image_extensions:
                root_images.append(file_path)

        # 如果根目錄有圖片，按檔名前綴分類
        if root_images:
            # 按檔名前綴分類（例如：1.0LVDS, 1.1Cable, 2.0常规 等）
            prefix_categories = {}
            for image_path in root_images:
                filename = Path(image_path).name

                # 根據檔名模式進行詳細分類
                import re
                category = "其他圖片"  # 預設類別

                # 根據不同的檔名模式分類
                if re.match(r'^1\.0', filename):
                    category = "1.0_LVDS線束加工"
                elif re.match(r'^1\.1', filename):
                    category = "1.1_Cable設計規範"
                elif re.match(r'^1\.2', filename):
                    category = "1.2_Wire_Harness製程"
                elif re.match(r'^1\.3', filename):
                    category = "1.3_WH線束加工"
                elif re.match(r'^1\.4', filename):
                    category = "1.4_FFC設計規範"
                elif re.match(r'^1\.★', filename):
                    category = "1.★_Cable產品設計規範"
                elif re.match(r'^2\.0', filename):
                    category = "2.0_外部線設計參考"
                elif re.match(r'^2\.1', filename):
                    category = "2.1_EC產品工藝"
                elif re.match(r'^2\.2', filename):
                    category = "2.2_外部線應用"
                elif re.match(r'^2\.3', filename):
                    category = "2.3_EC產品工藝簡報"
                elif re.match(r'^3\.0', filename):
                    category = "3.0_汽車電線技術條件"
                elif re.match(r'^3\.1', filename):
                    category = "3.1_AT-Cable設計規範"
                elif re.match(r'^QSA', filename):
                    category = "QSA稽核條款"
                elif re.match(r'^Wire', filename):
                    category = "Wire_Harness介紹"
                elif re.match(r'^cable', filename):
                    category = "Cable內訓"
                elif re.match(r'^圖面識別', filename):
                    category = "圖面識別教材"
                elif re.match(r'^材料', filename):
                    category = "材料介紹"
                elif re.match(r'^生產線', filename):
                    category = "生產線學習"
                elif re.match(r'^客戶', filename):
                    category = "客戶管理"
                elif re.match(r'^合同', filename):
                    category = "合同評審"
                elif re.match(r'^產品', filename):
                    category = "產品設計變更"
                elif re.match(r'^識圖', filename):
                    category = "識圖指南"
                elif re.match(r'^清單', filename):
                    category = "清單文件"

                if category not in prefix_categories:
                    prefix_categories[category] = []
                prefix_categories[category].append(image_path)

            # 將分類結果加入 categories
            for category, images in prefix_categories.items():
                categories[category] = sorted(images)

        # 然後檢查子目錄
        for root, dirs, files in os.walk(image_dir):
            # 跳過根目錄，只處理子目錄
            if root == image_dir:
                continue

            category = os.path.basename(root)
            image_files = []

            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    image_path = os.path.join(root, file)
                    image_files.append(image_path)

            if image_files:
                categories[category] = sorted(image_files)

        return categories
    
    @staticmethod
    def encode_image_to_base64(image_path: str, max_size: tuple = (600, 400), quality: int = 60) -> str:
        """將圖片編碼為 base64 用於 HTML 嵌入"""
        try:
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

                # 保存到內存中
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
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
                file_size = os.path.getsize(image_path)
                if file_size > 500 * 1024:  # 500KB限制
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
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """驗證圖片是否有效"""
        try:
            if not os.path.exists(image_path):
                return False
            
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_image_info(image_path: str) -> Dict[str, any]:
        """獲取圖片資訊"""
        try:
            if not os.path.exists(image_path):
                return {}
            
            with Image.open(image_path) as img:
                return {
                    'filename': Path(image_path).name,
                    'size': img.size,
                    'mode': img.mode,
                    'format': img.format,
                    'file_size': os.path.getsize(image_path)
                }
        except Exception as e:
            return {'error': str(e)}
