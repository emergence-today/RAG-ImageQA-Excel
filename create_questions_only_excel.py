#!/usr/bin/env python3
"""
生成只有問題的 Excel 文件（無圖片模式）
"""

import pandas as pd

def create_questions_only_excel():
    """創建只包含問題的 Excel 文件"""
    
    # 只有問題的測試數據
    questions_data = {
        'question': [
            '什麼是焊接式連接器？它的主要特點和應用場景是什麼？',
            '除了PCB板以外，電子產品中還有哪些重要的材料？請詳細說明。',
            '連接器有哪些不同的分類方式？每種類型有什麼特點？',
            '電子材料的選擇需要考慮哪些因素？',
            '導電材料和絕緣材料在電子產品中如何配合使用？',
            '什麼是Housing材料？它在電子產品中的作用是什麼？',
            '電子連接器的可靠性如何保證？有哪些測試方法？',
            '現代電子產品對材料有哪些新的要求？'
        ]
    }
    
    # 創建 DataFrame
    df = pd.DataFrame(questions_data)
    
    # 保存為 Excel 文件
    filename = 'questions_only.xlsx'
    df.to_excel(filename, index=False, engine='openpyxl')
    
    print(f"✅ 純問題 Excel 文件已創建: {filename}")
    print(f"📊 包含 {len(df)} 個問題")
    
    # 顯示內容預覽
    print("\n📋 問題列表:")
    print("=" * 80)
    for i, question in enumerate(df['question'], 1):
        print(f"{i:2d}. {question}")
    
    return filename

def create_simple_questions_excel():
    """創建簡單的問題 Excel（用於快速測試）"""
    
    simple_questions = {
        'question': [
            '什麼是連接器？',
            'PCB板的作用是什麼？',
            '電子材料有哪些類型？'
        ]
    }
    
    df = pd.DataFrame(simple_questions)
    filename = 'simple_questions.xlsx'
    df.to_excel(filename, index=False, engine='openpyxl')
    
    print(f"✅ 簡單問題 Excel 文件已創建: {filename}")
    print(f"📊 包含 {len(df)} 個問題")
    
    return filename

if __name__ == "__main__":
    print("🚀 創建純問題 Excel 文件")
    print("=" * 50)
    
    # 創建完整問題文件
    full_file = create_questions_only_excel()
    
    print("\n" + "=" * 50)
    
    # 創建簡單問題文件
    simple_file = create_simple_questions_excel()
    
    print("\n✨ 完成！")
    print("💡 使用說明:")
    print(f"   - {simple_file}: 快速測試用（3個問題）")
    print(f"   - {full_file}: 完整測試用（8個問題）")
    print("   - 這些文件只包含問題，會使用 RAG 系統直接回答")
