import os
import glob
import pyzipper
import tarfile
import tempfile
import shutil

# Ask the user for the directory, password, and keyword
directory = input("Enter the directory of the archive: ")
password = input("Enter archive password (ignore if none): ")
keyword = input("Enter keyword: ")

# Get a list of all zip and tar files in the specified directory
files = glob.glob(os.path.join(directory, '*.zip')) + glob.glob(os.path.join(directory, '*.tar'))

# Create a temporary directory
temp_dir = tempfile.mkdtemp()

# List to store files where the keyword is found
found_files = []

# Iterate over each file
for file in files:
    # Check if the file is a tar file
    if tarfile.is_tarfile(file):
        # Open the tar file
        with tarfile.open(file, 'r') as tar_ref:
            # Extract all contents of the tar file to the temporary directory
            tar_ref.extractall(path=temp_dir)
    else:
        # Extract all contents of the zip file to the temporary directory
        with pyzipper.AESZipFile(file, 'r', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zip_ref:
            if password:
                zip_ref.extractall(pwd=str.encode(password), path=temp_dir)
    # Iterate over each file in the temporary directory
    for root, dirs, files in os.walk(temp_dir):
        for name in files:
            file_path = os.path.join(root, name)
            # Read the contents of the file
            with open(file_path, 'r') as file:
                content = file.read()
                # Check if the keyword is in the file's contents
                if keyword in content:
                    found_files.append((file, file_path))
                    print(f"Keyword '{keyword}' found in file {file_path}")

# Remove the temporary directory
shutil.rmtree(temp_dir)

if not found_files:
    print(f"No files found containing the keyword '{keyword}'")
