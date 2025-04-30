import os
from datetime import datetime

from airflow.decorators import dag, task
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

from pipelines.split_docs     import split_documents
from pipelines.match_entities import match_entities
from pipelines.assemble       import assemble_entities

# Wrap plain functions as tasks
split_documents_task   = task(split_documents)
match_entities_task    = task(match_entities)
assemble_entities_task = task(assemble_entities)

# Paths
AIRFLOW_HOME    = os.environ.get("AIRFLOW_HOME", "/opt/airflow")
DATA_PATH       = os.path.join(AIRFLOW_HOME, "data")
DOCUMENT_CSV    = os.path.join(DATA_PATH, "documents.csv")
IN_DIR          = os.path.join(DATA_PATH, "in")
OUT_DIR         = os.path.join(DATA_PATH, "out")
MATCHED_DIR     = os.path.join(DATA_PATH, "matched")
OUTPUT_DIR      = os.path.join(DATA_PATH, "output")
OUTPUT_PATH     = os.path.join(OUTPUT_DIR, "final_entities.json")
ALIASES_CSV     = os.path.join(DATA_PATH, "entity_aliases.csv")

EXTRACTOR_IMAGE = "extractor:latest"
DOCKER_URL       = os.environ.get("DOCKER_URL", "unix:///var/run/docker.sock")

@dag(
    dag_id="entity_pipeline",
    start_date=datetime(2025, 4, 28),
    schedule_interval=None,
    catchup=False,
    tags=["entity_pipeline"],
)
def entity_pipeline():

    # 1) split into batches
    split_task = split_documents_task(
        DOCUMENT_CSV, IN_DIR, csv_chunksize=500, chunk_size=2000, batch_size=10
    )

    # 2) extract via DockerOperator
    # build a list of env‐dicts per batch via XComArg.map
    extract_env = split_task.map(lambda fname: {
        "INPUT_PATH":    f"/data/in/{fname}",
        "OUTPUT_PATH":   f"/data/out/{fname.replace('.json','_entities.json')}",
        "PROCESSED_DIR": "/data/in/processed",
    })

    extract = DockerOperator.partial(
        task_id="extract_entities",
        image=EXTRACTOR_IMAGE,
        api_version="auto",
        docker_url=DOCKER_URL,  
        auto_remove="force",
        mounts=[
            Mount(source=IN_DIR,  target="/data/in",  type="bind"),
            Mount(source=OUT_DIR, target="/data/out", type="bind"),
        ],
    ).expand(environment=extract_env)

    # 3) match entities in parallel
    match_kwargs = split_task.map(lambda fname: {
        "input_path":  os.path.join(
            OUT_DIR, fname.replace(".json", "_entities.json")
        ),
        "output_path": os.path.join(
            MATCHED_DIR, fname.replace(".json", "_matched.json")
        ),
        "aliases_csv": ALIASES_CSV,
    })

    matched = match_entities_task.partial().expand_kwargs(match_kwargs)

    # 4) assemble final JSON
    assemble = assemble_entities_task(MATCHED_DIR, OUTPUT_PATH)

    # dependencies
    split_task >> extract >> matched >> assemble

dag = entity_pipeline()
