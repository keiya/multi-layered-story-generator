from typing import List, Dict, Any
import json
from utils import call_llm

def backstory_consistency_validation_filter(
    master_plot: str,
    backstories: str,
    characters: str,
    plot: str,
    intent: str
) -> str:
    """
    BCVF: Backstory Consistency Validation Filter
    プロット、世界観、キャラクター設定との整合性をチェック
    """
    prompt = f"""
    [Master Plot]
    {master_plot}

    [Backstories]
    {backstories}

    [Characters]
    {characters}

    対象plot:
    {plot}
    対象intent:
    {intent}

    矛盾がないかチェック。
    問題あれば指摘、なければOK。
    """
    validation_output = call_llm(prompt)
    return validation_output

def chapter_level_causal_chain_validation_filter(
    master_plot: str,
    backstories: str,
    all_characters_timeline: List[Dict[str, Any]],
    characters: str,
    chapter_plots: List[str]
) -> str:
    """
    Chapter-Level CCVF: Chapter-Level Causal-Chain Validation Filter
    章レベルでの因果関係の整合性をチェック
    """
    prompt = f"""
    [Master Plot]
    {master_plot}

    [Backstories]
    {backstories}

    [Characters]
    {characters}

    全キャラクタータイムライン:
    {json.dumps(all_characters_timeline, ensure_ascii=False, indent=2)}

    全てのChapter Plot:
    {json.dumps(chapter_plots, ensure_ascii=False, indent=2)}

    全体の因果関係に矛盾がないかチェック。
    問題あれば指摘、なければOK。
    """
    validation_output = call_llm(prompt)
    return validation_output

def section_level_causal_chain_validation_filter(
    master_plot: str,
    backstories: str,
    all_characters_timeline: List[Dict[str, Any]],
    characters: str,
    chapter_plot: str,
    section_plots: List[str]
) -> str:
    """
    Section-Level CCVF: Section-Level Causal-Chain Validation Filter
    セクションレベルでの因果関係の整合性をチェック
    """
    prompt = f"""
    [Master Plot]
    {master_plot}

    [Backstories]
    {backstories}

    [Characters]
    {characters}

    全キャラクタータイムライン:
    {json.dumps(all_characters_timeline, ensure_ascii=False, indent=2)}

    Chapter Plot:
    {chapter_plot}

    全てのSection Plot:
    {json.dumps(section_plots, ensure_ascii=False, indent=2)}

    章内の因果関係に矛盾がないかチェック。
    問題あれば指摘、なければOK。
    """
    validation_output = call_llm(prompt)
    return validation_output

def style_filter(paragraph: str) -> str:
    """
    Style Filter
    段落の文体を整える
    """
    prompt = f"""
    以下の段落の文体を整えてください:
    {paragraph}
    """
    styled_paragraph = call_llm(prompt)
    return styled_paragraph 
