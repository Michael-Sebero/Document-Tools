#!/usr/bin/env python3

import os
import sys
import re
import csv
import hashlib
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict

# Optional imports with graceful fallbacks
try:
    from pydub import AudioSegment
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import PyPDF2
    import docx
    import magic
    import chardet
    DOCUMENT_AVAILABLE = True
except ImportError:
    DOCUMENT_AVAILABLE = False

try:
    import requests
    from urllib.parse import urljoin, urlparse
    from bs4 import BeautifulSoup
    import cssutils
    import logging
    cssutils.log.setLevel(logging.CRITICAL)
    FONT_AVAILABLE = True
except ImportError:
    FONT_AVAILABLE = False


def get_key():
    """Get single keypress from terminal"""
    import termios
    import tty
    
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        
        # Handle escape sequences (arrow keys)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
        elif ch in '\r\n':
            return 'ENTER'
        elif ch == '\x03':  # Ctrl+C
            return 'CTRL_C'
        
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def clear():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


class Config:
    """Central configuration"""
    CHUNK_SIZE = 8192
    OUTPUT_FOLDER = "Output"
    
    # File type definitions
    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.heic', '.webp', '.tiff'}
    VIDEO_EXTS = {'.webm', '.mp4', '.mov', '.flv', '.avi', '.mkv', '.wmv', '.rmvb', '.3gp', '.m4v'}
    AUDIO_EXTS = {'.m4a', '.mp3', '.ogg', '.opus', '.flac', '.alac', '.wav', '.amr', '.aac', '.m4b', '.m4p'}
    DOCUMENT_EXTS = {'.txt', '.md', '.log', '.conf', '.doc', '.docx', '.pdf', '.ppt', '.pptx', 
                     '.xls', '.xlsx', '.odt', '.rtf', '.json', '.xml', '.yaml', '.yml', 
                     '.ini', '.cfg', '.properties', '.csv', '.tsv'}
    CODE_EXTS = {'.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.sh', '.bat', '.ps1', '.sql'}
    ARCHIVE_EXTS = {'.zip', '.tar', '.tar.gz', '.rar', '.gz', '.7z'}
    FONT_EXTS = {'.ttf', '.otf', '.woff', '.woff2', '.eot'}


class PathUtils:
    """Path and file utilities"""
    
    @staticmethod
    def get_valid_path(prompt: str = "Enter path: ", must_exist: bool = True) -> Optional[Path]:
        """Get and validate a path from user input"""
        path_str = input(prompt).strip().strip("'\"")
        if not path_str:
            return None
        
        path = Path(os.path.expanduser(path_str)).resolve()
        
        if must_exist and not path.exists():
            print(f"Error: Path does not exist: {path}")
            return None
        
        return path
    
    @staticmethod
    def ensure_unique(filepath: Path) -> Path:
        """Ensure filepath is unique by adding counter if needed"""
        if not filepath.exists():
            return filepath
        
        stem = filepath.stem
        suffix = filepath.suffix
        parent = filepath.parent
        counter = 1
        
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    @staticmethod
    def get_output_folder(base_path: Path) -> Path:
        """Create and return output folder path"""
        output = base_path / Config.OUTPUT_FOLDER
        output.mkdir(exist_ok=True)
        return output


class FileScanner:
    """File system scanning utilities"""
    
    @staticmethod
    def scan(location: Path, extensions: Set[str] = None, recursive: bool = False) -> List[Path]:
        """Scan for files with specified extensions"""
        files = []
        
        if location.is_file():
            if extensions is None or location.suffix.lower() in extensions:
                files.append(location)
        elif location.is_dir():
            if recursive:
                for root, _, filenames in os.walk(location):
                    for filename in filenames:
                        filepath = Path(root) / filename
                        if extensions is None or filepath.suffix.lower() in extensions:
                            files.append(filepath)
            else:
                for item in location.iterdir():
                    if item.is_file():
                        if extensions is None or item.suffix.lower() in extensions:
                            files.append(item)
        
        return sorted(files)


