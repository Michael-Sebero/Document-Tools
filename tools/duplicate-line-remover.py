import os

def sort_and_save_unique_lines(input_location, recursive=False):
    def process_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as input_file:
                lines = input_file.readlines()

            unique_lines = sorted(set(lines))

            # Create output filename
            input_file_name = os.path.basename(file_path)
            output_file_path = os.path.join(os.path.dirname(file_path), f"output_{input_file_name}")

            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                output_file.writelines(unique_lines)

            print(f"Processed: {file_path} -> {output_file_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def process_directory(dir_path):
        for entry in os.scandir(dir_path):
            if entry.is_file():
                process_file(entry.path)
            elif entry.is_dir() and recursive:
                process_directory(entry.path)

    if os.path.isfile(input_location):
        process_file(input_location)
    elif os.path.isdir(input_location):
        process_directory(input_location)
    else:
        print("Error: The specified path does not exist.")

if __name__ == "__main__":
    location = input("Directory path: ")
    recursive = input("Apply recursively? (y/n): ").lower() == 'y'
    
    sort_and_save_unique_lines(location, recursive)
