# Bilby Entity Extraction Pipeline

This repository implements a proof-of-concept entity extraction and matching pipeline using Apache Airflow, Docker, and a pre-trained GLiNER model. It reads raw documents, splits them into manageable chunks, extracts entities in parallel via a Docker container, matches them against a Source-of-Truth aliases table, and assembles the final nested output.
![image](https://github.com/user-attachments/assets/aa98cd4d-6567-40ed-b78f-d3d1508cfd5d)



## Project Structure
```
.
├── dags/
│   └── entity_pipeline.py
├── pipelines/
│   ├── split_docs.py
│   ├── match_entities.py
│   └── assemble.py
├── logs/
├── docker/
│   ├── Dockerfile
│   └── extract.py
├── data/
│   ├── documents.csv
│   ├── entity_aliases.csv
│   ├── in/
│   ├── out/
│   ├── matched/
│   └── output/
├── logs/
├── .env.example
├── start.sh
├── pyproject.toml
└── README.md
```

## Pipeline Design
This pipeline consists of four core stages, each implemented as a separate Airflow task or operator:
1. Batch Ingestion (`split_documents`)
   - Reads the master `documents.csv` in 500-row chunks
   - Cleans texts, splits into 2,000-character segments, and groups into batches of 10
   - Writes out JSON batch files to `data/in`
2. Entity Extraction (`DockerOperator`)
   - Launches a Docker container (`extractor:latest`) for each batch
   - Runs GLiNER inside the container to extract `Person`, `Company`, and `Location` entities
   - Caches the model at build time and isolates memory usage
   - Writes raw extraction results (`entities_raw`) to `data/out` in `<batch>_entities.json`
   - Move all proceed json into `data/in/processed`
3. Entity Matching (`match_entities`)
   - Loads the hard-coded SoT aliases CSV into memory
   - Iterates each extracted entity, performing exact, case-sensitive alias matching
   - Annotates each record with `is_matched` and matched_entity_name
   - Writes matched outputs to `data/matched` in `<batch>_matched.json`
4. Assembly (`assemble_entities`)
   - Reads all matched JSON files from `data/matched`
   - Aggregates them by document UUID into a nested JSON structure
   - Outputs the final consolidated file at `data/output/final_entities.json`

Each stage uses dynamic task mapping (.map + .expand/.expand_kwargs) to parallelize work across batches without manual iteration.


## Setup Guide
### Prerequisites
- **Python 3.12+** with `pip` and `uv` installed  
- **Docker Desktop** (ensure the Docker daemon is running and socket available at `~/.docker/run/docker.sock`)  
- **Git** for cloning the repository  

### Setup & Quick Start
#### 1.	Clone the repo
```console
git clone git@github.com:<YOUR_USER>/bilby-entity-pipeline.git
cd bilby-entity-pipeline
```
#### 2.	Configure environment
```console
cp .env.example .env
```
Edit .env if you need to adjust `AIRFLOW_HOME` or other settings

#### 3. Build the Docker image for extraction use
```console
cd docker
docker build -t extractor:latest extractor/
```

#### 4. Start Airflow
```console
uv run --env-file .env airflow standalone
# or
sh start.sh
```
#### 5.	Activate the DAG

•	Open `http://localhost:8080` in your browser

•	Log in (see `standalone_admin_password.txt`)

•	Find and Unpause the entity_pipeline DAG

#### 6.	Trigger & Monitor

•	In the UI, click Trigger DAG

•	Watch the Graph or Tree view to follow each step

•	Once complete, view the final output in data/output/final_entities.json

### Output Schema

The final output is a JSON file (final_entities.json) containing a list of documents with their extracted and matched entities:
```json
[
  {
    "uuid": "<document-uuid>",
    "entities": [
      {
        "entity_type": "Person",
        "entity_text": "Xi Jinping",
        "start_pos": 42,
        "end_pos": 52,
        "is_matched": true,
        "matched_entity_name": "Xi Jinping"
      },
      {
        "entity_type": "Location",
        "entity_text": "Shenzhen",
        "start_pos": 5,
        "end_pos": 13,
        "is_matched": false,
        "matched_entity_name": null
      }
      // ...
    ]
  }
  // ...
]
```
### Database Schema Design
We store the data in a nested‐JSON format, but if broken out into relational tables, the schema would look like:
1. documents table
    -	uuid (PK, string)
    -	(additional columns from documents.csv as needed)
2. entities table
    -	id (PK, auto‐increment)
    -	document_uuid (FK → documents.uuid)
    -	entity_type (string)
    -	start_pos (integer)
    -	end_pos (integer)
    -	is_matched (boolean)
    -	matched_entity_name (string, nullable)


In our JSON output, each document object carries its uuid and an array of entity records matching the above fields.

### Assumptions & Notes
•	Airflow logs are stored under logs/ and pipeline data under data/ subfolders.

•	Uses a local Docker socket; adjust docker_url in the DAG if needed.

•	For a fresh run, clear data/in, data/out, data/matched, and data/output folders.
```bash
rm -rf data/in/* data/out/* data/matched/* data/output/*
```

•	Designed to scale via batch streaming and dynamic task mapping.

## TODO
- Add a simple pytest suite and a GitHub Actions workflow to run tests on every push.
- Include flake8 or black code style checks in the CI pipeline.
