import os

def filter_and_save(file_path, keyword, recursive=False):
    def process_file(file_path):
        try:
            with open(file_path, 'rb') as file:
                lines = file.readlines()

            filtered_lines = [line for line in lines if keyword.encode('utf-8') in line]

            if filtered_lines:
                output_path = os.path.splitext(file_path)[0] + "_filtered.txt"
                with open(output_path, 'wb') as output_file:
                    output_file.writelines(filtered_lines)
                print(f"Filtered content saved to: {output_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def process_directory(dir_path):
        for entry in os.scandir(dir_path):
            if entry.is_file():
                process_file(entry.path)
            elif entry.is_dir() and recursive:
                process_directory(entry.path)

    if os.path.isfile(file_path):
        process_file(file_path)
    elif os.path.isdir(file_path):
        process_directory(file_path)
    else:
        print("Error: The specified path does not exist.")

def main():
    path = input("Directory path: ")
    keyword = input("Enter the keyword: ")
    recursive = input("Apply recursively? (y/n): ").lower() == 'y