class UserInput:
    """User interaction utilities"""
    
    @staticmethod
    def yes_no(prompt: str, default: bool = False) -> bool:
        """Get yes/no response from user"""
        suffix = " [Y/n]: " if default else " [y/N]: "
        response = input(prompt + suffix).strip().lower()
        
        if not response:
            return default
        return response in {'y', 'yes'}
    
    @staticmethod
    def get_choice(prompt: str, valid_choices: List[str]) -> str:
        """Get a valid choice from user"""
        while True:
            choice = input(prompt).strip()
            if choice in valid_choices:
                return choice
            print(f"Invalid choice. Please enter one of: {', '.join(valid_choices)}")


class AudioProcessor:
    """Audio file processing operations"""
    
    @staticmethod
    def adjust_volume():
        """Adjust volume of audio files"""
        if not AUDIO_AVAILABLE:
            print("Error: pydub not installed. Run: pip install pydub")
            return
        
        input_path = PathUtils.get_valid_path("Enter file or directory path: ")
        if not input_path:
            return
        
        try:
            choice = UserInput.get_choice(
                "Choose option:\n1 = Reduce volume\n2 = Increase volume\nEnter 1 or 2: ",
                ['1', '2']
            )
            increase = (choice == '2')
            
            adjustment = float(input("Enter adjustment percentage (1-100): ").strip())
            if not (1 <= adjustment <= 100):
                print("Adjustment must be between 1 and 100")
                return
            
            AudioProcessor._process_files(input_path, adjustment, increase)
            
        except ValueError as e:
            print(f"Error: {e}")
    
    @staticmethod
    def _process_files(input_path: Path, adjustment: float, increase: bool):
        """Process audio files for volume adjustment"""
        base_dir = input_path.parent if input_path.is_file() else input_path
        output_folder = PathUtils.get_output_folder(base_dir)
        
        audio_files = FileScanner.scan(input_path, Config.AUDIO_EXTS)
        
        if not audio_files:
            print("No audio files found")
            return
        
        print(f"\nProcessing {len(audio_files)} files...\n")
        
        for filepath in audio_files:
            try:
                AudioProcessor._adjust_file(filepath, output_folder, adjustment, increase)
            except Exception as e:
                print(f"Error processing {filepath.name}: {e}")
        
        print("\nComplete!")
    
    @staticmethod
    def _adjust_file(filepath: Path, output_folder: Path, adjustment: float, increase: bool):
        """Adjust volume of a single audio file"""
        audio = AudioSegment.from_file(str(filepath))
        adjustment_db = adjustment if increase else -adjustment
        adjusted = audio + adjustment_db
        
        output_path = output_folder / filepath.name
        file_format = filepath.suffix[1:]  # Remove leading dot
        
        adjusted.export(str(output_path), format=file_format)
        print(f"Saved: {output_path}")


