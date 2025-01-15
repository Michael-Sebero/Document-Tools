import os

def replace_in_file(file_path, old_text, new_text):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if old_text in content:
            updated_content = content.replace(old_text, new_text)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False

def process_directory(directory_path, old_text, new_text, recursive=False):
    modified_files = 0
    total_files = 0
    
    def process_dir(dir_path):
        nonlocal modified_files, total_files
        
        for entry in os.scandir(dir_path):
            if entry.is_file():
                total_files += 1
                if replace_in_file(entry.path, old_text, new_text):
                    modified_files += 1
                    print(f"Modified: {entry.path}")
            elif entry.is_dir() and recursive:
                process_dir(entry.path)
    
    process_dir(directory_path)
    return modified_files, total_files

def main():
    directory = input("Directory path: ")
    recursive = input("Apply recursively? (y/n): ").lower() == 'y'
    old_text = input("Text to replace: ")
    new_text = input("Replace with: ")

    if not os.path.isdir(directory):
        print("Error: Invalid directory path")
        return

    modified, total = process_directory(directory, old_text, new_text, recursive)
    print(f"\nComplete! Modified {modified} out of {total} files")

if __name__ == "__main__":
    main()
