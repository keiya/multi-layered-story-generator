from typing import List, Dict, Any, Optional, Tuple
import json
import os
from utils import call_llm

def paragraph_layer(
    master_plot: str,
    backstories: str,
    characters: str,
    all_characters_timeline: List[Dict[str, Any]],
    section_plot: str,
    previous_paragraphs: Optional[List[str]] = None,
    previous_paragraph_intent: Optional[str] = None
) -> Tuple[str, str]:
    """
    Paragraph Layer:
    Section Layerで生成したセクションプロットをベースに、段落単位で物語を展開する。
    
    処理の流れ:
    1. 入力として受け取ったsection_plotをベースに、paragraph_intentとtimelineデータを参考にする
    2. 前回までの段落との連続性を保ちながら、新しい段落を生成
    3. 次の段落への意図も一緒に生成
    4. 生成された段落と意図をモックファイルに保存（テスト用）
    
    特徴:
    - 最大3つ前までの段落を参照して連続性を保つ
    - 段落ごとに細かいストーリー展開が可能
    - 節をまたいでも段落の連続性を維持
    
    Args:
        master_plot (str): マスタープロット
        backstories (str): 世界観の設定
        characters (str): キャラクターの設定
        all_characters_timeline (List[Dict[str, Any]]): すべてのキャラクターのタイムライン
        section_plot (str): 現在処理中のセクションプロット
        previous_paragraphs (Optional[List[str]]): 前回までに生成した段落のリスト
        previous_paragraph_intent (Optional[str]): 前回の段落の意図
        
    Returns:
        Tuple[str, str]: 段落と段落の意図
    """
    if previous_paragraphs is None:
        previous_paragraphs = []
    
    # 現在の段落番号を特定
    current_paragraph_index = len(previous_paragraphs)
    
    # 参照する段落は最大3つ前まで
    ref_paragraphs = previous_paragraphs[-3:] if previous_paragraphs else []
    
    # 参照する段落を文字列化
    ref_paragraphs_str = ""
    if ref_paragraphs:
        for i, para in enumerate(ref_paragraphs):
            # 何番目の段落かを計算（例：現在の段落が5番目なら、参照するのは2, 3, 4番目）
            para_num = current_paragraph_index - len(ref_paragraphs) + i + 1
            ref_paragraphs_str += f"\n\n段落 {para_num}:\n{para}"
    
    # タイムラインデータの準備（複雑すぎる場合は最新のエントリのみ使用）
    timeline_str = json.dumps(all_characters_timeline[-1] if all_characters_timeline else {}, ensure_ascii=False, indent=2)
    
    # プロンプトの構築
    prompt = f"""
    # 段落生成タスク
    
    あなたは物語の段落を生成するアシスタントです。セクションプロットをベースに、前の段落との連続性を保ちながら次の段落を作成してください。

    ## 入力情報

    [マスタープロット]
    {master_plot}

    [世界観設定]
    {backstories}

    [キャラクター設定]
    {characters}

    [キャラクタータイムライン]
    {timeline_str}

    [セクションプロット]
    {section_plot}

    [前の段落]
    {ref_paragraphs_str if ref_paragraphs_str else "まだ段落は生成されていません。この段落が最初の段落です。"}
    
    {f"[前回の段落意図]\n{previous_paragraph_intent}" if previous_paragraph_intent else ""}

    ## 指示
    セクションプロットと前の段落を元に、段落{current_paragraph_index + 1}を作成してください。
    
    1. 前の段落との自然な連続性を持たせてください
    2. 会話、描写、行動などをバランスよく含めてください
    3. 1段落あたり100〜300語程度で書いてください
    4. セクションプロットの一部だけに焦点を当て、細部を掘り下げてください
    5. 登場人物の感情や思考、周囲の環境描写なども含めると良いでしょう
    
    ## 出力形式
    以下の2つの部分を出力してください：

    1. 段落（必須）: 物語の一部分としての段落テキスト
    2. 段落意図（必須）: 次の段落でどのように物語を展開したいかの簡潔な意図
    
    出力例：
    
    # 段落
    （ここに段落テキストを書く）
    
    # 段落意図
    （ここに次の段落への意図を書く）
    """
    
    # LLMを呼び出して段落を生成
    response = call_llm(prompt)
    
    # 最終的な応答からパラグラフと意図を抽出
    paragraph, paragraph_intent = extract_paragraph_and_intent(response)
    
    # For debugging only - this will be removed in production
    # save_paragraph_to_mock_files(paragraph, paragraph_intent, current_paragraph_index)
    
    return paragraph, paragraph_intent


def extract_paragraph_and_intent(response: str) -> Tuple[str, str]:
    """
    LLMのレスポンスから段落と段落意図を抽出する
    
    Args:
        response (str): LLMからのレスポンス
        
    Returns:
        Tuple[str, str]: 段落と段落の意図
    """
    # デフォルト値を設定
    paragraph = ""
    paragraph_intent = ""
    
    # 段落と意図の抽出
    para_marker = "# 段落"
    intent_marker = "# 段落意図"
    
    if para_marker in response and intent_marker in response:
        # 両方のマーカーが見つかった場合、その間のテキストを抽出
        para_start = response.find(para_marker) + len(para_marker)
        intent_start = response.find(intent_marker)
        paragraph = response[para_start:intent_start].strip()
        paragraph_intent = response[intent_start + len(intent_marker):].strip()
    else:
        # マーカーが見つからない場合、テキストを半分に分割して割り当て
        lines = response.strip().split('\n')
        mid_point = len(lines) // 2
        paragraph = '\n'.join(lines[:mid_point]).strip()
        paragraph_intent = '\n'.join(lines[mid_point:]).strip()
        
        # それでも抽出できなかった場合はレスポンス全体を段落とし、
        # 意図はデフォルト値を使用
        if not paragraph:
            paragraph = response.strip()
            paragraph_intent = "次の段落では、この流れを継続して展開します。"
    
    return paragraph, paragraph_intent

# Function to be removed as file saving will be centralized in main.py
# def save_paragraph_to_mock_files(paragraph: str, paragraph_intent: str, paragraph_index: int) -> None:
#     """
#     生成された段落と意図をモックファイルに保存する
#     
#     Args:
#         paragraph (str): 段落テキスト
#         paragraph_intent (str): 段落意図
#         paragraph_index (int): 段落のインデックス（0から始まる）
#     """
#     # 段落を保存
#     try:
#         with open(f"paragraph{paragraph_index + 1}-mock.txt", 'w', encoding='utf-8') as f:
#             f.write(paragraph)
#         print(f"段落{paragraph_index + 1}を paragraph{paragraph_index + 1}-mock.txt に保存しました")
#     except Exception as e:
#         print(f"段落ファイルへの書き込み中にエラーが発生しました: {e}")
#     
#     # 段落意図を保存
#     try:
#         with open(f"paragraph{paragraph_index + 1}-intent-mock.txt", 'w', encoding='utf-8') as f:
#             f.write(paragraph_intent)
#         print(f"段落{paragraph_index + 1}の意図を paragraph{paragraph_index + 1}-intent-mock.txt に保存しました")
#     except Exception as e:
#         print(f"意図ファイルへの書き込み中にエラーが発生しました: {e}")

# ... existing code ... 