class DocumentProcessor:
    """Document processing operations"""
    
    @staticmethod
    def compare_documents():
        """Compare two documents and output differences"""
        file1 = PathUtils.get_valid_path("Enter first document path: ")
        file2 = PathUtils.get_valid_path("Enter second document path: ")
        
        if not file1 or not file2:
            return
        
        try:
            lines1 = set(DocumentProcessor._read_file(file1))
            lines2 = set(DocumentProcessor._read_file(file2))
            
            common = lines1.intersection(lines2)
            diff1 = lines1 - common
            diff2 = lines2 - common
            
            desktop = Path.home() / 'Desktop'
            output_path = desktop / "comparison_output.txt"
            
            DocumentProcessor._write_comparison(output_path, file1, file2, common, diff1, diff2)
            print(f"\nComparison saved to: {output_path}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    @staticmethod
    def _read_file(filepath: Path) -> List[str]:
        """Read file lines with encoding fallback"""
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                    return f.readlines()
            except (UnicodeDecodeError, LookupError):
                continue
        return []
    
    @staticmethod
    def _write_comparison(output: Path, file1: Path, file2: Path, 
                         common: Set[str], diff1: Set[str], diff2: Set[str]):
        """Write comparison results to file"""
        border = "=" * 20
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(f"{border} Common Lines {border}\n")
            f.write('\n'.join(sorted(common)))
            
            f.write(f"\n\n{border} Only in {file1.name} {border}\n")
            f.write('\n'.join(sorted(diff1)))
            
            f.write(f"\n\n{border} Only in {file2.name} {border}\n")
            f.write('\n'.join(sorted(diff2)))


class DuplicateRemover:
    """Remove duplicate lines from files"""
    
    @staticmethod
    def remove_duplicates():
        """Remove duplicate lines and sort"""
        location = PathUtils.get_valid_path("Directory path: ")
        if not location:
            return
        
        recursive = UserInput.yes_no("Apply recursively?")
        
        files = FileScanner.scan(location, recursive=recursive)
        
        if not files:
            print("No files found")
            return
        
        print(f"\nProcessing {len(files)} files...\n")
        
        for filepath in files:
            try:
                DuplicateRemover._process_file(filepath)
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
    
    @staticmethod
    def _process_file(filepath: Path):
        """Process single file to remove duplicates"""
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        unique_lines = sorted(set(lines))
        
        output_path = filepath.parent / f"output_{filepath.name}"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(unique_lines)
        
        print(f"Processed: {filepath.name} → {output_path.name}")


class TextExtractor:
    """Extract text from images using OCR"""
    
    @staticmethod
    def extract_text():
        """Extract text from images in directory or single file"""
        if not OCR_AVAILABLE:
            print("Error: OCR libraries not installed")
            print("Run: pip install pytesseract pillow")
            print("Also install Tesseract OCR system package")
            return
        
        source = PathUtils.get_valid_path("Enter source (file or directory): ")
        if not source:
            return
        
        if source.is_file():
            TextExtractor._process_file(source)
        else:
            TextExtractor._process_directory(source)
    
    @staticmethod
    def _process_directory(directory: Path):
        """Process all images in directory"""
        images = FileScanner.scan(directory, Config.IMAGE_EXTS)
        
        if not images:
            print("No image files found")
            return
        
        print(f"\nProcessing {len(images)} images...\n")
        
        for filepath in images:
            print(f"\n{'='*70}")
            print(f"{filepath.name}")
            print('='*70)
            TextExtractor._extract_from_image(filepath)
    
    @staticmethod
    def _process_file(filepath: Path):
        """Process single image file"""
        if filepath.suffix.lower() not in Config.IMAGE_EXTS:
            print(f"Error: Not a supported image format")
            return
        
        print(f"\n{'='*70}")
        print(f"{filepath.name}")
        print('='*70)
        TextExtractor._extract_from_image(filepath)
    
    @staticmethod
    def _extract_from_image(filepath: Path):
        """Extract text from single image"""
        try:
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img).strip()
            
            if text:
                print(text)
            else:
                print("[No text detected]")
        except Exception as e:
            print(f"Error: {e}")


