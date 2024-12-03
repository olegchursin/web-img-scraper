import os
from pathlib import Path
from rembg import remove
from PIL import Image


class BackgroundRemover:
    def __init__(self, input_folder, output_folder=None):
        """
        Initialize the background remover.
        
        :param input_folder: Path to the folder containing images to process
        :param output_folder: Path to save background-removed images (defaults to 'background_removed' 
                               in the same directory as input folder)
        """
        # Validate input folder
        self.input_folder = Path(input_folder)
        if not self.input_folder.is_dir():
            raise ValueError(f"Input folder does not exist: {input_folder}")

        # Set output folder, creating if not specified
        if output_folder is None:
            self.output_folder = self.input_folder.parent / 'background_removed'
        else:
            self.output_folder = Path(output_folder)

        # Create output folder if it doesn't exist
        self.output_folder.mkdir(parents=True, exist_ok=True)

        # Supported image extensions
        self.image_extensions = {'.png', '.jpg',
                                 '.jpeg', '.webp', '.bmp', '.tiff'}

    def remove_background(self, input_path, output_path=None):
        """
        Remove background from a single image.
        
        :param input_path: Path to the input image
        :param output_path: Path to save the background-removed image (optional)
        :return: Path to the saved image
        """
        try:
            # Open the input image
            with Image.open(input_path) as img:
                # Remove background
                output = remove(img)

                # Determine output path if not provided
                if output_path is None:
                    output_path = self.output_folder / \
                        f"nobg_{input_path.stem}.png"

                # Save the image with transparency
                output.save(output_path)

                print(f"Processed: {input_path.name} -> {output_path.name}")
                return output_path

        except Exception as e:
            print(f"Error processing {input_path}: {e}")
            return None

    def batch_remove_backgrounds(self, recursive=False):
        """
        Remove backgrounds from all images in the input folder.
        
        :param recursive: Whether to search for images in subfolders
        :return: List of processed image paths
        """
        processed_images = []

        # Determine search method based on recursive flag
        if recursive:
            file_search = self.input_folder.rglob('*')
        else:
            file_search = self.input_folder.glob('*')

        # Process each file
        for file_path in file_search:
            # Check if file is an image
            if file_path.is_file() and file_path.suffix.lower() in self.image_extensions:
                output_path = self.output_folder / f"nobg_{file_path.stem}.png"

                # Skip if output already exists
                if output_path.exists():
                    print(f"Skipping existing: {file_path.name}")
                    continue

                # Remove background
                result = self.remove_background(file_path)
                if result:
                    processed_images.append(result)

        print(f"\nProcessed {len(processed_images)} images.")
        return processed_images


def main():
    # Example usage
    try:
        # Specify the input folder containing images
        input_folder = 'downloaded_images/src'

        # Optional: specify a different output folder
        # output_folder = '/path/to/output/folder'

        # Create background remover instance
        remover = BackgroundRemover(input_folder)

        # Remove backgrounds from all images
        processed_images = remover.batch_remove_backgrounds(recursive=False)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    main()

# Requirements (install via pip):
# pip install pillow rembg
