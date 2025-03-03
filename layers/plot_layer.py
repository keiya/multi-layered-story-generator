from typing import Optional
from utils import call_llm

def plot_layer(user_input: str) -> str:
    """
    Plot Layer:
    ユーザーは LLM に大まかな物語の世界観、設定、価値観等を入力する。
    LLM はプロンプトと入力に従い、ワンレスポンス程度で収まるが、
    物語を要約できるほどの適度な長さのマスタープロット(登場人物、設定、価値観も含める)を生成する。

    Args:
        user_input (str): 大まかな物語の世界観、設定、価値観等

    Returns:
        str: master_plot (登場人物、設定、価値観を含むマスタープロット)
    """
    prompt = f"""
    あなたは多層的物語生成システムの一部として、物語のマスタープロットを生成する専門家です。
    以下のユーザー設定に基づいて、物語の全体的なマスタープロットを生成してください。

    # ユーザー設定
    {user_input}

    # 指示
    以下の要素を含む、一貫性のあるマスタープロットを生成してください：
    1. 主要な登場人物（2-5人程度）- それぞれの特徴や動機
    2. 物語の舞台となる世界観や設定
    3. 物語のテーマと中心的な価値観
    4. 主要な物語の展開（始まり、中間、終わり）
    5. 主要な対立や葛藤

    マスタープロットは、後続の処理で物語を展開するための基盤となります。
    物語全体を要約できる程度の詳細さを持ちつつも、1つのレスポンスに収まる適度な長さ（約500-1000文字）にしてください。
    """
    
    master_plot = call_llm(prompt)
    return master_plot 
