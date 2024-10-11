import os
import torch
from torch.utils.data import Dataset, DataLoader, Subset
from torchvision import transforms
from tqdm import tqdm
from PIL import Image
from diffusers import AutoencoderKL, UNet2DConditionModel, PNDMScheduler, StableDiffusionPipeline
import gc

CACHED_MODEL_PATH = r'C:\Users\mabhi\Documents\comic\cached_model'
CHECKPOINT_PATH = r'C:\Users\mabhi\Documents\comic\checkpoints'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

class ComicDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.root_dir = os.path.abspath(root_dir)
        self.transform = transform
        self.image_paths = [os.path.join(root, file) for root, _, files in os.walk(self.root_dir) 
                            for file in files if file.lower().endswith(('.png', '.jpg', '.jpeg'))]
        print(f"Found {len(self.image_paths)} images.")

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image

def load_comic_dataset(root_dir, batch_size=1, sample_size=20):
    transform = transforms.Compose([
        transforms.Resize((320, 320)),  # Further reduce resolution
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5])
    ])
    full_dataset = ComicDataset(root_dir=root_dir, transform=transform)
    subset_indices = torch.randperm(len(full_dataset))[:sample_size]
    subset = Subset(full_dataset, subset_indices)
    dataloader = DataLoader(subset, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
    return dataloader

def load_or_create_models():
    if os.path.exists(CACHED_MODEL_PATH):
        print(f"Loading cached model from {CACHED_MODEL_PATH}")
        pipeline = StableDiffusionPipeline.from_pretrained(CACHED_MODEL_PATH, torch_dtype=torch.float16, low_cpu_mem_usage=True)
    else:
        print("Initializing and caching model")
        model_id = "CompVis/stable-diffusion-v1-4"
        pipeline = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, low_cpu_mem_usage=True)
        pipeline.save_pretrained(CACHED_MODEL_PATH)

    pipeline = pipeline.to(device)
    pipeline.enable_attention_slicing(1)
    pipeline.enable_vae_slicing()
    pipeline.unet.enable_gradient_checkpointing()
    pipeline.safety_checker = lambda images, clip_input: (images, [False] * len(images))
    return pipeline

def generate_image(prompt, pipeline):
    with torch.no_grad():
        with torch.autocast(device.type):
            image = pipeline(prompt, num_inference_steps=30, guidance_scale=7.0).images[0]
    return image

def save_checkpoint(pipeline, optimizer, epoch, loss, filename):
    torch.save({
        'epoch': epoch,
        'model_state_dict': pipeline.unet.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
    }, filename)

def load_checkpoint(pipeline, optimizer, filename):
    checkpoint = torch.load(filename)
    pipeline.unet.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    return checkpoint['epoch'], checkpoint['loss']

def main():
    root_dir = r'C:\Users\mabhi\Documents\comic\data\pics\train'
    os.makedirs(CHECKPOINT_PATH, exist_ok=True)
    
    try:
        dataloader = load_comic_dataset(root_dir, batch_size=1, sample_size=40)  # Reduced sample size
        pipeline = load_or_create_models()

        pipeline.unet.to(device)
        pipeline.vae.to(device)
        pipeline.text_encoder.to(device)

        optimizer = torch.optim.AdamW(pipeline.unet.parameters(), lr=1e-6)  # Further reduced learning rate
        
        start_epoch = 0
        if os.path.exists(os.path.join(CHECKPOINT_PATH, 'latest_checkpoint.pth')):
            start_epoch, _ = load_checkpoint(pipeline, optimizer, os.path.join(CHECKPOINT_PATH, 'latest_checkpoint.pth'))
            print(f"Resuming from epoch {start_epoch}")

        num_epochs = 3  # Reduced number of epochs
        gradient_accumulation_steps = 8  # Increased gradient accumulation steps

        for epoch in range(start_epoch, num_epochs):
            total_loss = 0
            for i, batch in enumerate(tqdm(dataloader, desc=f"Epoch {epoch+1}/{num_epochs}")):
                batch = batch.to(device, dtype=torch.float16)
                
                with torch.autocast(device.type):
                    latents = pipeline.vae.encode(batch).latent_dist.sample()
                    latents = latents * pipeline.vae.config.scaling_factor

                    noise = torch.randn_like(latents)
                    timesteps = torch.randint(0, pipeline.scheduler.config.num_train_timesteps, (latents.shape[0],), device=latents.device).long()
                    noisy_latents = pipeline.scheduler.add_noise(latents, noise, timesteps)

                    encoder_hidden_states = pipeline.text_encoder(
                        pipeline.tokenizer([""] * batch.shape[0], return_tensors="pt", padding=True).input_ids.to(device)
                    )[0]
                    
                    noise_pred = pipeline.unet(noisy_latents, timesteps, encoder_hidden_states).sample
                    loss = torch.nn.functional.mse_loss(noise_pred, noise)
                    loss = loss / gradient_accumulation_steps
                
                loss.backward()
                
                if (i + 1) % gradient_accumulation_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad()

                total_loss += loss.item() * gradient_accumulation_steps

                if (i + 1) % 5 == 0:  # Save checkpoint more frequently
                    print(f"Batch {i+1}, Loss: {total_loss / (i+1)}")
                    save_checkpoint(pipeline, optimizer, epoch, total_loss / (i+1), os.path.join(CHECKPOINT_PATH, 'latest_checkpoint.pth'))
                    
                # Clear cache more frequently
                if (i + 1) % 2 == 0:
                    torch.cuda.empty_cache()
                    gc.collect()

            avg_loss = total_loss / len(dataloader)
            print(f"Epoch {epoch+1} completed. Average Loss: {avg_loss}")
            save_checkpoint(pipeline, optimizer, epoch, avg_loss, os.path.join(CHECKPOINT_PATH, f'checkpoint_epoch_{epoch+1}.pth'))

        print("Fine-tuning completed. Saving the final model...")
        pipeline.save_pretrained(CACHED_MODEL_PATH)
        print(f"Fine-tuned model saved to {CACHED_MODEL_PATH}")

        prompt = "A superhero flying through a futuristic city, comic book style"
        image = generate_image(prompt, pipeline)
        image.save("generated_comic.png")
        print("Sample image generated and saved as 'generated_comic.png'")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()