import os
import json
import pandas as pd
from typing import List, Tuple, Dict


def split_documents(
    document_csv: str,
    in_dir: str,
    csv_chunksize: int = 500,
    chunk_size: int = 2000,
    batch_size: int = 10,
) -> List[str]:
    """
    Reads a CSV in streaming chunks, cleans and splits text, batches records,
    writes each batch to JSON in in_dir, and returns the list of filenames.
    """
    # Inner helper: clean text
    def clean_text(text: str) -> str:
        """UTF-8 sanitize & collapse whitespace."""
        if not isinstance(text, str):
            text = str(text or "")
        cleaned = text.encode("utf-8", "ignore").decode("utf-8")
        return " ".join(cleaned.split())

    # Inner helper: split into fixed-size pieces
    def split_into_chunks(text: str) -> List[str]:
        """Break text into ≤size-char pieces."""
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    os.makedirs(in_dir, exist_ok=True)
    filenames: List[str] = []
    buffer: List[Dict[str, str]] = []
    batch_id = 0

    # Stream CSV
    reader = pd.read_csv(
        document_csv,
        dtype={"uuid": str, "body_en": str},
        chunksize=csv_chunksize,
    )

    for df in reader:
        # Ensure required columns
        if not {"uuid", "body_en"}.issubset(df.columns):
            raise KeyError(f"{document_csv} missing uuid/body_en columns")

        # Clean and drop empty bodies (with no string content)
        df["body_en"] = df["body_en"].apply(clean_text)
        df = df[df["body_en"].astype(bool)]

        # Chunk and buffer
        for row in df.itertuples(index=False):
            for idx, chunk in enumerate(split_into_chunks(row.body_en)):
                buffer.append({
                    "uuid": row.uuid,
                    "chunk_id": f"{row.uuid}_{idx}",
                    "body_en": chunk,
                })
                if len(buffer) >= batch_size:
                    fname = f"batch_{batch_id}.json"
                    path = os.path.join(in_dir, fname)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(buffer, f, ensure_ascii=False)
                    filenames.append(fname)
                    batch_id += 1
                    buffer = []

    # Write any remaining buffer
    if buffer:
        fname = f"batch_{batch_id}.json"
        path = os.path.join(in_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(buffer, f, ensure_ascii=False)
        filenames.append(fname)

    return filenames
