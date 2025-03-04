from typing import Optional, Tuple, List
import json
from utils import call_llm

def chapter_layer(
    master_plot: str,
    backstories: str,
    characters: str,
    chapter_index: int,
    previous_chapter_plots: Optional[List[str]] = None,
    previous_chapter_intents: Optional[List[str]] = None,
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
        chapter_index (int): 現在の章番号（0始まり）
        previous_chapter_plots (Optional[List[str]]): これまでの全ての章のプロットのリスト
        previous_chapter_intents (Optional[List[str]]): これまでの全ての章の意図のリスト
        is_final_chapter (bool): 最終章かどうか
        
    Returns:
        Tuple[str, str]: 章のプロットと章の意図
        
    Raises:
        ValueError: JSONパースエラーやレスポンス形式が不正な場合
    """
    # 人間が読むための章番号（1始まり）
    chapter_number = chapter_index + 1
    
    # 最終章用の特別な指示
    final_chapter_instruction = ""
    if is_final_chapter:
        final_chapter_instruction = """
        これは物語の最終章です。すべての物語の主要な要素を解決し、適切な結末に導いてください。
        オープンエンドにせず、明確な終わりをつけてください。
        """
    
    # これまでの章の情報を生成
    previous_chapters_info = ""
    if previous_chapter_plots and len(previous_chapter_plots) > 0:
        previous_chapters_info += "# これまでの章のプロット\n"
        for i, plot in enumerate(previous_chapter_plots):
            previous_chapters_info += f"## 第{i+1}章\n{plot}\n\n"
    
    if previous_chapter_intents and len(previous_chapter_intents) > 0:
        previous_chapters_info += "# これまでの章の意図\n"
        for i, intent in enumerate(previous_chapter_intents):
            previous_chapters_info += f"## 第{i+1}章の意図\n{intent}\n\n"
    
    # プロンプトの構築
    prompt = f"""
    # チャプター生成タスク
    
    あなたは物語の章を生成するアシスタントです。マスタープロットを元に、今回の章のプロットを詳細に作成してください。
    
    ## 入力情報:
    
    # マスタープロット
    {master_plot}
    
    # 世界観設定
    {backstories}
    
    # キャラクター設定
    {characters}

    {previous_chapters_info}

    # 指示
    第{chapter_number}章のプロット（chapter_plot）と、この章から物語を今後どう進めるかの意図（chapter_intent）を生成してください。
    {final_chapter_instruction}
    
    ## 制約条件:
    1. 章のプロットは、マスタープロットのストーリーラインに沿ったものであること
    2. キャラクターの行動や動機は、設定された性格と一致していること
    3. 世界観の設定と矛盾しないこと
    4. プロットは十分な詳細を含み、章の要約として機能すること
    5. この章で起こる主要なイベント、キャラクターの行動、設定の変化を明確に記述すること
    6. これまでの章と自然につながるストーリーを作成すること
    
    ## 出力形式:
    JSONフォーマットで以下の情報を出力してください:

    {{
        "chapter_plot": "第{chapter_number}章のプロット",
        "chapter_intent": "次の章に向けての意図"
    }}
    """
    
    try:
        # LLMを呼び出してJSONモードでレスポンスを取得
        response = call_llm(prompt, json_mode=True)
        
        # JSONからchapter_plotとchapter_intentを抽出
        data = json.loads(response)
        chapter_plot = data.get("chapter_plot", "")
        chapter_intent = data.get("chapter_intent", "")
        
        # 値の検証
        if not chapter_plot:
            raise ValueError("'chapter_plot'が見つからないか空です")
        if not chapter_intent:
            raise ValueError("'chapter_intent'が見つからないか空です")
    
    except json.JSONDecodeError as e:
        # JSONパースに失敗した場合
        raise ValueError(f"JSONパースに失敗しました: {e}\nレスポンス: {response[:100]}...")
    except ValueError as e:
        # 値が不正な場合
        raise ValueError(f"レスポンスの値が不正です: {e}")
    except Exception as e:
        # その他のエラー
        raise ValueError(f"チャプター生成中に予期しないエラーが発生しました: {e}")
    
    # 最終章の場合は、章の意図を物語の終了を示すものに
    if is_final_chapter:
        chapter_intent = "物語はここで完結しました。"
    
    return chapter_plot, chapter_intent 
