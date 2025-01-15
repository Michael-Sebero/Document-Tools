import os

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.readlines()

def find_and_write_common_and_diff_lines(file1_path, file2_path, output_path):
    # Extract file names from the paths
    file1_name = os.path.basename(file1_path)
    file2_name = os.path.basename(file2_path)

    file1_lines = set(read_file(file1_path))
    file2_lines = set(read_file(file2_path))

    common_lines = file1_lines.intersection(file2_lines)
    differing_lines_file1 = file1_lines - common_lines
    differing_lines_file2 = file2_lines - common_lines

    border = "=" * 20

    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write(f"{border} Common Lines {border}\n")
        output_file.write('\n'.join(sorted(common_lines)))
        
        output_file.write(f"\n\n{border} Differing Lines in {file1_name} {border}\n")
        output_file.write('\n'.join(sorted(differing_lines_file1)))
        
        output_file.write(f"\n\n{border} Differing Lines in {file2_name} {border}\n")
        output_file.write('\n'.join(sorted(differing_lines_file2)))

if __name__ == "__main__":
    # Get input file paths from the user and strip any extra whitespace
    file1_path = input("Enter the file path of the first document: ").strip()
    file2_path = input("Enter the file path of the second document: ").strip()

    # Get the user's desktop directory
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')

    # Set the default output path to the desktop
    output_path = os.path.join(desktop_path, "output.txt")

    # Find and write the common and differing lines to the output file
    find_and_write_common_and_diff_lines(file1_path, file2_path, output_path)

    print(f"Output file has been created on your desktop: {output_path}")
