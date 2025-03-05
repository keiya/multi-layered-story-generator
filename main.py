import os
import sys
import time
import argparse
from dotenv import load_dotenv
from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain.chains import LLMChain
import json
import shutil
from typing import Tuple, List, Dict, Any, Optional, Union, TypedDict, cast, Literal
from pathlib import Path
from enum import Enum, auto

from layers import (
    plot_layer,
    backstory_layer,
    character_layer,
    chapter_layer,
    timeline_layer,
    section_layer,
    paragraph_layer
)
from filters import (
    backstory_consistency_validation_filter,
    chapter_level_causal_chain_validation_filter,
    section_level_causal_chain_validation_filter,
    style_filter
)

# 利用可能なレイヤーを定義するEnum
class Layer(Enum):
    PLOT = "plot"
    BACKSTORY = "backstory"
    CHARACTER = "character"
    CHAPTER = "chapter"
    TIMELINE = "timeline"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    STYLE = "style"
    ALL = "all"  # すべてのレイヤーを実行

    @staticmethod
    def from_string(layer_name: str) -> "Layer":
        try:
            return Layer(layer_name.lower())
        except ValueError:
            valid_layers = ", ".join([l.value for l in Layer])
            raise ValueError(f"Invalid layer: {layer_name}. Valid layers are: {valid_layers}")

class Timeline(TypedDict):
    datetime: str
    event: str

# 出力ディレクトリ設定
OUTPUT_DIR = Path("./output")

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_status(message: str, level: str = "info") -> None:
    """
    Print a status message with color coding
    
    Args:
        message (str): Message to print
        level (str): Message level (info, success, warning, error, header)
    """
    now = time.strftime("%H:%M:%S")
    prefix = f"[{now}]"
    
    if level == "info":
        print(f"{Colors.BLUE}{prefix} INFO:{Colors.ENDC} {message}")
    elif level == "success":
        print(f"{Colors.GREEN}{prefix} SUCCESS:{Colors.ENDC} {message}")
    elif level == "warning":
        print(f"{Colors.YELLOW}{prefix} WARNING:{Colors.ENDC} {message}")
    elif level == "error":
        print(f"{Colors.RED}{prefix} ERROR:{Colors.ENDC} {message}")
    elif level == "header":
        print(f"\n{Colors.HEADER}{Colors.BOLD}{prefix} {message}{Colors.ENDC}")
    else:
        print(f"{prefix} {message}")

