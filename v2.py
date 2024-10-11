import os
import sys
import argparse
import urllib.request
import subprocess
import torch
import torchvision.transforms as transforms
from PIL import Image
#restormer
def install_dependencies():
    dependencies = [
        "torch",
        "torchvision",
        "opencv-python",
        "einops",
        "timm"
    ]
    for dep in dependencies:
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

def setup_restormer():
    restormer_path = os.path.abspath("Restormer")
    if not os.path.exists(restormer_path):
        print("Error: Restormer directory not found. Please ensure you've cloned the repository.")
        sys.exit(1)
    if restormer_path not in sys.path:
        sys.path.append(restormer_path)

def download_weights(url, save_path):
    if not os.path.exists(save_path):
        print(f"Downloading weights from {url}")
        urllib.request.urlretrieve(url, save_path)
        print(f"Weights downloaded and saved to {save_path}")
    else:
        print(f"Weights file already exists at {save_path}")

def load_model(weights_path):
    from restormer import Restormer
    model = Restormer()
    model.load_state_dict(torch.load(weights_path, map_location=torch.device('cpu')))
    model.eval()
    return model

def preprocess_image(image_path):
    image = Image.open(image_path).convert('RGB')
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])
    return transform(image).unsqueeze(0)

def enhance_image(model, image_tensor):
    with torch.no_grad():
        enhanced_image = model(image_tensor)
    return enhanced_image

def postprocess_image(enhanced_image):
    to_pil = transforms.ToPILImage()
    enhanced_image = to_pil(enhanced_image.squeeze(0).clamp(0, 1))
    return enhanced_image

def main(input_path, output_path, task="denoising"):
    # Install dependencies
    print("Installing dependencies...")
    install_dependencies()

    # Setup Restormer
    print("Setting up Restormer...")
    setup_restormer()

    # Set up weights path and URL based on the task
    weights_dir = os.path.join("Restormer", "pretrained_models")
    weights_filename = f"image_{task}.pth"
    weights_path = os.path.join(weights_dir, weights_filename)
    weights_url = f"https://github.com/swz30/Restormer/releases/download/v1.0/pretrained_models/{weights_filename}"

    # Create directory for weights if it doesn't exist
    os.makedirs(weights_dir, exist_ok=True)

    # Download weights if they don't exist
    download_weights(weights_url, weights_path)

    # Load the Restormer model
    print("Loading Restormer model...")
    model = load_model(weights_path)
    
    # Preprocess the input image
    print("Preprocessing input image...")
    input_tensor = preprocess_image(input_path)
    
    # Enhance the image
    print("Enhancing image...")
    enhanced_tensor = enhance_image(model, input_tensor)
    
    # Postprocess and save the enhanced image
    print("Postprocessing and saving enhanced image...")
    enhanced_image = postprocess_image(enhanced_tensor)
    enhanced_image.save(output_path)
    
    print(f"Enhanced image saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance an image using Restormer")
    parser.add_argument("input_path", help="Path to the input image")
    parser.add_argument("output_path", help="Path to save the enhanced image")
    parser.add_argument("--task", default="denoising", choices=["denoising", "deraining", "deblurring"], help="Image restoration task")
    
    args = parser.parse_args()
    
    main(args.input_path, args.output_path, args.task)