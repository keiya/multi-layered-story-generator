from typing import List, Dict, Any, Optional, Tuple
import json
import os
from utils import call_llm

def section_layer(
    master_plot: str,
    backstories: str,
    characters: str,
    all_characters_timeline: List[Dict[str, Any]],
    chapter_plot: str,
    previous_sections: Optional[List[str]] = None,
    previous_section_intent: Optional[str] = None
) -> Tuple[str, str]:
    """
    Section Layer:
    Chapter Layerで生成したチャプタープロットをベースに、セクション単位で物語を肉付けする。
    
    処理の流れ:
    1. 入力として受け取ったchapter_plotをベースに、section_intentとtimelineデータを参考にする
    2. 前回までのセクションとの連続性を保ちながら、新しいセクションのプロットを生成
    3. 次のセクションへの意図も一緒に生成
    4. 生成されたセクションプロットとインテントをモックファイルに保存（テスト用）
    
    Args:
        master_plot (str): マスタープロット
        backstories (str): 世界観の設定
        characters (str): キャラクターの設定
        all_characters_timeline (List[Dict[str, Any]]): すべてのキャラクターのタイムライン
        chapter_plot (str): 現在処理中のチャプタープロット
        previous_sections (Optional[List[str]]): 前回までに生成したセクションのリスト
        previous_section_intent (Optional[str]): 前回のセクションの意図
        
    Returns:
        Tuple[str, str]: セクションプロットとセクションの意図
        
    Raises:
        ValueError: JSONパースエラーやレスポンス形式が不正な場合
    """
    if previous_sections is None:
        previous_sections = []
    
    # 現在のセクション番号を特定
    current_section_index = len(previous_sections)
    
    # タイムラインデータの準備
    timeline_str = json.dumps(all_characters_timeline, ensure_ascii=False, indent=2)
    # タイムラインが複雑すぎる場合は、最新のエントリだけを使用
    if len(timeline_str) > 4000:  # 文字数制限を設ける
        timeline_str = json.dumps(all_characters_timeline[-1] if all_characters_timeline else {}, ensure_ascii=False, indent=2)
    
    # 前回のセクション内容を文字列化
    previous_sections_str = ""
    if previous_sections:
        for i, section in enumerate(previous_sections):
            previous_sections_str += f"\n\nSection {i+1}:\n{section}"
    
    # プロンプトの構築
    prompt = f"""
    # セクション生成タスク
    
    あなたは物語のセクションを生成するアシスタントです。チャプターのプロットをより詳細に肉付けし、物語性のある具体的なセクションプロットを作成してください。

    ## 入力情報

    [マスタープロット]
    {master_plot}

    [世界観設定]
    {backstories}

    [キャラクター設定]
    {characters}

    [キャラクタータイムライン]
    {timeline_str}

    [現在のチャプタープロット]
    {chapter_plot}

    [これまでのセクション]
    {previous_sections_str if previous_sections_str else "まだセクションは生成されていません。"}
    
    {f"[前回のセクション意図]\n{previous_section_intent}" if previous_section_intent else ""}

    ## 指示
    チャプタープロットを元に、セクション{current_section_index + 1}のプロットを詳細に作成してください。
    各セクションは物語の一区切りとなるまとまりで、一つの場面や時間帯、あるいは特定のイベントに焦点を当てます。
    
    1. このセクションで起こる主要な出来事、登場するキャラクター、彼らの会話や行動、感情の変化などを詳細に含めてください。
    2. 時系列、場所の描写、キャラクターの動きが明確になるように記述してください。
    3. チャプターの全体的なテーマを保ちながら、物語を進展させてください。
    4. 前のセクションとの連続性を保ち、自然な流れを作りましょう。
    
    ## 出力形式
    JSONフォーマットで以下の2つの部分を出力してください：

    {
        "section_plot": "詳細な物語の一部分としてのプロット。500-1000語程度。",
        "section_intent": "次のセクションでどのように物語を展開したいかの簡潔な意図（100-200語程度）"
    }
    """
    
    # LLMを呼び出してセクションを生成（JSONモードを有効化）
    response = call_llm(prompt, json_mode=True)
    
    # 最終的な応答からセクションプロットと意図を抽出
    section_plot, section_intent = extract_plot_and_intent(response)
    
    # For debugging only - this will be removed in production
    # save_section_to_mock_files(section_plot, section_intent, current_section_index)
    
    return section_plot, section_intent


def extract_plot_and_intent(response: str) -> Tuple[str, str]:
    """
    LLMのレスポンスからセクションプロットとセクション意図を抽出する
    
    Args:
        response (str): LLMからのレスポンス（JSON形式）
        
    Returns:
        Tuple[str, str]: セクションプロットとセクション意図
    """
    try:
        # JSON形式のレスポンスをパース
        data = json.loads(response)
        
        # キーからデータを取得
        section_plot = data.get("section_plot", "")
        section_intent = data.get("section_intent", "")
        
        # キーが存在しない、または値が空の場合はエラーを発生
        if not section_plot:
            raise ValueError("'section_plot' が見つからないか空です")
        if not section_intent:
            raise ValueError("'section_intent' が見つからないか空です")
            
    except json.JSONDecodeError as e:
        # JSONパースに失敗した場合は例外を投げる
        raise ValueError(f"JSONパースに失敗しました: {e}\nレスポンス: {response[:100]}...")
    
    return section_plot, section_intent

# Function to be removed as file saving will be centralized in main.py
# def save_section_to_mock_files(section_plot: str, section_intent: str, section_index: int) -> None:
#     """
#     生成されたセクションプロットとインテントをモックファイルに保存する
#     
#     Args:
#         section_plot (str): セクションプロット
#         section_intent (str): セクション意図
#         section_index (int): セクションのインデックス（0から始まる）
#     """
#     # セクションプロットを保存
#     try:
#         with open(f"section{section_index + 1}-plot-mock.txt", 'w', encoding='utf-8') as f:
#             f.write(section_plot)
#         print(f"セクション{section_index + 1}のプロットを section{section_index + 1}-plot-mock.txt に保存しました")
#     except Exception as e:
#         print(f"プロットファイルへの書き込み中にエラーが発生しました: {e}")
#     
#     # セクション意図を保存
#     try:
#         with open(f"section{section_index + 1}-intent-mock.txt", 'w', encoding='utf-8') as f:
#             f.write(section_intent)
#         print(f"セクション{section_index + 1}の意図を section{section_index + 1}-intent-mock.txt に保存しました")
#     except Exception as e:
#         print(f"意図ファイルへの書き込み中にエラーが発生しました: {e}")
#     
#     # セクション全体（プロットと意図を両方含む）を保存
#     try:
#         with open(f"section{section_index + 1}-mock.txt", 'w', encoding='utf-8') as f:
#             f.write(f"# セクションプロット\n{section_plot}\n\n# セクション意図\n{section_intent}")
#         print(f"セクション{section_index + 1}の全体を section{section_index + 1}-mock.txt に保存しました")
#     except Exception as e:
#         print(f"全体ファイルへの書き込み中にエラーが発生しました: {e}") 
