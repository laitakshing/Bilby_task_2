import os
import json
import logging
import ast
import pandas as pd
from typing import List, Dict, Any


def match_entities(
    input_path: str,
    output_path: str,
    aliases_csv: str,
) -> str:
    """
    Load extracted records from input_path, match each entity against the SoT aliases,
    write matched records to output_path, and return output_path.
    """
    # Inner helper: load aliases into a mapping
    def load_aliases(path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load the SoT aliases CSV into a mapping:
        { entity_type: [ {name: ..., aliases: [...]}, ... ], ... }
        Expects columns: entity_type, name, aliases (as a Python list or semicolon-separated).
        """
        df = pd.read_csv(path, dtype={"entity_type": str, "name": str, "aliases": str})
        alias_map: Dict[str, List[Dict[str, Any]]] = {}
        for _, row in df.iterrows():
            etype = row["entity_type"]
            name = row["name"]
            raw = row["aliases"]
            try:
                aliases = ast.literal_eval(raw)
            except Exception:
                aliases = [a.strip() for a in raw.split(";") if a.strip()]
            alias_map.setdefault(etype, []).append({"name": name, "aliases": aliases})
        return alias_map

    # Inner helper: apply matching to a single record
    def match_record(record: Dict[str, Any], alias_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        For each record and each entity in record['entities_raw'],
        add match info:
        - is_matched: bool
        - matched_entity_name: the SoT 'name' or None
        """
        matched_list: List[Dict[str, Any]] = []
        for ent in record.get("entities_raw", []):
            etype = ent.get("label")
            text = ent.get("text")
            is_matched = False
            matched_name: Any = None
            for sot in alias_map.get(etype, []):
                if text == sot["name"] or text in sot["aliases"]:
                    is_matched = True
                    matched_name = sot["name"]
                    break
            matched_list.append({
                **ent,
                "is_matched": is_matched,
                "matched_entity_name": matched_name,
            })
        record["entities_matched"] = matched_list
        return record

    # Ensure directories
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Load records
    logging.info(f"Loading extracted records from {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Load alias map
    logging.info(f"Loading aliases from {aliases_csv}")
    alias_map = load_aliases(aliases_csv)

    # Match all records
    logging.info("Performing entity matching...")
    matched = [match_record(rec, alias_map) for rec in records]

    # Write output
    logging.info(f"Writing matched results to {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(matched, f, ensure_ascii=False, indent=2)

    logging.info(f"Entity matching complete: wrote {len(matched)} records.")
    return output_path
