import os
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, GenerationConfig
import re

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv('PROJECT_ID')
LOCATION = os.getenv('LOCATION')

class ComicStoryGenerator:
    def __init__(self):
        self.model = GenerativeModel("gemini-1.0-pro-002")

    def generate_story(self, prompt):
        generation_config = GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            top_k=40,
            max_output_tokens=1000
        )

        response = self.model.generate_content(prompt, generation_config=generation_config)
        return response.text

    def create_comic_tiles(self, story):
        prompt = f"""
        Convert the following story into a series of 10 comic book tiles. Each tile should represent a key scene or moment in the story. Provide a brief description for each tile.

        Story:
        {story}

        Format the output as a numbered list of scenes, like this:
        1. [Scene description]
        2. [Scene description]
        ...
        10. [Scene description]
        """

        response = self.model.generate_content(prompt)
        
        tiles = []
        for line in response.text.split('\n'):
            match = re.match(r'(\d+)\.\s*(.*)', line.strip())
            if match:
                tiles.append({"scene": match.group(2)})
        
        if len(tiles) < 10:
            tiles = self.create_tiles_manually(story)
        
        return tiles

    def create_tiles_manually(self, story):
        tiles = []
        sentences = re.split(r'(?<=[.!?])\s+', story)
        
        while len(sentences) < 10:
            sentences.append("The story continues...")
        
        for i in range(0, len(sentences), max(1, len(sentences) // 10)):
            tile_content = " ".join(sentences[i:i+max(1, len(sentences) // 10)])
            tiles.append({"scene": tile_content})
        
        return tiles[:10]

    def find_inspiration_source(self, story):
        prompt = f"""
        Based on the following comic book story, identify a recent (within the last 10 years) or highly popular movie that it most likely drew inspiration from. The movie should be well-known and widely recognized. Provide the movie title, its release year, and a brief explanation of the similarities.

        Story:
        {story}

        Focus on finding connections to movies that are:
        1. Released within the last 10 years (2013 or later)
        2. Blockbusters or critically acclaimed films
        3. Well-known franchises or from famous directors
        4. Award-winning movies (Oscars, Golden Globes, etc.)

        If no recent movie fits well, you may choose an older classic that is universally recognized.

        Format your response as:
        Movie Title: [Title] ([Release Year])
        Explanation: [Brief explanation of similarities and why this movie is recent/popular]
        """

        response = self.model.generate_content(prompt)
        return response.text

    def generate_story_from_tiles(self, tile_scenes):
        prompt = f"""
        Create a coherent story based on the following comic book tiles. Each tile represents a key scene or moment in the story.

        Tiles:
        {' '.join(tile_scenes)}

        Create a detailed story that incorporates all these scenes in the given order. The story should flow naturally and provide context and connections between the scenes.
        """

        generation_config = GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            top_k=40,
            max_output_tokens=1000
        )

        response = self.model.generate_content(prompt, generation_config=generation_config)
        return response.text