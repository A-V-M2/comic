import urllib.request

def download_weights(url, save_path):
    if not os.path.exists(save_path):
        print(f"Downloading weights from {url}")
        try:
            urllib.request.urlretrieve(url, save_path)
            print(f"Weights downloaded and saved to {save_path}")
        except urllib.error.URLError as e:
            print(f"Error downloading weights: {e}")
            print("Please check your internet connection and try again.")
            sys.exit(1)
    else:
        print(f"Weights file already exists at {save_path}")