import os
from pydub import AudioSegment

def adjust_volume(input_path, output_folder, adjustment_percentage, increase_volume):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the audio file
    audio = AudioSegment.from_file(input_path)
    
    # Calculate the adjustment in decibels
    adjustment_db = adjustment_percentage if increase_volume else -adjustment_percentage
    adjusted_audio = audio + adjustment_db
    
    # Get the original file format from the file extension
    file_extension = os.path.splitext(input_path)[1][1:]  # Removes the leading dot
    output_path = os.path.join(output_folder, os.path.basename(input_path))
    
    # Save the adjusted audio file in the original format
    adjusted_audio.export(output_path, format=file_extension)
    print(f"File saved to {output_path}")

def process_input(input_path, adjustment_percentage, increase_volume):
    # Determine the output folder based on the input path directory
    base_dir = os.path.dirname(input_path) if os.path.isfile(input_path) else input_path
    output_folder = os.path.join(base_dir, "Output")

    # Check if input path is a directory or file
    if os.path.isdir(input_path):
        # Process each file in the directory
        for filename in os.listdir(input_path):
            if filename.endswith(('.mp3', '.wav', '.flac', '.ogg')):
                file_path = os.path.join(input_path, filename)
                adjust_volume(file_path, output_folder, adjustment_percentage, increase_volume)
    elif os.path.isfile(input_path):
        # Process a single file
        adjust_volume(input_path, output_folder, adjustment_percentage, increase_volume)
    else:
        print("Invalid path. Please enter a valid file or directory path.")

if __name__ == "__main__":
    # Get user input
    input_path = input("Enter the file or directory path: ").strip()
    try:
        # Ask if the user wants to reduce or increase volume
        choice = input("Choose an option:\n1 = Reduce volume by percent\n2 = Increase volume by percent\nEnter 1 or 2: ").strip()
        if choice not in ['1', '2']:
            raise ValueError("Please enter either 1 or 2.")
        
        increase_volume = (choice == '2')
        adjustment_percentage = float(input("Enter adjustment percentage (1-100): ").strip())
        if not (1 <= adjustment_percentage <= 100):
            raise ValueError("Adjustment percentage must be between 1 and 100.")
        
        process_input(input_path, adjustment_percentage, increase_volume)
    except ValueError as e:
        print(e)
