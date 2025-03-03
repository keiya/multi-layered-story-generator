import os
import sys
import time
from dotenv import load_dotenv
from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain.chains import LLMChain
import json
import shutil
from typing import Tuple, List, Dict, Any, Optional, Union, TypedDict, cast
from pathlib import Path

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

class Timeline(TypedDict):
    datetime: str
    event: str

# Load environment variables
load_dotenv()

# Define output directory
OUTPUT_DIR = Path("output")

# Colors for terminal output
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
    Print a formatted status message.
    
    Args:
        message (str): The message to print
        level (str): The level of the message (info, success, warning, error)
    """
    timestamp = time.strftime("%H:%M:%S")
    
    if level == "info":
        color = Colors.BLUE
        prefix = "INFO"
    elif level == "success":
        color = Colors.GREEN
        prefix = "SUCCESS"
    elif level == "warning":
        color = Colors.YELLOW
        prefix = "WARNING"
    elif level == "error":
        color = Colors.RED
        prefix = "ERROR"
    elif level == "header":
        color = Colors.HEADER + Colors.BOLD
        prefix = "PROCESS"
    else:
        color = ""
        prefix = "LOG"
        
    print(f"{color}[{timestamp}] {prefix}: {message}{Colors.ENDC}")

def ensure_dir(directory: Path) -> None:
    """Ensure a directory exists, create it if it doesn't."""
    directory.mkdir(parents=True, exist_ok=True)
    print_status(f"Ensuring directory exists: {directory}", "info")

def save_to_file(content: str, file_path: Path) -> None:
    """
    Save content to a file, ensuring the directory exists.
    
    Args:
        content (str): The content to save
        file_path (Path): The path to save the content to
    """
    ensure_dir(file_path.parent)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print_status(f"Saved content to {file_path}", "success")
    except Exception as e:
        print_status(f"Error saving to {file_path}: {e}", "error")

