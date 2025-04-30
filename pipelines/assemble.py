import os, json, glob
from typing import List, Dict

def assemble_entities(
    matched_dir: str,
    output_path: str
) -> None:
    entities_by_doc: Dict[str, List[dict]] = {}
    pattern = os.path.join(matched_dir, "*_matched.json")
    for path in glob.glob(pattern):
        with open(path, "r", encoding="utf-8") as f:
            batch = json.load(f)
        for rec in batch:
            for ent in rec.get("entities_matched", []):
                row = {
                    "entity_type":         ent["label"],
                    "entity_text":         ent["text"],
                    "start_pos":           ent["start"],
                    "end_pos":             ent["end"],
                    "is_matched":          ent["is_matched"],
                    "matched_entity_name": ent["matched_entity_name"],
                }
                entities_by_doc.setdefault(rec["uuid"], []).append(row)

    final_output = [{"uuid": u, "entities": ents} for u, ents in entities_by_doc.items()]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
