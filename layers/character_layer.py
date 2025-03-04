from typing import Optional
from utils import call_llm

def character_layer(master_plot: str, backstories: str) -> str:
    """
    Character Layer:
    Plot Layer で生成したプロットと Backstory Layer で生成した世界観をベースに
    キャラクターの設定を出力するレイヤー。

    Args:
        master_plot (str): Plot Layer で生成されたマスタープロット
        backstories (str): Backstory Layer で生成された背景設定

    Returns:
        str: characters (キャラクター設定)
    """
    prompt = f"""
    あなたは多層的物語生成システムの一部として、物語のキャラクター設定を生成する専門家です。
    以下のマスタープロットと背景設定に基づいて、物語のキャラクターを詳細に描写してください。

    # マスタープロット
    {master_plot}

    # 背景設定
    {backstories}

    # 指示
    マスタープロットに記載された主要キャラクターとサブキャラクターについて、以下の要素を含む詳細な設定を作成してください：
    1. 外見的特徴 - 年齢、性別、外見、服装など
    2. 性格と内面 - 性格特性、価値観、恐れ、希望など
    3. 背景 - 生い立ち、重要な過去の出来事
    4. 関係性 - 他のキャラクターとの関係
    5. 能力と限界 - 特殊能力、スキル、弱点
    6. 目標と動機 - 短期的・長期的な目標、行動の動機
    7. 成長の可能性 - 物語を通じてどのように変化し得るか

    キャラクター設定は、一貫性があり、深みを持ち、マスタープロットと背景設定の世界観と調和したものにしてください。
    各キャラクターは独自の声や個性を持ち、読者が共感できる存在であるべきです。
    適度な長さ（キャラクターごとに約200-400文字）で、物語を進めるのに十分な詳細を含めてください。
    """
    
    characters = call_llm(prompt)
    return characters 
