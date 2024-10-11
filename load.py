import csv
import json
import os
from typing import List, Dict

def load_plot_summaries(file_path: str) -> Dict[str, str]:
    summaries = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                wikipedia_id, summary = parts
                summaries[wikipedia_id] = summary
    return summaries

def load_movie_metadata(file_path: str) -> Dict[str, Dict]:
    metadata = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) >= 9:
                metadata[row[0]] = {
                    'wikipedia_id': row[0],
                    'freebase_id': row[1],
                    'name': row[2],
                    'release_date': row[3],
                    'revenue': row[4],
                    'runtime': row[5],
                    'languages': row[6].split(','),
                    'countries': row[7].split(','),
                    'genres': row[8].split(',')
                }
    return metadata

def merge_data(summaries: Dict[str, str], metadata: Dict[str, Dict]) -> List[Dict]:
    merged_data = []
    for wikipedia_id, summary in summaries.items():
        if wikipedia_id in metadata:
            merged_item = {**metadata[wikipedia_id], 'summary': summary}
            merged_data.append(merged_item)
    return merged_data

def format_for_fine_tuning(merged_data: List[Dict]) -> List[Dict]:
    fine_tuning_data = []
    for movie in merged_data:
        input_text = f"Movie Title: {movie['name']}\nGenres: {', '.join(movie['genres'])}\nSummary: {movie['summary']}\n\nCreate a comic book premise based on this movie plot. Include a catchy comic book title, main characters and their roles, the central conflict or challenge, and a twist that makes it different from the original movie."
        output_text = "Comic Book Premise: [Your model will learn to generate this]"
        fine_tuning_data.append({
            "text_input": input_text,
            "output": output_text
        })
    return fine_tuning_data

def save_processed_data(data: List[Dict], output_file: str):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    # Construct paths based on the project structure
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, 'data')
    
    summaries_path = os.path.join(data_dir, 'plot_summaries.txt')
    metadata_path = os.path.join(data_dir, 'movie.metadata.tsv')
    output_path = os.path.join(current_dir, 'gemini_fine_tuning_data.json')

    print(f"Loading plot summaries from: {summaries_path}")
    summaries = load_plot_summaries(summaries_path)
    
    print(f"Loading movie metadata from: {metadata_path}")
    metadata = load_movie_metadata(metadata_path)
    
    merged_data = merge_data(summaries, metadata)
    fine_tuning_data = format_for_fine_tuning(merged_data)
    
    save_processed_data(fine_tuning_data, output_path)
    print(f"Processed {len(fine_tuning_data)} movies for fine-tuning.")
    print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    main()