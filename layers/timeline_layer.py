from typing import List, Dict, Any
import json
import os
from utils import call_llm

def timeline_layer(
    master_plot: str,
    backstories: str,
    characters: str,
    chapter_plots: List[str],
    previous_timeline: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Timeline Layer:
    章ごとに各キャラクターのタイムラインを作成・更新する。
    各キャラクターの行動や出来事を日時とともに記録し、物語の時系列を追跡する。
    
    処理の流れ：
    1. 現在処理中のチャプター番号を特定
    2. そのチャプターのプロットを取得
    3. LLMにプロンプトを送信し、タイムラインを生成
    4. JSONをパースし、前回のタイムラインに追加
    5. 結果をモックファイルに保存（テスト用）
    
    各チャプターの後、タイムラインは「章数」の長さの配列となる。
    各インデックスには、そのチャプターまでの全キャラクターの累積タイムラインが含まれる。
    
    出力形式：
    ```json
    [
      { // 1章目の出力
        "キャラクターA": {
          "YYYY-MM-DD HH:MM": "出来事の説明",
          "YYYY-MM-DD HH:MM": "出来事の説明"
        },
        "キャラクターB": {
          "YYYY-MM-DD HH:MM": "出来事の説明"
        }
      },
      { // 2章目の出力（1章目+2章目の累積）
        "キャラクターA": {
          "YYYY-MM-DD HH:MM": "出来事の説明",
          // ... 1章目の内容も保持
          "YYYY-MM-DD HH:MM": "2章目の出来事"
        },
        "キャラクターB": {
          // ... 同様
        }
      }
    ]
    ```
    
    Args:
        master_plot (str): マスタープロット
        backstories (str): 世界観の設定
        characters (str): キャラクターの設定
        chapter_plots (List[str]): これまでに生成された全チャプターのプロット
        previous_timeline (List[Dict[str, Any]]): 前回までに生成されたタイムライン
        
    Returns:
        List[Dict[str, Any]]: 更新されたタイムライン
    """
    # 現在処理中のチャプター番号
    current_chapter_index = len(previous_timeline)
    
    # 現在処理中のチャプターのプロット
    current_chapter_plot = chapter_plots[current_chapter_index]
    
    # キャラクター名を抽出するための文字列を生成（プロンプト内で使用）
    character_names = "キャラクター名を抽出できません"
    try:
        # 文字列からキャラクター名を抽出するロジックを実装
        # 簡易的な実装としては、charactersからキャラクター名を抽出する
        pass
    except Exception as e:
        print(f"キャラクター名の抽出中にエラーが発生しました: {e}")
    
    # プロンプトの構築
    prompt = f"""
    # タイムライン生成タスク

    あなたは物語のタイムラインを整理するアシスタントです。各キャラクターの行動や出来事を日時とともに記録し、JSONフォーマットで出力してください。

    ## 入力情報

    [マスタープロット]
    {master_plot}

    [世界観設定]
    {backstories}

    [キャラクター設定]
    {characters}

    [現在のチャプタープロット] (チャプター{current_chapter_index + 1})
    {current_chapter_plot}

    ## これまでのタイムライン
    {json.dumps(previous_timeline, ensure_ascii=False, indent=2) if previous_timeline else "まだタイムラインは生成されていません。"}

    ## 指示
    チャプター{current_chapter_index + 1}に含まれる各キャラクターの行動や重要な出来事をタイムライン形式で整理してください。
    以下の形式のJSONを出力してください：

    ```json
    {{
      "キャラクター名A": {{
        "YYYY-MM-DD HH:MM": "出来事の説明",
        "YYYY-MM-DD HH:MM": "出来事の説明"
      }},
      "キャラクター名B": {{
        "YYYY-MM-DD HH:MM": "出来事の説明"
      }}
    }}
    ```

    注意事項：
    1. 日付は「YYYY-MM-DD HH:MM」形式で記述してください（例: "2023-05-15 14:30"）
    2. 同じキャラクターの以前のタイムラインエントリも保持し、チャプター{current_chapter_index + 1}での新しい出来事を追加してください
    3. 事実のみを簡潔に記述し、解釈や感情は含めないでください
    4. チャプター内の時系列が物語の時系列と一致しない場合があります
    5. 必ず有効なJSONフォーマットで出力してください
    6. すべてのキャラクターのタイムラインを含めてください（たとえチャプター{current_chapter_index + 1}に登場しなくても）

    JSON形式のタイムラインのみを出力してください。他の説明は不要です。
    """
    
    # LLMを呼び出してタイムラインを生成
    response = call_llm(prompt)
    
    # JSONの抽出（レスポンスからJSONのみを抽出する処理）
    json_str = extract_json_from_response(response)
    
    # JSON文字列をパース
    try:
        new_timeline_entry = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSONデコードに失敗しました: {e}")
        print(f"受け取った文字列: {json_str}")
        # エラー時は空の辞書を返す
        new_timeline_entry = {}
    
    # 前回のタイムラインに今回のエントリを追加
    updated_timeline = previous_timeline.copy()
    updated_timeline.append(new_timeline_entry)
    
    # For debugging only - will be removed in production
    # save_timeline_to_mock_files(updated_timeline, current_chapter_index)
    
    return updated_timeline


def extract_json_from_response(response: str) -> str:
    """
    LLMのレスポンスからJSON部分のみを抽出する
    
    このヘルパー関数は以下の順序でJSONを抽出しようとします:
    1. ```json```で囲まれたコードブロック内のJSONを探す
    2. レスポンス全体が有効なJSONかどうかチェック
    3. 最初の { から最後の } までを抽出し、有効なJSONとして解析する
    
    Args:
        response (str): LLMからのレスポンス
        
    Returns:
        str: 抽出されたJSON文字列
    """
    # JSONのコードブロックを探す
    json_pattern_start = "```json"
    json_pattern_end = "```"
    
    if json_pattern_start in response:
        start_index = response.find(json_pattern_start) + len(json_pattern_start)
        end_index = response.find(json_pattern_end, start_index)
        if end_index > start_index:
            json_str = response[start_index:end_index].strip()
            return json_str
    
    # コードブロックがない場合は、レスポンス全体からJSONを抽出しようとする
    # { で始まり } で終わる部分を探す
    if response.strip().startswith("{") and response.strip().endswith("}"):
        return response.strip()
    
    # 上記の方法で抽出できない場合は、最初の { から最後の } までを抽出
    start_index = response.find("{")
    end_index = response.rfind("}")
    if start_index != -1 and end_index > start_index:
        return response[start_index:end_index+1]
    
    # どの方法でも抽出できない場合は、エラーメッセージ付きの空のJSONを返す
    return '{}'