class FileSearcher:
    """Search files for keywords"""
    
    @staticmethod
    def find_word():
        """Search directory for word in documents"""
        if not DOCUMENT_AVAILABLE:
            print("Warning: Some document types may not be searchable")
            print("Install: pip install PyPDF2 python-docx python-magic chardet")
        
        directory = PathUtils.get_valid_path("Enter directory to search: ")
        if not directory or not directory.is_dir():
            print("Error: Invalid directory")
            return
        
        keyword = input("Enter keyword to search for: ").strip()
        if not keyword:
            print("Error: No keyword provided")
            return
        
        print(f"\nSearching for '{keyword}' in {directory}...\n")
        
        results, total = FileSearcher._search_directory(directory, keyword)
        FileSearcher._display_results(results, total, keyword)
    
    @staticmethod
    def _search_directory(directory: Path, keyword: str) -> Tuple[Dict, int]:
        """Search all supported documents in directory"""
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        results = defaultdict(lambda: defaultdict(list))
        total_matches = 0
        
        all_docs = Config.DOCUMENT_EXTS | Config.CODE_EXTS
        files = FileScanner.scan(directory, all_docs, recursive=True)
        
        print(f"Scanning {len(files)} files...")
        
        for filepath in files:
            matches = FileSearcher._search_file(filepath, pattern)
            if matches:
                results[str(filepath.parent)][filepath.name] = matches
                total_matches += len(matches)
        
        return results, total_matches
    
    @staticmethod
    def _search_file(filepath: Path, pattern: re.Pattern) -> List[Tuple[int, str]]:
        """Search single file for pattern"""
        matches = []
        
        try:
            if filepath.suffix == '.pdf' and DOCUMENT_AVAILABLE:
                matches = FileSearcher._search_pdf(filepath, pattern)
            elif filepath.suffix == '.docx' and DOCUMENT_AVAILABLE:
                matches = FileSearcher._search_docx(filepath, pattern)
            else:
                matches = FileSearcher._search_text(filepath, pattern)
        except Exception as e:
            print(f"Error reading {filepath.name}: {e}")
        
        return matches
    
    @staticmethod
    def _search_text(filepath: Path, pattern: re.Pattern) -> List[Tuple[int, str]]:
        """Search text file (streaming to avoid OOM on large files)"""
        matches = []

        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            matches.append((i, line.strip()))
                break
            except (UnicodeDecodeError, LookupError):
                continue
            except Exception:
                break

        return matches
    
    @staticmethod
    def _search_pdf(filepath: Path, pattern: re.Pattern) -> List[Tuple[str, str]]:
        """Search PDF file"""
        matches = []
        
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        for i, line in enumerate(text.split('\n'), 1):
                            if pattern.search(line):
                                matches.append((f"Page {page_num}, Line {i}", line.strip()))
        except Exception:
            pass
        
        return matches
    
    @staticmethod
    def _search_docx(filepath: Path, pattern: re.Pattern) -> List[Tuple[str, str]]:
        """Search DOCX file"""
        matches = []
        
        try:
            doc = docx.Document(filepath)
            for para_num, para in enumerate(doc.paragraphs, 1):
                if pattern.search(para.text):
                    matches.append((f"Paragraph {para_num}", para.text.strip()))
        except Exception:
            pass
        
        return matches
    
    @staticmethod
    def _display_results(results: Dict, total: int, keyword: str):
        """Display search results"""
        if not results:
            print("No matches found")
            return
        
        print(f"\nTotal matches: {total}")
        print("=" * 80)
        
        for directory, files in sorted(results.items()):
            print(f"\nDirectory: {directory}")
            print("-" * 80)
            for filename, matches in sorted(files.items()):
                print(f"  File: {filename}")
                for location, content in matches[:5]:  # Limit to 5 matches per file
                    print(f"    {location}: {content[:100]}")
                if len(matches) > 5:
                    print(f"    ... and {len(matches) - 5} more matches")
            print()


