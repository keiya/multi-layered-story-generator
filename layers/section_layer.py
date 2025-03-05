from typing import List, Dict, Any, Optional, Tuple
import json
import os
from utils import call_llm

import pprint
pp = pprint.PrettyPrinter(indent=4)

def section_layer(
    master_plot: str,
    backstories: str,
    characters: str,
    all_characters_timeline: List[Dict[str, Any]],
    chapter_plot: str,
    previous_sections: Optional[List[str]] = None,
    previous_section_intent: Optional[str] = None,
    all_previous_sections: Optional[List[List[str]]] = None,  # 新規: 全章の全セクションのリスト
    remaining_chapter_plots: Optional[List[str]] = None  # 新規: まだセクション化されていない章のプロット
) -> Tuple[str, str]:
    """
    Section Layer:
    Chapter で生成したプロットを節ごとに分割し、節ごとに物語を生成するレイヤー。
    
    Args:
        master_plot (str): Plot Layer で生成されたマスタープロット
        backstories (str): Backstory Layer で生成された背景設定
        characters (str): Character Layer で生成されたキャラクター設定
        all_characters_timeline (List[Dict[str, Any]]): これまでの全ての章のタイムラインのリスト
        chapter_plot (str): 現在の章のプロット
        previous_sections (Optional[List[str]]): 現在の章でこれまでに生成された節のリスト
        previous_section_intent (Optional[str]): 直前の節の意図
        all_previous_sections (Optional[List[List[str]]]): これまでの全ての章の全ての節のリスト
        remaining_chapter_plots (Optional[List[str]]): まだ節に展開されていない章のプロットのリスト
        
    Returns:
        Tuple[str, str]: 節のプロットと次の節に向けての意図
    """
    # セクションの生成準備
    current_section_index = 0 if not previous_sections else len(previous_sections)
    
    # 前のセクションの情報を生成
    previous_sections_info = ""
    if previous_sections and len(previous_sections) > 0:
        previous_sections_info = "# 現在の章における前のセクション\n"
        for i, section in enumerate(previous_sections):
            previous_sections_info += f"## セクション{i+1}\n{section}\n\n"
    
    # タイムライン情報を現在の章のみにフィルタリング
    timeline_info = "# タイムライン情報\n"
    if all_characters_timeline and len(all_characters_timeline) > 0:
        # 最新のタイムラインを取得（現在の章までのタイムライン）
        latest_timeline = all_characters_timeline[-1]
        
        for character, events in latest_timeline.items():
            timeline_info += f"## {character}のタイムライン\n"
            for date, event in events.items():
                timeline_info += f"- {date}: {event}\n"
            timeline_info += "\n"

    # 全ての過去のセクションとまだセクション化されていない章の情報を生成（新規）
    all_content_info = ""
    
    # 1. 過去の章のセクション
    if all_previous_sections and len(all_previous_sections) > 0:
        all_content_info += "# これまでの章のセクション\n"
        for chapter_idx, chapter_sections in enumerate(all_previous_sections):
            all_content_info += f"## 第{chapter_idx+1}章\n"
            for section_idx, section in enumerate(chapter_sections):
                all_content_info += f"### セクション{section_idx+1}\n{section}\n\n"
    
    # 2. まだセクション化されていない章のプロット
    if remaining_chapter_plots and len(remaining_chapter_plots) > 0:
        all_content_info += "# 今後の章のプロット\n"
        start_idx = 0 if not all_previous_sections else len(all_previous_sections) + 1
        for i, plot in enumerate(remaining_chapter_plots):
            chapter_idx = start_idx + i
            all_content_info += f"## 第{chapter_idx}章\n{plot}\n\n"
    
    # プロンプトの構築
    prompt = f"""
    # セクション生成タスク
    
    あなたは物語の節（セクション）を生成するアシスタントです。「現在の章のプロット」を参考に、「現在の章における前のセクション」から物語が繋がるように、「このセクションの意図」を反映した詳細なセクションプロットを作成してください。セクションの意図の範囲内で物語を詳細化し、続きなどは書かないでください。

    {f"[このセクションの意図]\n{previous_section_intent}" if previous_section_intent else ""}

    ## 入力情報:
    
    # マスタープロット
    {master_plot}
    
    # 世界観設定
    {backstories}
    
    # キャラクター設定
    {characters}
    
    # 現在の章のプロット
    {chapter_plot}
    
    {timeline_info}
    
    {previous_sections_info}
    
    {all_content_info}

    ## 指示
    現在の章のプロットを元に、セクション{current_section_index + 1}のプロットを詳細に作成してください。
    
    1. このセクションで起こる主要な出来事、登場するキャラクター、彼らの行動、感情の変化などを詳細に含めてください。
    2. 時系列、場所の描写、キャラクターの動きが明確になるように記述してください。
    3. 現在の章のプロットの全体的なテーマを保ちながら、物語を進展させてください。
    4. 前のセクションとの連続性を保ち、自然な流れを作りましょう。
    
    ## 出力形式
    JSONフォーマットで以下の2つの部分を出力してください：

    {{
        "section_plot": "詳細な物語の一部分としてのプロット。500-1000語程度。",
        "section_intent": "次のセクションでどのように物語を展開したいかの簡潔な意図（100-200語程度）"
    }}
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
            pp.pprint(data)
            raise ValueError("'section_plot' が見つからないか空です")
        if not section_intent:
            pp.pprint(data)
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
