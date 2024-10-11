from api import ComicStoryGenerator

def pics(prompt):
    generator = ComicStoryGenerator()
    
    story = generator.generate_story(prompt)
    tiles = generator.create_comic_tiles(story)
    inspiration = generator.find_inspiration_source(story)

    output = {
        "story": story,
        "tiles": tiles,
        "inspiration": inspiration
    }

    return output