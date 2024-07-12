import os
from pathlib import Path

class DirectorySetup:
    def __init__(self, root_dir=None):
        # If no root directory is provided, use the current working directory
        if root_dir is None:
            self.root_dir = Path.cwd()  # Gets the current working directory
        else:
            self.root_dir = Path(root_dir)  # Use the provided root directory
        
        # Define the path for the recorded_data directory
        self.recorded_data_dir = self.root_dir / "recorded_data"

    def create_directory_structure(self):
        # Define the list of directories to be created
        directories = [
            self.recorded_data_dir,
            self.recorded_data_dir / "autofocus",
            self.recorded_data_dir / "captured_images",
            self.recorded_data_dir / "identified_cell_images"
        ]

        # Create each directory in the list
        for directory in directories:
            # Create the directory and its parents if they don't exist
            # If the directory already exists, this won't raise an error
            directory.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {directory}")

    def get_directory(self, name):
        # Return the path of a subdirectory within recorded_data
        return self.recorded_data_dir / name

def setup_directories(root_dir=None):
    # Create a DirectorySetup instance
    dir_setup = DirectorySetup(root_dir)
    # Create the directory structure
    dir_setup.create_directory_structure()
    # Return the DirectorySetup instance for further use if needed
    return dir_setup

# This block is executed when the script is run directly
if __name__ == "__main__":
    setup_directories()

# Note: To add a new directory to the structure, follow these steps:
# 1. In the create_directory_structure method, add a new entry to the 'directories' list.
#    For example, to add a 'new_folder' directory:
#    self.recorded_data_dir / "new_folder"
# 2. If you need to access this new directory elsewhere in your code, you can use:
#    dir_setup.get_directory("new_folder")
# 3. Remember to create an instance of DirectorySetup in your main script:
#    dir_setup = setup_directories()
# This will ensure that your new directory is created along with the others.