class KeywordProcessor:
    """Keyword-based file operations"""
    
    @staticmethod
    def extract_lines():
        """Extract lines containing keyword"""
        location = PathUtils.get_valid_path("Directory or file path: ")
        if not location:
            return
        
        keyword = input("Enter keyword: ").strip()
        if not keyword:
            print("Error: No keyword provided")
            return
        
        recursive = False
        if location.is_dir():
            recursive = UserInput.yes_no("Apply recursively?")
        
        files = FileScanner.scan(location, recursive=recursive)
        
        if not files:
            print("No files found")
            return
        
        print(f"\nProcessing {len(files)} files...\n")
        
        for filepath in files:
            try:
                KeywordProcessor._extract_from_file(filepath, keyword)
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
    
    @staticmethod
    def _extract_from_file(filepath: Path, keyword: str):
        """Extract lines containing keyword from file"""
        with open(filepath, 'rb') as f:
            lines = f.readlines()
        
        keyword_bytes = keyword.encode('utf-8')
        filtered = [line for line in lines if keyword_bytes in line]
        
        if filtered:
            output_path = filepath.parent / f"{filepath.stem}_filtered.txt"
            with open(output_path, 'wb') as f:
                f.writelines(filtered)
            print(f"Saved: {output_path}")
    
    @staticmethod
    def replace_keyword():
        """Replace keyword in files"""
        directory = PathUtils.get_valid_path("Directory path: ")
        if not directory or not directory.is_dir():
            return
        
        recursive = UserInput.yes_no("Apply recursively?")
        old_text = input("Text to replace: ").strip()
        new_text = input("Replace with: ").strip()
        
        if not old_text:
            print("Error: No text to replace provided")
            return
        
        files = FileScanner.scan(directory, recursive=recursive)
        modified = 0
        
        print(f"\nProcessing {len(files)} files...\n")
        
        for filepath in files:
            try:
                if KeywordProcessor._replace_in_file(filepath, old_text, new_text):
                    print(f"Modified: {filepath}")
                    modified += 1
            except Exception as e:
                print(f"Error: {filepath}: {e}")
        
        print(f"\nModified {modified} out of {len(files)} files")
    
    @staticmethod
    def _replace_in_file(filepath: Path, old_text: str, new_text: str) -> bool:
        """Replace text in single file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            if old_text in content:
                updated = content.replace(old_text, new_text)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(updated)
                return True
        except Exception:
            pass
        
        return False


class FontExtractor:
    """Extract and download web fonts from URLs"""

    @staticmethod
    def extract_fonts():
        """Extract fonts from a webpage URL"""
        if not FONT_AVAILABLE:
            print("Error: Required libraries not installed.")
            print("Run: pip install requests beautifulsoup4 cssutils")
            return

        url = input("Enter webpage URL: ").strip()
        if not url:
            print("Error: No URL provided")
            return

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        font_types = UserInput.get_choice(
            "Font formats to download:\n1 = TTF only\n2 = All formats (TTF, OTF, WOFF, WOFF2, EOT)\nEnter 1 or 2: ",
            ['1', '2']
        )
        all_formats = (font_types == '2')

        dest_folder = Path.home() / "Downloads" / "Fonts"
        dest_folder.mkdir(parents=True, exist_ok=True)

        print(f"\nFetching webpage: {url}\n")
        FontExtractor._extract_from_url(url, dest_folder, all_formats)

    @staticmethod
    def _get_target_extensions(all_formats: bool) -> Set[str]:
        """Return the set of font extensions to look for"""
        if all_formats:
            return {'.ttf', '.otf', '.woff', '.woff2', '.eot'}
        return {'.ttf'}

    @staticmethod
    def _extract_fonts_from_css(css_text: str, base_url: str, extensions: Set[str]) -> List[str]:
        """Extract font URLs from CSS text"""
        fonts = []

        try:
            sheet = cssutils.parseString(css_text)
            for rule in sheet:
                if rule.type == rule.FONT_FACE_RULE:
                    for prop in rule.style:
                        if prop.name == 'src':
                            urls = re.findall(r'url\(["\']?([^"\')]+)["\']?\)', prop.value)
                            for url in urls:
                                if not url.startswith('data:'):
                                    ext = os.path.splitext(url.split('?')[0])[1].lower()
                                    if ext in extensions:
                                        fonts.append(urljoin(base_url, url))
        except Exception:
            pass

        # Backup regex pass for any missed font URLs
        ext_pattern = '|'.join(re.escape(e) for e in extensions)
        pattern = rf'url\(["\']?([^"\')]+(?:{ext_pattern}))["\']?\)'
        for url in re.findall(pattern, css_text, re.IGNORECASE):
            if not url.startswith('data:'):
                full_url = urljoin(base_url, url)
                if full_url not in fonts:
                    fonts.append(full_url)

        return fonts

    @staticmethod
    def _download_font(url: str, dest_folder: Path) -> bool:
        """Download a single font file"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            parsed = urlparse(url)
            filename = os.path.basename(parsed.path).split('?')[0]

            # Ensure a font extension is present
            if not any(filename.lower().endswith(ext) for ext in Config.FONT_EXTS):
                filename += '.ttf'

            filepath = PathUtils.ensure_unique(dest_folder / filename)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded: {filepath.name}")
            return True

        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return False

    @staticmethod
    def _extract_from_url(url: str, dest_folder: Path, all_formats: bool):
        """Fetch a page and collect all matching font URLs"""
        extensions = FontExtractor._get_target_extensions(all_formats)
        all_fonts: Set[str] = set()

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Inline <style> blocks
            for style_tag in soup.find_all('style'):
                fonts = FontExtractor._extract_fonts_from_css(
                    style_tag.string or '', url, extensions
                )
                all_fonts.update(fonts)

            # 2. External stylesheets
            for link in soup.find_all('link', rel='stylesheet'):
                css_url = urljoin(url, link.get('href', ''))
                try:
                    css_response = requests.get(css_url, timeout=10)
                    css_response.raise_for_status()
                    fonts = FontExtractor._extract_fonts_from_css(
                        css_response.text, css_url, extensions
                    )
                    all_fonts.update(fonts)
                except Exception as e:
                    print(f"Warning: Could not fetch CSS from {css_url}: {e}")

            # 3. Google Fonts / font service links
            for link in soup.find_all('link'):
                href = link.get('href', '')
                if 'fonts.googleapis.com' in href or 'fonts.gstatic.com' in href:
                    try:
                        font_response = requests.get(href, timeout=10)
                        fonts = FontExtractor._extract_fonts_from_css(
                            font_response.text, href, extensions
                        )
                        all_fonts.update(fonts)
                    except Exception as e:
                        print(f"Warning: Could not fetch fonts from {href}: {e}")

            if not all_fonts:
                fmt_label = "fonts" if all_formats else "TTF fonts"
                print(f"No {fmt_label} found on this webpage.")
                return

            fmt_label = "font file(s)" if all_formats else "TTF font file(s)"
            print(f"Found {len(all_fonts)} {fmt_label}")
            print(f"Downloading to: {dest_folder}\n")

            success_count = sum(
                FontExtractor._download_font(font_url, dest_folder)
                for font_url in all_fonts
            )

            print(f"\nSuccessfully downloaded {success_count}/{len(all_fonts)} fonts")
            print(f"Location: {dest_folder}")

        except Exception as e:
            print(f"Error: {e}")


