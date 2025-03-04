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
    Section Layerで生成したセクションプロットをベースに、段落単位で物語を肉付けする。
    
    処理の流れ:
    1. 入力として受け取ったsection_plotをベースに、paragraph_intentとtimelineデータを参考にする
    2. 前回までの段落との連続性を保ちながら、新しい段落のテキストを生成
    3. 次の段落への意図も一緒に生成
    4. 生成された段落テキストと意図をモックファイルに保存（テスト用）
    
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
        
    Raises:
        ValueError: JSONパースエラーやレスポンス形式が不正な場合
    """
    if previous_paragraphs is None:
        previous_paragraphs = []
    
    # 現在の段落番号を特定
    current_paragraph_index = len(previous_paragraphs)
    
    # タイムラインデータの準備
    timeline_str = json.dumps(all_characters_timeline, ensure_ascii=False, indent=2)
    # タイムラインが複雑すぎる場合は、最新のエントリだけを使用
    if len(timeline_str) > 4000:  # 文字数制限を設ける
        timeline_str = json.dumps(all_characters_timeline[-1] if all_characters_timeline else {}, ensure_ascii=False, indent=2)
    
    # 前回の段落内容を文字列化（最新の3つだけ使用）
    previous_paragraphs_str = ""
    if previous_paragraphs:
        # 最新の3つの段落だけを使用
        recent_paragraphs = previous_paragraphs[-3:] if len(previous_paragraphs) > 3 else previous_paragraphs
        for i, paragraph in enumerate(recent_paragraphs):
            paragraph_number = current_paragraph_index - len(recent_paragraphs) + i + 1
            previous_paragraphs_str += f"\n\nParagraph {paragraph_number}:\n{paragraph}"
    
    # プロンプトの構築
    prompt = f"""
    # 段落生成タスク
    
    あなたは物語の段落を生成するアシスタントです。セクションプロットをより詳細に肉付けし、流れるような自然な段落テキストを作成してください。

    ## 入力情報

    [マスタープロット]
    {master_plot}

    [世界観設定]
    {backstories}

    [キャラクター設定]
    {characters}

    [キャラクタータイムライン]
    {timeline_str}

    [現在のセクションプロット]
    {section_plot}

    [これまでの段落]
    {previous_paragraphs_str if previous_paragraphs_str else "まだ段落は生成されていません。"}
    
    {f"[前回の段落意図]\n{previous_paragraph_intent}" if previous_paragraph_intent else ""}

    ## 指示
    セクションプロットを元に、段落{current_paragraph_index + 1}のテキストを詳細に作成してください。
    これは物語の一部として読者に提示される実際のテキストです。
    
    1. 流れるような自然な文章で、小説の1パートとして読めるようなクオリティで書いてください
    2. 前の段落から自然に続くようにしてください。つながりを意識しましょう
    3. 文体は一貫して、物語世界に没入できるような表現を心がけてください
    4. 必要に応じて会話や内的独白、ナレーションをバランスよく含めてください
    5. キャラクターの感情や思考、周囲の環境描写なども含めると良いでしょう
    
    ## 出力形式
    JSONフォーマットで以下の2つの部分を出力してください：

    {
        "paragraph": "物語の一部分としての段落テキスト",
        "paragraph_intent": "次の段落でどのように物語を展開したいかの簡潔な意図"
    }
    """
    
    # LLMを呼び出して段落を生成
    try:
        response = call_llm(prompt, json_mode=True)
        
        # 最終的な応答からパラグラフと意図を抽出
        paragraph, paragraph_intent = extract_paragraph_and_intent(response)
        
        # For debugging only - this will be removed in production
        # save_paragraph_to_mock_files(paragraph, paragraph_intent, current_paragraph_index)
        
        return paragraph, paragraph_intent
    except ValueError as e:
        print(f"段落生成中にエラーが発生しました: {e}")
        raise


def extract_paragraph_and_intent(response: str) -> Tuple[str, str]:
    """
    LLMのレスポンスから段落と段落意図を抽出する
    
    Args:
        response (str): LLMからのレスポンス（JSON形式）
        
    Returns:
        Tuple[str, str]: 段落と段落の意図
        
    Raises:
        ValueError: JSONパースエラーやレスポンス形式が不正な場合
    """
    try:
        # JSON形式のレスポンスをパース
        data = json.loads(response)
        
        # キーからデータを取得
        paragraph = data.get("paragraph", "")
        paragraph_intent = data.get("paragraph_intent", "")
        
        # キーが存在しない、または値が空の場合はエラーを発生
        if not paragraph:
            raise ValueError("'paragraph' が見つからないか空です")
        if not paragraph_intent:
            raise ValueError("'paragraph_intent' が見つからないか空です")
            
    except json.JSONDecodeError as e:
        # JSONパースに失敗した場合は例外を投げる
        raise ValueError(f"JSONパースに失敗しました: {e}\nレスポンス: {response[:100]}...")
    
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