def ensure_dir(directory: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary
    """
    directory.mkdir(parents=True, exist_ok=True)

def save_to_file(content: str, file_path: Path) -> None:
    """
    Save text content to a file
    
    Args:
        content (str): Text content to save
        file_path (Path): Path to save the file to
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print_status(f"Saved content to {file_path}", "success")
    except Exception as e:
        print_status(f"Error saving to {file_path}: {e}", "error")

def read_from_file(file_path: Path) -> Optional[str]:
    """
    Read text content from a file if it exists
    
    Args:
        file_path (Path): Path to read from
    
    Returns:
        Optional[str]: File content or None if file doesn't exist
    """
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print_status(f"Read content from {file_path}", "success")
        return content
    except Exception as e:
        print_status(f"Error reading from {file_path}: {e}", "error")
        return None

def save_timeline_to_file(timeline: List[Dict[str, Any]], chapter_index: int) -> None:
    """
    Save timeline data to a JSON file
    
    Args:
        timeline (List[Dict[str, Any]]): Timeline data to save
        chapter_index (int): Current chapter index
    """
    chapter_dir = OUTPUT_DIR / f"chapters/{chapter_index+1:02d}"
    ensure_dir(chapter_dir)
    
    timeline_file = chapter_dir / "_timeline.txt"
    try:
        with open(timeline_file, 'w', encoding='utf-8') as f:
            json.dump(timeline[chapter_index] if chapter_index < len(timeline) else {}, f, ensure_ascii=False, indent=2)
        print_status(f"Timeline saved to {timeline_file}", "success")
    except Exception as e:
        print_status(f"Error saving timeline to {timeline_file}: {e}", "error")

class StoryGenerator:
    """
    物語生成を管理するクラス
    """
    def __init__(self, user_input: str, chapter_count: int = 5, resume: bool = False):
        """
        StoryGenerator を初期化する
        
        Args:
            user_input (str): ユーザーからの初期プロンプト
            chapter_count (int): 生成する章の数
            resume (bool): 既存ファイルから再開するかどうか
        """
        self.user_input = user_input
        self.chapter_count = chapter_count
        self.resume = resume
        
        # 各レイヤーの結果を保存する変数
        self.master_plot: str = ""  # None から空文字列に変更
        self.backstories: str = ""  # None から空文字列に変更
        self.characters: str = ""   # None から空文字列に変更
        self.chapter_plots: List[str] = []
        self.chapter_intents: List[str] = []
        self.all_characters_timeline: List[Dict[str, Any]] = []
        self.section_plots: List[List[str]] = []
        self.section_intents: List[List[str]] = []
        self.story_text: str = ""
        
        # 出力ディレクトリを初期化
        ensure_dir(OUTPUT_DIR)
        
        # 開始メッセージを表示
        if resume:
            print_status("Story generation started in RESUME mode", "header")
            print_status("Looking for existing files to resume from...", "info")
        else:
            print_status("Story generation started in NEW mode", "header")
            print_status("Creating a new story from scratch", "info")

    def generate_plot(self) -> str:
        """
        マスタープロットを生成する
        
        Returns:
            str: 生成されたマスタープロット
        """
        print_status("=== PLOT LAYER ===", "header")
        master_plot_path = OUTPUT_DIR / "master_plot.txt"
        if self.resume and (cached_master_plot := read_from_file(master_plot_path)) is not None:
            print_status("Resuming with existing master plot", "success")
            self.master_plot = cached_master_plot
        else:
            print_status("Generating new master plot...", "info")
            self.master_plot = plot_layer(self.user_input)
            save_to_file(self.master_plot, master_plot_path)
        
        return self.master_plot
    
    def generate_backstory(self) -> str:
        """
        世界観設定を生成する
        
        Returns:
            str: 生成された世界観設定
        """
        if not self.master_plot:  # 空文字列のチェックに変更
            self.generate_plot()
        
        print_status("=== BACKSTORY LAYER ===", "header")
        backstories_path = OUTPUT_DIR / "backstory.txt"
        if self.resume and (cached_backstories := read_from_file(backstories_path)) is not None:
            print_status("Resuming with existing backstories", "success")
            self.backstories = cached_backstories
        else:
            print_status("Generating new backstories...", "info")
            self.backstories = backstory_layer(self.master_plot)
            save_to_file(self.backstories, backstories_path)
        
        return self.backstories
    
    def generate_characters(self) -> str:
        """
        キャラクター設定を生成する
        
        Returns:
            str: 生成されたキャラクター設定
        """
        if not self.backstories:  # 空文字列のチェックに変更
            self.generate_backstory()
        
        print_status("=== CHARACTER LAYER ===", "header")
        characters_path = OUTPUT_DIR / "character.txt"
        if self.resume and (cached_characters := read_from_file(characters_path)) is not None:
            print_status("Resuming with existing characters", "success")
            self.characters = cached_characters
        else:
            print_status("Generating new characters...", "info")
            self.characters = character_layer(self.master_plot, self.backstories)
            save_to_file(self.characters, characters_path)
        
        return self.characters
    
    def generate_chapters(self) -> List[str]:
        """
        章ごとのプロットを生成する
        
        Returns:
            List[str]: 生成された章のプロットのリスト
        """
        if not self.characters:  # 空文字列のチェックに変更
            self.generate_characters()
        
        print_status("=== CHAPTER LAYER ===", "header")
        
        for ch_i in range(self.chapter_count):
            print_status(f"Processing Chapter {ch_i+1}/{self.chapter_count}", "header")
            chapter_dir = OUTPUT_DIR / f"chapters/{ch_i+1:02d}"
            ensure_dir(chapter_dir)
            
            # 章ファイルが既に存在するかチェック
            chapter_plot_path = chapter_dir / "_plot.txt"
            chapter_intent_path = chapter_dir / "_intent.txt"
            
            if self.resume and (cached_chapter_plot := read_from_file(chapter_plot_path)) is not None and (cached_chapter_intent := read_from_file(chapter_intent_path)) is not None:
                print_status(f"Resuming with existing Chapter {ch_i+1}", "success")
                chapter_plot = cached_chapter_plot
                chapter_intent = cached_chapter_intent
            else:
                print_status(f"Generating new Chapter {ch_i+1}...", "info")
                is_final_chapter = (ch_i == self.chapter_count - 1)
                chapter_plot, chapter_intent = chapter_layer(
                    self.master_plot,
                    self.backstories,
                    self.characters,
                    ch_i,
                    previous_chapter_plots=self.chapter_plots if self.chapter_plots else None,
                    previous_chapter_intents=self.chapter_intents if self.chapter_intents else None,
                    is_final_chapter=is_final_chapter
                )
                save_to_file(chapter_plot, chapter_plot_path)
                save_to_file(chapter_intent, chapter_intent_path)
            
            self.chapter_plots.append(chapter_plot)
            self.chapter_intents.append(chapter_intent)
            
            # タイムラインレイヤーの生成は各章ごとに必要
            self.generate_timeline_for_chapter(ch_i)
            
            # 章を検証
            print_status(f"=== VALIDATING CHAPTER {ch_i+1} ===", "header")
            validation: str = backstory_consistency_validation_filter(
                self.master_plot, self.backstories, self.characters, 
                chapter_plot, chapter_intent
            )
            if "OK" not in validation:
                print_status(f"Chapter {ch_i+1} validation failed: {validation}", "warning")
            else:
                print_status(f"Chapter {ch_i+1} validation passed", "success")
        
        # すべての章を検証
        print_status("=== VALIDATING ALL CHAPTERS ===", "header")
        validation: str = chapter_level_causal_chain_validation_filter(
            self.master_plot, self.backstories, self.all_characters_timeline, 
            self.characters, self.chapter_plots
        )
        if "OK" not in validation:
            print_status(f"Overall chapter validation failed: {validation}", "warning")
        else:
            print_status("Overall chapter validation passed", "success")
        
        return self.chapter_plots
    
    def generate_timeline_for_chapter(self, chapter_index: int) -> List[Dict[str, Any]]:
        """
        指定された章のタイムラインを生成する
        
        Args:
            chapter_index (int): 章のインデックス
            
        Returns:
            List[Dict[str, Any]]: 更新されたタイムライン
        """
        print_status(f"=== TIMELINE LAYER (Chapter {chapter_index+1}) ===", "header")
        chapter_dir = OUTPUT_DIR / f"chapters/{chapter_index+1:02d}"
        chapter_timeline_path = chapter_dir / "_timeline.txt"
        
        if self.resume and chapter_timeline_path.exists():
            print_status(f"Resuming with existing timeline for Chapter {chapter_index+1}", "success")
            try:
                with open(chapter_timeline_path, 'r', encoding='utf-8') as f:
                    timeline_data = json.load(f)
                    # 新しい章なら、タイムラインに追加
                    if len(self.all_characters_timeline) <= chapter_index:
                        self.all_characters_timeline.append(timeline_data)
                    else:
                        # 既存の章のタイムラインを更新
                        self.all_characters_timeline[chapter_index] = timeline_data
            except Exception as e:
                print_status(f"Error reading timeline from {chapter_timeline_path}: {e}", "error")
                # タイムラインの読み込みに失敗したら生成
                print_status(f"Generating new timeline for Chapter {chapter_index+1}...", "info")
                self.all_characters_timeline = timeline_layer(
                    self.master_plot, self.backstories, self.characters, 
                    self.chapter_plots, self.all_characters_timeline
                )
                save_timeline_to_file(self.all_characters_timeline, chapter_index)
        else:
            print_status(f"Generating new timeline for Chapter {chapter_index+1}...", "info")
            self.all_characters_timeline = timeline_layer(
                self.master_plot, self.backstories, self.characters, 
                self.chapter_plots, self.all_characters_timeline
            )
            save_timeline_to_file(self.all_characters_timeline, chapter_index)
        
        return self.all_characters_timeline
    
    def generate_sections(self) -> List[List[str]]:
        """
        各章のセクションを生成する
        
        Returns:
            List[List[str]]: 章ごとのセクションプロットのリスト
        """
        if not self.chapter_plots:
            self.generate_chapters()
        
        print_status("=== GENERATING SECTIONS ===", "header")
        self.section_plots = []
        self.section_intents = []
        
        for ch_i, chapter_plot in enumerate(self.chapter_plots):
            print_status(f"Processing sections for Chapter {ch_i+1}/{self.chapter_count}", "header")
            chapter_dir = OUTPUT_DIR / f"chapters/{ch_i+1:02d}"
            
            # セクションレイヤー
            print_status(f"=== SECTION LAYER (Chapter {ch_i+1}) ===", "header")
            section_plots: List[str] = []
            section_intents: List[str] = []
            prev_sections: List[str] = []
            prev_section_intent: Optional[str] = None
            
            # デフォルトでは1章あたり3セクションだが、既存のものがあればそれに合わせる
            section_count = 3
            if self.resume:
                # 既存のセクションディレクトリをカウント
                existing_sections = [d for d in chapter_dir.iterdir() if d.is_dir() and d.name.startswith("sec_")]
                section_count = max(section_count, len(existing_sections))
                print_status(f"Found {section_count} existing sections for Chapter {ch_i+1}", "info")
            
            for sec_i in range(section_count):
                print_status(f"Processing Section {sec_i+1}/{section_count} in Chapter {ch_i+1}", "info")
                section_dir = chapter_dir / f"sec_{sec_i+1:02d}"
                ensure_dir(section_dir)
                
                section_plot_path = section_dir / "_plot.txt"
                section_intent_path = section_dir / "_intent.txt"
                
                if self.resume and (cached_section_plot := read_from_file(section_plot_path)) is not None and (cached_section_intent := read_from_file(section_intent_path)) is not None:
                    print_status(f"Resuming with existing Section {sec_i+1} in Chapter {ch_i+1}", "success")
                    section_plot = cached_section_plot
                    section_intent = cached_section_intent
                else:
                    print_status(f"Generating new Section {sec_i+1} in Chapter {ch_i+1}...", "info")
                    # これまでの全ての章のセクションを収集
                    all_previous_sections = self.section_plots[:ch_i] if ch_i > 0 else []
                    
                    # まだセクション化されていない章のプロットを収集
                    remaining_chapter_plots = []
                    if ch_i + 1 < len(self.chapter_plots):
                        remaining_chapter_plots = self.chapter_plots[ch_i+1:]
                    
                    section_plot, section_intent = section_layer(
                        self.master_plot, self.backstories, self.characters,
                        self.all_characters_timeline, chapter_plot,
                        prev_sections, prev_section_intent,
                        all_previous_sections, remaining_chapter_plots
                    )
                    save_to_file(section_plot, section_plot_path)
                    save_to_file(section_intent, section_intent_path)
                
                section_plots.append(section_plot)
                section_intents.append(section_intent)
                prev_sections.append(section_plot)
                prev_section_intent = section_intent
            
            # セクションを検証
            print_status(f"=== VALIDATING SECTIONS (Chapter {ch_i+1}) ===", "header")
            validation: str = section_level_causal_chain_validation_filter(
                self.master_plot, self.backstories, self.all_characters_timeline,
                self.characters, chapter_plot, section_plots
            )
            if "OK" not in validation:
                print_status(f"Section validation failed in Chapter {ch_i+1}: {validation}", "warning")
            else:
                print_status(f"Section validation passed in Chapter {ch_i+1}", "success")
            
            self.section_plots.append(section_plots)
            self.section_intents.append(section_intents)
        
        return self.section_plots
    
    def generate_paragraphs(self) -> str:
        """
        各セクションの段落を生成し、完全なストーリーテキストを作成する
        
        Returns:
            str: 生成された完全なストーリーテキスト
        """
        if not self.section_plots:
            self.generate_sections()
        
        print_status("=== GENERATING PARAGRAPHS ===", "header")
        story_text = ""
        
        for ch_i, (chapter_plot, section_plots_for_chapter) in enumerate(zip(self.chapter_plots, self.section_plots)):
            print_status(f"Processing paragraphs for Chapter {ch_i+1}/{self.chapter_count}", "header")
            story_text += f"\n\nChapter {ch_i+1}\n\n"
            chapter_dir = OUTPUT_DIR / f"chapters/{ch_i+1:02d}"
            
            for sec_i, section_plot in enumerate(section_plots_for_chapter):
                print_status(f"=== PARAGRAPH LAYER (Chapter {ch_i+1}, Section {sec_i+1}) ===", "header")
                story_text += f"\nSection {sec_i+1}\n"
                section_dir = chapter_dir / f"sec_{sec_i+1:02d}"
                
                # パラグラフレイヤー
                prev_paragraphs: List[str] = []
                prev_paragraph_intent: Optional[str] = None
                
                # デフォルトでは1セクションあたり5段落だが、既存のものがあればそれに合わせる
                paragraph_count = 5
                if self.resume:
                    # 既存の段落ファイルをカウント
                    existing_paragraphs = [f for f in section_dir.iterdir() 
                                        if f.is_file() and f.name.endswith(".txt") 
                                        and not f.name.startswith("_") 
                                        and not f.name.endswith("_intent.txt")
                                        and not f.name.endswith("_styled.txt")]
                    paragraph_count = max(paragraph_count, len(existing_paragraphs))
                    print_status(f"Found {paragraph_count} existing paragraphs in Section {sec_i+1}, Chapter {ch_i+1}", "info")
                
                for para_i in range(paragraph_count):
                    print_status(f"Processing Paragraph {para_i+1}/{paragraph_count} in Section {sec_i+1}, Chapter {ch_i+1}", "info")
                    paragraph_path = section_dir / f"{para_i+1:03d}.txt"
                    paragraph_intent_path = section_dir / f"{para_i+1:03d}_intent.txt"
                    
                    if self.resume and (cached_paragraph := read_from_file(paragraph_path)) is not None and (cached_paragraph_intent := read_from_file(paragraph_intent_path)) is not None:
                        print_status(f"Resuming with existing Paragraph {para_i+1} in Section {sec_i+1}, Chapter {ch_i+1}", "success")
                        paragraph = cached_paragraph
                        paragraph_intent = cached_paragraph_intent
                    else:
                        print_status(f"Generating new Paragraph {para_i+1} in Section {sec_i+1}, Chapter {ch_i+1}...", "info")
                        paragraph, paragraph_intent = paragraph_layer(
                            self.master_plot, self.backstories, self.characters,
                            self.all_characters_timeline, section_plot,
                            prev_paragraphs, prev_paragraph_intent
                        )
                        save_to_file(paragraph, paragraph_path)
                        save_to_file(paragraph_intent, paragraph_intent_path)
                    
                    # スタイルフィルターを適用
                    print_status(f"Applying style filter to Paragraph {para_i+1}...", "info")
                    styled_paragraph: str = style_filter(paragraph)
                    styled_paragraph_path = section_dir / f"{para_i+1:03d}_styled.txt"
                    save_to_file(styled_paragraph, styled_paragraph_path)
                    
                    story_text += f"\n{styled_paragraph}"
                    prev_paragraphs.append(paragraph)
                    prev_paragraph_intent = paragraph_intent
        
        self.story_text = story_text
        
        # 完全なストーリーを保存
        print_status("=== SAVING COMPLETE STORY ===", "header")
        complete_story_path = OUTPUT_DIR / "complete_story.txt"
        save_to_file(story_text, complete_story_path)
        
        print_status("Story generation completed successfully!", "header")
        print_status(f"Complete story saved to {complete_story_path}", "success")
        
        # ストーリーの長さの統計を表示
        word_count = len(story_text.split())
        print_status(f"Generated story with {word_count} words", "success")
        
        return story_text
    
    def generate_until_layer(self, target_layer: Layer) -> Any:
        """
        指定されたレイヤーまで物語を生成する
        
        Args:
            target_layer (Layer): 生成を停止するレイヤー
            
        Returns:
            Any: 最後に生成されたレイヤーの結果
        """
        if target_layer == Layer.PLOT:
            return self.generate_plot()
        elif target_layer == Layer.BACKSTORY:
            return self.generate_backstory()
        elif target_layer == Layer.CHARACTER:
            return self.generate_characters()
        elif target_layer == Layer.CHAPTER:
            return self.generate_chapters()
        elif target_layer == Layer.TIMELINE:
            self.generate_chapters()  # タイムラインは章と一緒に生成される
            return self.all_characters_timeline
        elif target_layer == Layer.SECTION:
            return self.generate_sections()
        elif target_layer == Layer.PARAGRAPH:
            return self.generate_paragraphs()
        elif target_layer == Layer.STYLE:
            return self.generate_paragraphs()  # スタイルは段落と一緒に適用される
        elif target_layer == Layer.ALL:
            return self.generate_paragraphs()
        else:
            raise ValueError(f"Unknown layer: {target_layer}")

def parse_args() -> argparse.Namespace:
    """
    コマンドライン引数をパースする
    
    Returns:
        argparse.Namespace: パースされた引数
    """
    parser = argparse.ArgumentParser(description='Multi-layered Story Generator')
    
    parser.add_argument('--layer', type=str, default='all',
                        help=f'レイヤーまで生成する (利用可能なレイヤー: {", ".join([l.value for l in Layer])})')
    
    parser.add_argument('--resume', action='store_true',
                        help='既存のファイルから再開する')
    
    parser.add_argument('--chapters', type=int, default=5,
                        help='生成する章の数 (デフォルト: 5)')
    
    parser.add_argument('--prompt', type=str,
                        help='物語生成のための初期プロンプト')
    
    parser.add_argument('--prompt-file', type=str,
                        help='プロンプトを含むファイルのパス')
    
    return parser.parse_args()

def main() -> None:
    """
    メイン関数
    """
    args = parse_args()
    
    # プロンプトの取得
    if args.prompt:
        user_input = args.prompt
    elif args.prompt_file:
        try:
            with open(args.prompt_file, 'r', encoding='utf-8') as f:
                user_input = f.read().strip()
        except Exception as e:
            print_status(f"Error reading prompt file: {e}", "error")
            user_input = """
            ファンタジー世界を舞台に、魔法使いの少女が失われた古代魔法を求めて冒険する物語。
            テーマは「知識の探求」と「成長」。
            """
    else:
        user_input = """
        ファンタジー世界を舞台に、魔法使いの少女が失われた古代魔法を求めて冒険する物語。
        テーマは「知識の探求」と「成長」。
        """
    
    # レイヤーの取得
    try:
        target_layer = Layer.from_string(args.layer)
    except ValueError as e:
        print_status(str(e), "error")
        return
    
    # ストーリー生成
    try:
        generator = StoryGenerator(user_input, chapter_count=args.chapters, resume=args.resume)
        result = generator.generate_until_layer(target_layer)
        
        print_status(f"Story generation completed until layer: {target_layer.value}", "header")
    except Exception as e:
        print_status(f"Error during story generation: {e}", "error")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
