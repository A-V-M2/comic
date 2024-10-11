import torch
from diffusers import StableDiffusionPipeline
import gc
import logging

logger = logging.getLogger(__name__)

class StableDiffusionModel:
    def __init__(self, model_path="CompVis/stable-diffusion-v1-4"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        self.pipeline = StableDiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float16, safety_checker=None)
        self.pipeline = self.pipeline.to(self.device)
        self.pipeline.enable_attention_slicing(1)
        self.pipeline.enable_vae_slicing()

    def generate_image(self, prompt, negative_prompt=None, num_inference_steps=10, guidance_scale=7.5, width=640, height=960):
        logger.info(f"Generating image with prompt: {prompt}")
        logger.info(f"Negative prompt: {negative_prompt}")
        logger.info(f"Inference steps: {num_inference_steps}, Guidance scale: {guidance_scale}")
        logger.info(f"Image size: {width}x{height}")
        
        try:
            with torch.no_grad():
                with torch.autocast("cuda"):
                    output = self.pipeline(
                        prompt, 
                        negative_prompt=negative_prompt,
                        num_inference_steps=num_inference_steps, 
                        guidance_scale=guidance_scale,
                        width=width,
                        height=height,
                    )
            
            image = output.images[0]
            
            # Clear CUDA cache
            torch.cuda.empty_cache()
            gc.collect()
            logger.info("CUDA cache cleared.")
            
            return image
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

# Example usage:
if __name__ == "__main__":
    model = StableDiffusionModel()
    prompt = "Superman staring off into distance of Gotham City with castle in the background, full body shot, dynamic pose, bold outlines, vibrant colors, halftone pattern background, birds in the sky, purple and orange sky, comic book style lettering, classic comic book art style"
    negative_prompt = "photorealistic, 3D rendering, smooth gradients, detailed textures, plain background"
    
    image = model.generate_image(prompt, negative_prompt)
    if image:
        image.save("generated_comic.png")
        print("Image saved as generated_comic.png")
    else:
        print("Failed to generate image.")