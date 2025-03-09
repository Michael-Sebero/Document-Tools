import os
import re
import magic
from collections import defaultdict
import PyPDF2
import docx
import zipfile
import csv
import chardet

def search_directory_for_word(directory, search_word):
    # Define document extensions only
    document_extensions = {
        'text': ('.txt', '.md', '.log', '.conf'),
        'code': ('.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.sh', '.bat', '.ps1', '.sql'),
        'data': ('.json', '.xml', '.yaml', '.yml', '.ini', '.cfg', '.properties', '.csv', '.tsv'),
        'office': ('.pdf', '.docx', '.doc', '.odt', '.rtf', '.pptx', '.xlsx', '.xls')
    }
    
    # Flatten the document extensions
    all_document_extensions = []
    for ext_group in document_extensions.values():
        all_document_extensions.extend(ext_group)
    
    results = defaultdict(lambda: defaultdict(list))
    total_matches = 0
    files_processed = 0
    files_skipped = 0

    # Precompile the regex pattern for better performance
    pattern = re.compile(re.escape(search_word), re.IGNORECASE)

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1].lower()
            
            # Skip non-document files
            if file_extension not in all_document_extensions:
                # Additional check using magic for files without extensions
                if not file_extension:
                    try:
                        file_type = magic.from_file(file_path, mime=True)
                        # Only process if it's a text or document type
                        if not (file_type.startswith('text/') or 
                                file_type == 'application/pdf' or
                                'document' in file_type or
                                'spreadsheet' in file_type):
                            files_skipped += 1
                            continue
                    except Exception:
                        files_skipped += 1
                        continue
                else:
                    files_skipped += 1
                    continue
            
            try:
                # Process files based on their extensions
                if file_extension in document_extensions['text'] or file_extension in document_extensions['code'] or file_extension in document_extensions['data']:
                    total_matches += process_text_file(file_path, pattern, results, root, file)
                    files_processed += 1
                elif file_extension == '.pdf':
                    total_matches += process_pdf_file(file_path, pattern, results, root, file)
                    files_processed += 1
                elif file_extension == '.docx':
                    total_matches += process_docx_file(file_path, pattern, results, root, file)
                    files_processed += 1
                elif file_extension == '.odt':
                    total_matches += process_odt_file(file_path, pattern, results, root, file)
                    files_processed += 1
                elif file_extension == '.csv' or file_extension == '.tsv':
                    total_matches += process_csv_file(file_path, pattern, results, root, file)
                    files_processed += 1
                elif file_extension in ('.xlsx', '.xls'):
                    # Skip Excel files for now as they require additional libraries
                    print(f"Skipping Excel file {file_path} (support not implemented)")
                    files_skipped += 1
                else:
                    # Default to text processing for other document types
                    total_matches += process_text_file(file_path, pattern, results, root, file)
                    files_processed += 1
            
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
                files_skipped += 1
                continue

    return results, total_matches, files_processed, files_skipped

def detect_encoding(file_path):
    """Detect the encoding of a file."""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read(1024))  # Only read a portion to speed up detection
    return result['encoding'] or 'utf-8'  # Fallback to utf-8 if detection fails

def process_text_file(file_path, pattern, results, root, file):
    """Process a text file and search for the pattern."""
    match_count = 0
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                results[root][file].append((i, line.strip()))
                match_count += 1
    except Exception as e:
        print(f"Error reading text file {file_path}: {str(e)}")
    
    return match_count

def process_pdf_file(file_path, pattern, results, root, file):
    """Process a PDF file and search for the pattern."""
    match_count = 0
    try:
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for i, line in enumerate(lines, 1):
                        if pattern.search(line):
                            line_number = f"Page {page_num}, Line {i}"
                            results[root][file].append((line_number, line.strip()))
                            match_count += 1
    except Exception as e:
        print(f"Error reading PDF file {file_path}: {str(e)}")
    
    return match_count

def process_docx_file(file_path, pattern, results, root, file):
    """Process a DOCX file and search for the pattern."""
    match_count = 0
    try:
        doc = docx.Document(file_path)
        for para_num, para in enumerate(doc.paragraphs, 1):
            text = para.text
            if pattern.search(text):
                results[root][file].append((f"Paragraph {para_num}", text.strip()))
                match_count += 1
    except Exception as e:
        print(f"Error reading DOCX file {file_path}: {str(e)}")
    
    return match_count

def process_odt_file(file_path, pattern, results, root, file):
    """Process an ODT file and search for the pattern."""
    match_count = 0
    try:
        with zipfile.ZipFile(file_path) as odt_file:
            content = odt_file.read('content.xml').decode('utf-8')
            # Basic XML parsing - a more robust approach would use proper XML parsing
            content = re.sub(r'<[^>]+>', ' ', content)  # Remove XML tags
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    results[root][file].append((i, line.strip()))
                    match_count += 1
    except Exception as e:
        print(f"Error reading ODT file {file_path}: {str(e)}")
    
    return match_count

def process_csv_file(file_path, pattern, results, root, file):
    """Process a CSV file and search for the pattern."""
    match_count = 0
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding, errors='replace') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row_num, row in enumerate(csv_reader, 1):
                row_text = ','.join(row)
                if pattern.search(row_text):
                    results[root][file].append((f"Row {row_num}", row_text.strip()))
                    match_count += 1
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {str(e)}")
    
    return match_count

def highlight_match(text, search_word):
    """Highlight the search word in the text."""
    pattern = re.compile(re.escape(search_word), re.IGNORECASE)
    return pattern.sub(lambda m: f'\033[91m{m.group(0)}\033[0m', text)

def display_results(results, total_matches, search_word, files_processed, files_skipped):
    if not results:
        print("No matches found.")
        return

    print(f"Total matches found: {total_matches}")
    print(f"Files processed: {files_processed}")
    print(f"Files skipped: {files_skipped}")
    print("=" * 80)

    for directory, files in sorted(results.items()):
        print(f"\nDirectory: {directory}")
        print("-" * 80)
        for file, matches in sorted(files.items()):
            print(f"  File: {file}")
            for line_num, line_content in matches:
                print(f"    Line {line_num}: {line_content}")
                highlighted_line = highlight_match(line_content, search_word)
                print(f"      Matched: {highlighted_line}")
            print("-" * 40)
        print("=" * 80)

def print_document_types():
    """Print the types of documents being searched."""
    print("Searching through the following document types:")
    print("  • Text documents: .txt, .md, .log, .conf")
    print("  • Code files: .py, .js, .html, .css, .java, .c, .cpp, .h, .sh, .bat, .ps1, .sql")
    print("  • Data files: .json, .xml, .yaml, .yml, .ini, .cfg, .properties, .csv, .tsv")
    print("  • Office documents: .pdf, .docx, .doc, .odt, .rtf, .pptx, .xlsx, .xls")
    print()

if __name__ == "__main__":
    try:
        directory = input("Enter the directory to search: ")
        search_word = input("Enter the word to search for: ")
        
        if not os.path.isdir(directory):
            print(f"Error: '{directory}' is not a valid directory.")
            exit(1)
        
        print_document_types()    
        print(f"Searching for '{search_word}' in '{directory}'...")
        results, total_matches, files_processed, files_skipped = search_directory_for_word(directory, search_word)
        display_results(results, total_matches, search_word, files_processed, files_skipped)
    
    except KeyboardInterrupt:
        print("\nSearch cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