def read_from_file(file_path: Path) -> Optional[str]:
    """
    Read content from a file if it exists.
    
    Args:
        file_path (Path): The path to read from
        
    Returns:
        Optional[str]: The content of the file or None if the file doesn't exist
    """
    if not file_path.exists():
        print_status(f"File does not exist: {file_path}", "info")
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
    Save timeline data to a file.
    
    Args:
        timeline (List[Dict[str, Any]]): The timeline data
        chapter_index (int): The chapter index (0-based)
    """
    # Create the chapter directory path
    chapter_dir = OUTPUT_DIR / f"chapters/{chapter_index+1:02d}"
    ensure_dir(chapter_dir)
    
    # Save the timeline for this chapter
    timeline_path = chapter_dir / "_timeline.txt"
    try:
        with open(timeline_path, 'w', encoding='utf-8') as f:
            json.dump(timeline[chapter_index], f, ensure_ascii=False, indent=2)
        print_status(f"Saved timeline to {timeline_path}", "success")
    except Exception as e:
        print_status(f"Error saving timeline to {timeline_path}: {e}", "error")

def generate_story(user_input: str, chapter_count: int = 5, resume: bool = False) -> str:
    """
    Main story generation function with caching and resumption capability.

    Args:
        user_input (str): The initial story prompt from the user
        chapter_count (int, optional): Number of chapters to generate. Defaults to 5.
        resume (bool, optional): Whether to resume from existing files. Defaults to False.

    Returns:
        str: The complete generated story text
    """
    # Initialize output directory
    ensure_dir(OUTPUT_DIR)
    
    # Print startup message
    if resume:
        print_status("Story generation started in RESUME mode", "header")
        print_status("Looking for existing files to resume from...", "info")
    else:
        print_status("Story generation started in NEW mode", "header")
        print_status("Creating a new story from scratch", "info")
    
    # Plot Layer
    print_status("=== PLOT LAYER ===", "header")
    master_plot_path = OUTPUT_DIR / "master_plot.txt"
    if resume and (cached_master_plot := read_from_file(master_plot_path)) is not None:
        print_status("Resuming with existing master plot", "success")
        master_plot = cached_master_plot
    else:
        print_status("Generating new master plot...", "info")
        master_plot: str = plot_layer(user_input)
        save_to_file(master_plot, master_plot_path)

    # Backstory Layer
    print_status("=== BACKSTORY LAYER ===", "header")
    backstories_path = OUTPUT_DIR / "backstory.txt"
    if resume and (cached_backstories := read_from_file(backstories_path)) is not None:
        print_status("Resuming with existing backstories", "success")
        backstories = cached_backstories
    else:
        print_status("Generating new backstories...", "info")
        backstories: str = backstory_layer(master_plot)
        save_to_file(backstories, backstories_path)

    # Character Layer
    print_status("=== CHARACTER LAYER ===", "header")
    characters_path = OUTPUT_DIR / "character.txt"
    if resume and (cached_characters := read_from_file(characters_path)) is not None:
        print_status("Resuming with existing characters", "success")
        characters = cached_characters
    else:
        print_status("Generating new characters...", "info")
        characters: str = character_layer(master_plot, backstories)
        save_to_file(characters, characters_path)

    # Chapter Layer
    print_status("=== CHAPTER LAYER ===", "header")
    chapter_plots: List[str] = []
    chapter_intents: List[str] = []
    prev_chapter_plot: Optional[str] = None
    prev_chapter_intent: Optional[str] = None
    all_characters_timeline: List[Dict[str, Any]] = []

    for ch_i in range(chapter_count):
        print_status(f"Processing Chapter {ch_i+1}/{chapter_count}", "header")
        chapter_dir = OUTPUT_DIR / f"chapters/{ch_i+1:02d}"
        ensure_dir(chapter_dir)
        
        # Check if chapter files already exist
        chapter_plot_path = chapter_dir / "_plot.txt"
        chapter_intent_path = chapter_dir / "_intent.txt"
        
        if resume and (cached_chapter_plot := read_from_file(chapter_plot_path)) is not None and (cached_chapter_intent := read_from_file(chapter_intent_path)) is not None:
            print_status(f"Resuming with existing Chapter {ch_i+1}", "success")
            chapter_plot = cached_chapter_plot
            chapter_intent = cached_chapter_intent
        else:
            print_status(f"Generating new Chapter {ch_i+1}...", "info")
            chapter_plot, chapter_intent = chapter_layer(
                master_plot,
                backstories,
                characters,
                ch_i,
                previous_chapter_plot=prev_chapter_plot,
                previous_chapter_intent=prev_chapter_intent
            )
            save_to_file(chapter_plot, chapter_plot_path)
            save_to_file(chapter_intent, chapter_intent_path)
        
        chapter_plots.append(chapter_plot)
        chapter_intents.append(chapter_intent)

        # Timeline Layer
        print_status(f"=== TIMELINE LAYER (Chapter {ch_i+1}) ===", "header")
        chapter_timeline_path = chapter_dir / "_timeline.txt"
        if resume and all_characters_timeline and chapter_timeline_path.exists():
            print_status(f"Resuming with existing timeline for Chapter {ch_i+1}", "success")
            try:
                with open(chapter_timeline_path, 'r', encoding='utf-8') as f:
                    timeline_data = json.load(f)
                    # If this is a new chapter, append to the timeline
                    if len(all_characters_timeline) <= ch_i:
                        all_characters_timeline.append(timeline_data)
            except Exception as e:
                print_status(f"Error reading timeline from {chapter_timeline_path}: {e}", "error")
                # Generate the timeline if we couldn't read it
                print_status(f"Generating new timeline for Chapter {ch_i+1}...", "info")
                all_characters_timeline = timeline_layer(master_plot, backstories, characters, chapter_plots, all_characters_timeline)
                save_timeline_to_file(all_characters_timeline, ch_i)
        else:
            print_status(f"Generating new timeline for Chapter {ch_i+1}...", "info")
            all_characters_timeline = timeline_layer(master_plot, backstories, characters, chapter_plots, all_characters_timeline)
            save_timeline_to_file(all_characters_timeline, ch_i)

        # Validate chapter
        print_status(f"=== VALIDATING CHAPTER {ch_i+1} ===", "header")
        validation: str = backstory_consistency_validation_filter(master_plot, backstories, characters, chapter_plot, chapter_intent)
        if "OK" not in validation:
            print_status(f"Chapter {ch_i+1} validation failed: {validation}", "warning")
        else:
            print_status(f"Chapter {ch_i+1} validation passed", "success")

        prev_chapter_plot = chapter_plot
        prev_chapter_intent = chapter_intent

    # Validate all chapters
    print_status("=== VALIDATING ALL CHAPTERS ===", "header")
    validation: str = chapter_level_causal_chain_validation_filter(master_plot, backstories, all_characters_timeline, characters, chapter_plots)
    if "OK" not in validation:
        print_status(f"Overall chapter validation failed: {validation}", "warning")
    else:
        print_status("Overall chapter validation passed", "success")

    # Generate sections and paragraphs for each chapter
    print_status("=== GENERATING DETAILED CONTENT ===", "header")
    story_text: str = ""
    for ch_i, chapter_plot in enumerate(chapter_plots):
        print_status(f"Processing detailed content for Chapter {ch_i+1}/{chapter_count}", "header")
        story_text += f"\n\nChapter {ch_i+1}\n\n"
        chapter_dir = OUTPUT_DIR / f"chapters/{ch_i+1:02d}"
        
        # Section Layer
        print_status(f"=== SECTION LAYER (Chapter {ch_i+1}) ===", "header")
        section_plots: List[str] = []
        section_intents: List[str] = []
        prev_sections: List[str] = []
        prev_section_intent: Optional[str] = None

        # Default to 3 sections per chapter, but allow for finding more if resuming
        section_count = 3
        if resume:
            # Count existing section directories
            existing_sections = [d for d in chapter_dir.iterdir() if d.is_dir() and d.name.startswith("sec_")]
            section_count = max(section_count, len(existing_sections))
            print_status(f"Found {section_count} existing sections for Chapter {ch_i+1}", "info")

        for sec_i in range(section_count):
            print_status(f"Processing Section {sec_i+1}/{section_count} in Chapter {ch_i+1}", "info")
            section_dir = chapter_dir / f"sec_{sec_i+1:02d}"
            ensure_dir(section_dir)
            
            section_plot_path = section_dir / "_plot.txt"
            section_intent_path = section_dir / "_intent.txt"
            
            if resume and (cached_section_plot := read_from_file(section_plot_path)) is not None and (cached_section_intent := read_from_file(section_intent_path)) is not None:
                print_status(f"Resuming with existing Section {sec_i+1} in Chapter {ch_i+1}", "success")
                section_plot = cached_section_plot
                section_intent = cached_section_intent
            else:
                print_status(f"Generating new Section {sec_i+1} in Chapter {ch_i+1}...", "info")
                section_plot, section_intent = section_layer(
                    master_plot, backstories, characters,
                    all_characters_timeline, chapter_plot,
                    prev_sections, prev_section_intent
                )
                save_to_file(section_plot, section_plot_path)
                save_to_file(section_intent, section_intent_path)
            
            section_plots.append(section_plot)
            section_intents.append(section_intent)
            prev_sections.append(section_plot)
            prev_section_intent = section_intent

        # Validate sections
        print_status(f"=== VALIDATING SECTIONS (Chapter {ch_i+1}) ===", "header")
        validation: str = section_level_causal_chain_validation_filter(
            master_plot, backstories, all_characters_timeline,
            characters, chapter_plot, section_plots
        )
        if "OK" not in validation:
            print_status(f"Section validation failed in Chapter {ch_i+1}: {validation}", "warning")
        else:
            print_status(f"Section validation passed in Chapter {ch_i+1}", "success")

        # Generate paragraphs for each section
        for sec_i, section_plot in enumerate(section_plots):
            print_status(f"=== PARAGRAPH LAYER (Chapter {ch_i+1}, Section {sec_i+1}) ===", "header")
            story_text += f"\nSection {sec_i+1}\n"
            section_dir = chapter_dir / f"sec_{sec_i+1:02d}"
            
            # Paragraph Layer
            prev_paragraphs: List[str] = []
            prev_paragraph_intent: Optional[str] = None

            # Default to 5 paragraphs per section, but allow for finding more if resuming
            paragraph_count = 5
            if resume:
                # Count existing paragraph files
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
                
                if resume and (cached_paragraph := read_from_file(paragraph_path)) is not None and (cached_paragraph_intent := read_from_file(paragraph_intent_path)) is not None:
                    print_status(f"Resuming with existing Paragraph {para_i+1} in Section {sec_i+1}, Chapter {ch_i+1}", "success")
                    paragraph = cached_paragraph
                    paragraph_intent = cached_paragraph_intent
                else:
                    print_status(f"Generating new Paragraph {para_i+1} in Section {sec_i+1}, Chapter {ch_i+1}...", "info")
                    paragraph, paragraph_intent = paragraph_layer(
                        master_plot, backstories, characters,
                        all_characters_timeline, section_plot,
                        prev_paragraphs, prev_paragraph_intent
                    )
                    save_to_file(paragraph, paragraph_path)
                    save_to_file(paragraph_intent, paragraph_intent_path)
                
                # Apply style filter
                print_status(f"Applying style filter to Paragraph {para_i+1}...", "info")
                styled_paragraph: str = style_filter(paragraph)
                styled_paragraph_path = section_dir / f"{para_i+1:03d}_styled.txt"
                save_to_file(styled_paragraph, styled_paragraph_path)
                
                story_text += f"\n{styled_paragraph}"
                prev_paragraphs.append(paragraph)
                prev_paragraph_intent = paragraph_intent

    # Save the complete story
    print_status("=== SAVING COMPLETE STORY ===", "header")
    complete_story_path = OUTPUT_DIR / "complete_story.txt"
    save_to_file(story_text, complete_story_path)
    
    print_status("Story generation completed successfully!", "header")
    print_status(f"Complete story saved to {complete_story_path}", "success")
    
    return story_text

if __name__ == "__main__":
    user_input: str = """
    ファンタジー世界を舞台に、魔法使いの少女が失われた古代魔法を求めて冒険する物語。
    テーマは「知識の探求」と「成長」。
    """
    
    # Add command line arguments support
    if len(sys.argv) > 1 and sys.argv[1] == "--resume":
        print_status("Command line argument '--resume' detected, resuming from existing files", "info")
        resume_mode = True
    else:
        resume_mode = False
    
    # Set resume=True to continue from existing files
    story: str = generate_story(user_input, resume=resume_mode)
    
    # Print story length statistics
    word_count = len(story.split())
    print_status(f"Generated story with {word_count} words", "success")