def show_menu(commands: List[str], selected: int):
    """Display menu with highlighted selection"""
    clear()
    print("\033[1m  Document Tools\033[0m")
    print("  --------------\n")
    
    for i, cmd in enumerate(commands):
        if i == selected:
            print(f"\033[1m➤ {cmd}\033[0m\n")
        else:
            print(f"  {cmd}\n")


def run_command(cmd: str):
    """Execute the selected command"""
    clear()
    
    try:
        if cmd == "Adjust Audio Volume":
            AudioProcessor.adjust_volume()
        elif cmd == "Compare Documents":
            DocumentProcessor.compare_documents()
        elif cmd == "Duplicate Line Remover":
            DuplicateRemover.remove_duplicates()
        elif cmd == "Extract Text":
            TextExtractor.extract_text()
        elif cmd == "Find Word":
            FileSearcher.find_word()
        elif cmd == "Keyword Line Extractor":
            KeywordProcessor.extract_lines()
        elif cmd == "Replace Keyword":
            KeywordProcessor.replace_keyword()
        elif cmd == "Web Font Extractor":
            FontExtractor.extract_fonts()
        elif cmd == "Quit":
            clear()
            print("\n\033[1mExiting Document Tools\033[0m\n")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to return to menu...")


def main():
    """Main program loop"""
    commands = [
        "Adjust Audio Volume",
        "Compare Documents",
        "Duplicate Line Remover",
        "Extract Text",
        "Find Word",
        "Keyword Line Extractor",
        "Replace Keyword",
        "Web Font Extractor",
        "Quit"
    ]
    
    selected = 0
    
    while True:
        show_menu(commands, selected)
        
        key = get_key()
        
        if key == 'UP':
            selected = (selected - 1) % len(commands)
        elif key == 'DOWN':
            selected = (selected + 1) % len(commands)
        elif key == 'ENTER':
            run_command(commands[selected])
        elif key == 'CTRL_C':
            clear()
            print("\n\033[1mExiting Document Tools\033[0m\n")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        print("\n\033[1mExiting Document Tools\033[0m\n")
