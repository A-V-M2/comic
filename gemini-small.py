import os
import json
import time
from typing import Dict, List
import pandas as pd
from dotenv import load_dotenv
from google.cloud import aiplatform
from vertexai.preview.language_models import TextGenerationModel
from vertexai.generative_models import GenerationConfig, GenerativeModel
from vertexai.preview.tuning import sft
from rouge_score import rouge_scorer
from tqdm import tqdm

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv('PROJECT_ID')
LOCATION = os.getenv('LOCATION')
BUCKET_NAME = os.getenv('BUCKET_NAME')
BUCKET_URI = f"gs://{BUCKET_NAME}"

def load_movie_data(metadata_file: str, summaries_file: str, sample_size: int = 1000) -> pd.DataFrame:
    """Load and merge movie metadata and summaries, with sampling."""
    print(f"Loading metadata from {metadata_file}")
    metadata = pd.read_csv(metadata_file, sep='\t', header=None, 
                           names=['wikipedia_id', 'freebase_id', 'name', 'release_date', 'revenue', 'runtime', 'languages', 'countries', 'genres'])
    
    print(f"Loading summaries from {summaries_file}")
    summaries = pd.read_csv(summaries_file, sep='\t', header=None, names=['wikipedia_id', 'summary'])
    
    print("Merging metadata and summaries")
    merged_data = pd.merge(metadata, summaries, on='wikipedia_id')
    
    # Sample the data
    sampled_data = merged_data.sample(n=min(sample_size, len(merged_data)))
    print(f"Sampled {len(sampled_data)} entries for fine-tuning")
    
    return sampled_data

def prepare_data_for_fine_tuning(input_data: pd.DataFrame, output_file: str):
    """Prepare data for fine-tuning."""
    fine_tuning_data = []
    for _, row in tqdm(input_data.iterrows(), total=len(input_data), desc="Preparing data"):
        input_text = f"Movie Title: {row['name']}\nGenres: {row['genres']}\nSummary: {row['summary']}\n\nCreate a comic book premise based on this movie plot. Include a catchy comic book title, main characters and their roles, the central conflict or challenge, and a twist that makes it different from the original movie."
        output_text = "Comic Book Premise: [Your model will learn to generate this]"
        
        fine_tuning_data.append({
            "messages": [
                {"role": "user", "content": input_text},
                {"role": "model", "content": output_text}
            ]
        })
    
    print(f"Saving fine-tuning data to {output_file}")
    with open(output_file, 'w') as f:
        for item in fine_tuning_data:
            f.write(json.dumps(item) + '\n')

def fine_tune_model():
    """Fine-tune the Gemini model."""
    print("Initiating fine-tuning process")
    tuning_job = sft.train(
        source_model="gemini-1.0-pro-002",
        train_dataset=f"{BUCKET_URI}/fine_tuning_data.jsonl",
        epochs=1,  # Reduced to 1 epoch
        learning_rate_multiplier=1,
    )

    start_time = time.time()
    with tqdm(total=100, desc="Fine-tuning progress") as pbar:
        while not tuning_job.refresh().has_ended:
            time.sleep(30)  # Check every 30 seconds
            elapsed_time = time.time() - start_time
            if elapsed_time > 900:  # 15 minutes = 900 seconds
                print("15 minutes elapsed. Stopping fine-tuning.")
                tuning_job.cancel()
                break
            pbar.update(5)  # Assuming each update is roughly 5% progress

    print("Tuning completed or stopped!")
    return tuning_job

def evaluate_model(model: GenerativeModel, test_data: pd.DataFrame):
    """Evaluate the fine-tuned model."""
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = []
    
    for _, row in tqdm(test_data.iterrows(), total=len(test_data), desc="Evaluating model"):
        prompt = f"Movie Title: {row['name']}\nGenres: {row['genres']}\nSummary: {row['summary']}\n\nCreate a comic book premise based on this movie plot."
        response = model.generate_content(prompt)
        generated_premise = response.text
        reference_premise = "Comic Book Premise: [Reference premise not available]"
        
        score = scorer.score(reference_premise, generated_premise)
        scores.append(score)
    
    return pd.DataFrame(scores)

def main():
    try:
        # Initialize Vertex AI
        print(f"Initializing Vertex AI with project {PROJECT_ID} in {LOCATION}")
        aiplatform.init(project=PROJECT_ID, location=LOCATION)

        # Load and prepare data
        print("Loading and preparing data...")
        movie_data = load_movie_data('data/movie.metadata.tsv', 'data/plot_summaries.txt', sample_size=1000)
        prepare_data_for_fine_tuning(movie_data, 'fine_tuning_data.jsonl')
        
        # Upload data to Cloud Storage
        print(f"Uploading data to Cloud Storage bucket: {BUCKET_URI}")
        os.system(f"gsutil cp fine_tuning_data.jsonl {BUCKET_URI}/")

        # Fine-tune the model
        print("Starting fine-tuning process...")
        tuning_job = fine_tune_model()

        # Load the fine-tuned model
        print("Loading fine-tuned model...")
        tuned_model = GenerativeModel(tuning_job.tuned_model_endpoint_name)

        # Evaluate the fine-tuned model
        print("Evaluating fine-tuned model...")
        evaluation_results = evaluate_model(tuned_model, movie_data.sample(100))  # Evaluate on a sample of 100 movies

        print("Evaluation Results:")
        print(evaluation_results.mean())

        # Save results
        print("Saving evaluation results...")
        evaluation_results.to_csv('evaluation_results.csv', index=False)
        print("Evaluation results saved to 'evaluation_results.csv'")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please check the error message and make sure all prerequisites are met.")

if __name__ == "__main__":
    main()