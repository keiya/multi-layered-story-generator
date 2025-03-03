from typing import Optional, Tuple
from utils import call_llm

def chapter_layer(
    master_plot: str,
    backstories: str,
    characters: str,
    chapter_index: int,
    previous_chapter_plot: Optional[str] = None,
    previous_chapter_intent: Optional[str] = None,
    is_final_chapter: bool = False
) -> Tuple[str, str]:
    """
    Chapter Layer:
    Plot Layer で生成したプロットを章ごとに分割し、章ごとに物語を生成するレイヤー。
    章を要約できるほどの適度な長さのプロットを生成する。
    
    Args:
        master_plot (str): Plot Layer で生成されたマスタープロット
        backstories (str): Backstory Layer で生成された背景設定
        characters (str): Character Layer で生成されたキャラクター設定
        chapter_index (int): 章のインデックス（0始まり）
        previous_chapter_plot (Optional[str]): 前の章のプロット（1章目の場合はNone）
        previous_chapter_intent (Optional[str]): 前の章の意図（1章目の場合はNone）
        is_final_chapter (bool): この章が最終章かどうか
        
    Returns:
        Tuple[str, str]: (chapter_plot, chapter_intent)
            - chapter_plot: この章のプロット
            - chapter_intent: 物語を今後どう進めるかのメモ（意図）
    """
    # 章番号（表示用）
    chapter_number = chapter_index + 1
    
    # 最終章の場合の追加指示
    final_chapter_instruction = """
    これは物語の最終章です。物語の主要な伏線を回収し、キャラクターの成長を描き、読者に満足感を与える結末を提供してください。
    主要なストーリーラインを解決し、キャラクターの旅の終着点を示し、テーマを明確に反映した終結を描いてください。
    オープンエンドの要素を残すことは構いませんが、主要な葛藤は解決してください。
    """ if is_final_chapter else ""
    
    prompt = f"""
    あなたは多層的物語生成システムの一部として、物語の章ごとのプロットを生成する専門家です。
    以下のマスタープロット、背景設定、キャラクター設定に基づいて、第{chapter_number}章の詳細なプロットを生成してください。

    # マスタープロット
    {master_plot}

    # 背景設定
    {backstories}

    # キャラクター設定
    {characters}

    {f'# 前章のプロット (第{chapter_number-1}章)\n{previous_chapter_plot}\n' if previous_chapter_plot else ''}
    {f'# 前章の意図\n{previous_chapter_intent}\n' if previous_chapter_intent else ''}

    # 指示
    第{chapter_number}章のプロット（chapter_plot）と、この章から物語を今後どう進めるかの意図（chapter_intent）を生成してください。
    {final_chapter_instruction}
    
    ## 制約条件:
    1. 章のプロットは、マスタープロットのストーリーラインに沿ったものであること
    2. キャラクターの行動や動機は、設定された性格と一致していること
    3. 世界観の設定と矛盾しないこと
    4. プロットは十分な詳細を含み、章の要約として機能すること
    5. この章で起こる主要なイベント、キャラクターの行動、設定の変化を明確に記述すること
    
    ## 出力形式:
    以下の形式で出力してください:

    [CHAPTER_PLOT]
    （ここに第{chapter_number}章のプロットを記述）

    [CHAPTER_INTENT]
    （ここに次の章に向けての意図を記述）
    """
    
    response = call_llm(prompt)
    
    # レスポンスから chapter_plot と chapter_intent を抽出
    try:
        # [CHAPTER_PLOT] と [CHAPTER_INTENT] で分割
        parts = response.split('[CHAPTER_PLOT]')
        if len(parts) > 1:
            plot_and_intent = parts[1]
            plot_intent_parts = plot_and_intent.split('[CHAPTER_INTENT]')
            
            if len(plot_intent_parts) > 1:
                chapter_plot = plot_intent_parts[0].strip()
                chapter_intent = plot_intent_parts[1].strip()
            else:
                # 意図の部分が見つからない場合
                chapter_plot = plot_intent_parts[0].strip()
                chapter_intent = f"第{chapter_number}章の続きとして、ストーリーを展開させてください。"
        else:
            # フォーマットに従っていない場合、そのまま使用
            chapter_plot = response
            chapter_intent = f"第{chapter_number}章の続きとして、ストーリーを展開させてください。"
    except Exception as e:
        print(f"Error parsing chapter response: {e}")
        chapter_plot = response
        chapter_intent = f"第{chapter_number}章の続きとして、ストーリーを展開させてください。"
    
    # 最終章の場合は、章の意図を物語の終了を示すものに
    if is_final_chapter:
        chapter_intent = "物語はここで完結しました。"
    
    return chapter_plot, chapter_intent 
