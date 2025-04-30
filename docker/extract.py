import os
import json
import logging
import shutil
from gliner import GLiNER

# Configuration via environment variables
INPUT_PATH = os.getenv("INPUT_PATH", "/data/in/batch.json")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/data/out/entities.json")
PROCESSED_DIR = os.getenv("PROCESSED_DIR", "/data/in/processed")
LABELS = ["Person", "Company", "Location"]
THRESHOLD = float(os.getenv("THRESHOLD", 0.5))


def load_batch(path: str):
    """
    Load a batch of documents from a JSON file.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results, path: str):
    """
    Save the extracted entities results back to a JSON file.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)


def move_to_processed(input_path: str, processed_dir: str):
    """
    Move the processed input file into a processed directory.
    """
    try:
        os.makedirs(processed_dir, exist_ok=True)
        dest = os.path.join(processed_dir, os.path.basename(input_path))
        shutil.move(input_path, dest)
        logging.info(f"Moved processed file to {dest}")
    except Exception as e:
        logging.error(f"Failed to move processed file: {e}")


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting entity extraction...")

    # Load input batch
    try:
        batch = load_batch(INPUT_PATH)
    except Exception as e:
        logging.error(f"Failed to load batch from {INPUT_PATH}: {e}")
        raise

    # Load or instantiate the GLiNER model
    logging.info("Loading GLiNER model...")
    model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")

    # Process each record
    for record in batch:
        text = record.get("body_en", "")
        if not text or not isinstance(text, str):
            record["entities_raw"] = []
            continue

        # Extract entities
        ents = model.predict_entities(text, LABELS, threshold=THRESHOLD)
        record["entities_raw"] = ents

    # Write output
    try:
        save_results(batch, OUTPUT_PATH)
    except Exception as e:
        logging.error(f"Failed to write results to {OUTPUT_PATH}: {e}")
        raise

    logging.info(f"Extraction complete: wrote {len(batch)} records to {OUTPUT_PATH}")

    # Move input to processed folder
    move_to_processed(INPUT_PATH, PROCESSED_DIR)

if __name__ == "__main__":
    main()
