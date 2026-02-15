
# conspiracy-graph
## Repository Contents

- `data/`: Stores all project data. Many directories contain very large files. To keep the repository manageable, the directories are included with a `.gitkeep` file, while the actual data files are listed in `.gitignore`.  
  - `data_models/`: JSON files representing individual lines from the raw compressed `.zst` files and the corresponding Wikidata response format.  
  - `extracted_data/`: Data extracted from the raw files, including creation timestamps, original post links, post content, etc.  
  - `filtered_entities/`: Filtered entities for the knowledge graph.  
  - `knowledge_graph/`: Final data used for visualizing the knowledge graph.  
  - `prepped_data/`: Cleaned and preprocessed data for input into the transformer model (e.g., with AutoModerator comments removed and short posts filtered out).  
  - `raw_data/`: Original compressed files downloaded from [The-Eye: Reddit Archive](https://the-eye.eu/redarcs/).  
  - `raw_entities/`: Outputs from the transformer model containing extracted entities and relationships used to build the knowledge graph.  

- `scripts/`: Python scripts for transforming data and generating the knowledge graph.  
  - `build_knowledge_graph/`: Scripts for building the graph from filtered entities.  
  - `extract_data/`: Scripts for extracting raw Reddit data into readable formats.  
  - `extract_entities/`: Scripts for extracting entities and relationships for the knowledge graph.  
  - `filter_entities/`: Scripts for filtering raw knowledge graph entities and performing entity linking.  
  - `prep_data/`: Scripts for preparing data for entity and relationship extraction.  
  - `utility/`: Helper scripts for utility functions, such as GPU validation and querying Wikidata.  

## Replication: Creating the Knowledge Graphs

The code in this repository can be used to regenerate the knowledge graphs or adapted to build similar graphs for other subreddits. The steps are outlined below:

### Step 1: Python Environment Setup

This project was developed using **Python 3.12.6**. Other versions may cause compatibility issues, particularly with PyTorch and other dependencies. Packages and dependencies are managed with [uv](https://docs.astral.sh/uv/), and this guide assumes `uv` is installed.
1. Initialize uv: ```uv init```
2. Create the python environment: ```uv venv .venv```
3. Activate the environment:
	- Linux/macOS: ```source .venv/bin/activate```
	- Windows: ```.venv\Scripts\activate```
4. Install packages from the lock file: ```uv sync```
5. Deactivate the environment when done: `deactivate`


### (Optional) GPU Setup for PyTorch

If you plan to use a GPU, follow the [PyTorch docs](https://pytorch.org/get-started/locally/) for the appropriate CUDA version. Example steps:

- Uninstall existing PyTorch packages: `pip uninstall torch torchvision torchaudio`
- Install PyTorch with CUDA libraries (example for CUDA 11.8): `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
- Validate PyTorch and GPU setup: `uv run ./scripts/utility/gpu_validation.py`

### Step 2: Sourcing the data
Archived reddit post and comment data was pulled from [The-Eye: Reddit Archive](https://the-eye.eu/redarcs/). The following files were manually downloaded to the `data/raw_data/` directory. As mentioned above, some of the data was not uploaded to Github due to the sheer size of files.

#### r/conspiracy
- Posts: https://the-eye.eu/redarcs/files/conspiracy_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/conspiracy_comments.zst

#### r/conspiracytheories
- Posts: https://the-eye.eu/redarcs/files/conspiracytheories_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/conspiracytheories_comments.zst

#### r/conspiracy_commons
- Posts: https://the-eye.eu/redarcs/files/conspiracy_commons_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/conspiracy_commons_comments.zst

#### r/conspiracyII
- Posts: https://the-eye.eu/redarcs/files/ConspiracyII_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/ConspiracyII_comments.zst

### Step 3: Extracting Relevant Data
**Command:** `uv run ./scripts/extract_data/extract_data.py`

This script processes Reddit data stored in Zstandard-compressed `.zst` files and converts it into structured JSON Lines (`.jsonl`) files that are suitable for building knowledge graphs. It is designed to handle very large files efficiently while maintaining robustness against malformed or partially corrupted data.

The script begins by decompressing the `.zst` files using the `zstandard` library with a stream reader. To handle incomplete UTF-8 sequences that can occur at chunk boundaries, it reads the data in large chunks and applies a recursive decoding function. This ensures that all valid text is captured even when lines span across chunks.

Once decompressed, the script processes the data line by line, parsing each line as a JSON object. Any malformed lines or missing fields are counted for logging purposes but do not interrupt the extraction process. Users can define exactly which fields to extract through the `extract_data_config.json` file. For each field, the script maps the raw key to a new standardized key in the output. Certain fields, like `permalink`, receive special handling. For example, the script constructs full Reddit post URLs automatically.

The extracted data is written to JSONL files under `data/extracted_data/`, preserving the original directory structure while only including the fields specified in the configuration. Each line in these output files represents a single post with a curated set of fields. During processing, the script logs progress every 100,000 lines, providing information on the number of lines processed, malformed lines, and the percentage of the file read. At the end of execution, it reports total lines processed, total errors, and the location of the output files.

Because the fields are configurable via `extract_data_config.json`, the script is highly adaptable. Users can modify the configuration to extract different keys or apply the script to different subreddits and raw datasets. This makes the script the foundational step in transforming raw Reddit data into clean, structured datasets suitable for knowledge graph generation and downstream analyses.

### Step 4: Prepping Model Data
**Command:**  `uv run ./scripts/prepped_data/prep_data.py`

After extracting the raw Reddit data, the dataset still contains information that is not suitable for input into a transformer model. Examples include comments generated by the AutoModerator bot, very short posts that provide little textual content, and removed or deleted comments. This script is responsible for filtering out such data and preparing a clean, high-quality dataset for model training.

The script reads each JSONL file line by line and applies a series of conditional filters. For comment data, lines authored by AutoModerator are automatically discarded, and the textual content is evaluated to ensure it meets minimum length requirements. Similarly, submission data undergoes filtering on both titles and post bodies. The script also integrates a pre-trained spaCy named entity recognition (NER) model to identify whether the text contains any entities. Posts or comments without named entities are excluded, further ensuring that the remaining data is relevant for downstream knowledge extraction tasks.

To maintain performance, the script accumulates valid lines in batches and writes them periodically to new JSONL files in the `data/prepped_data/` directory, preserving a parallel directory structure to the extracted data. Each output file contains only the cleaned and filtered text, with all original metadata removed. The filtering criteria and input file paths are configurable via `prep_data_config.json`, allowing users to adapt the preprocessing logic for different subreddits or data formats.

By removing irrelevant, low-quality, or uninformative content, this preprocessing step ensures that only meaningful, entity-rich text is fed into the transformer model, which improves the quality of subsequent entity extraction and knowledge graph generation.
### Step 5: Extracting the entities
**Command:**  `uv run ./scripts/extract_entities/extract_entities.py`

Once the data has been preprocessed and cleaned, this step uses a transformer model to extract entities and their relationships from the text. The pipeline relies on Babelscape’s REBEL Large model, a sequence-to-sequence model designed specifically for joint entity and relation extraction (the original paper can be found [here](https://github.com/Babelscape/rebel/blob/main/docs/EMNLP_2021_REBEL__Camera_Ready_.pdf)). The script will automatically utilize a GPU if one is available, but can fall back to CPU execution for systems without GPU support.

The script processes JSONL files containing prepped text, reading each line and encoding it as input for the model. The model generates predictions in the form of sequences that encode relational triplets, which are then parsed to extract structured subject-relation-object tuples. To improve efficiency, the script tokenizes and batches text inputs, performs beam search to enhance output quality, and can generate multiple candidate triplets per input line.

Progress is tracked using a JSON-based configuration file, which records the last processed line for each file. This allows users to safely stop and resume processing, which is especially important when working with large datasets on limited hardware. The script also logs progress periodically, including the number of lines processed and the number of triplets extracted, ensuring transparency and traceability of the extraction process.

All extracted triplets are written to output JSONL files in the `data/raw_entities/ directory`, maintaining a parallel directory structure to the prepped data. This ensures that each triplet is associated with the source text while providing a clean, structured representation of entities and their relationships for downstream tasks, such as building knowledge graphs or performing further analyses.

By combining efficient batching, GPU acceleration, and structured progress tracking, this step converts raw textual data into a high-quality, entity-relationship dataset suitable for knowledge graph generation.

### Step 6: Filter the Entities
**Command:**  `uv run ./scripts/filter_entities/filter_entities.py`

After extracting entities from the text, many of them are low-quality or semantically uninformative for constructing knowledge graphs. For example, entities like “bro” linked to a generic type such as “person” do not meaningfully contribute to understanding the structure of topics like conspiracy theories. This step addresses both the quality and the semantic alignment of extracted entities by filtering and linking them to established concepts in Wikidata.

The script reads JSONL files containing raw entity triplets and applies entity linking by querying Wikidata for each head and tail entity. For each term, all candidate labels and aliases returned by Wikidata are compared against the original term using Levenshtein-based similarity scoring. Only the most semantically similar candidate above a defined similarity threshold is retained, ensuring that the resulting knowledge graph contains consistent and meaningful entities. Triplets for which either the head or tail cannot be confidently linked are discarded.

Progress is tracked through a configuration file, allowing the script to be safely stopped and resumed on large datasets or limited hardware. The script also periodically logs progress, including the number of lines processed and the number of entities successfully linked. Filtered and linked triplets are written to JSONL files in the `data/filtered_entities/` directory, maintaining a parallel structure to the raw entity data.

By combining similarity-based filtering and entity linking, this step transforms noisy extracted entities into a refined, semantically coherent dataset. The resulting triplets are suitable for downstream tasks such as knowledge graph construction, analysis, and visualization, ensuring the final graph reflects meaningful relationships between concepts rather than irrelevant or ambiguous data.

### Step 7: Building the Knowledge Graph
**Command:**  `uv run ./scripts/build_knowledge_graph/build_graph.py`

This script takes the filtered and linked entity triplets and constructs knowledge graphs that represent relationships between concepts. The process begins by ingesting all JSONL files from the filtered entity directory, parsing each triplet, and aggregating duplicate edges. Each unique pair of linked entities is counted to produce raw edge weights, which reflect how frequently two entities co-occur in the dataset. Self-loops, edges connecting an entity to itself, are discarded, and undirected edges are used, so that connections are counted symmetrically.

The raw edge counts are then normalized to produce two versions of the knowledge graph. The first, a larger graph, retains more edges for high-resolution visualization, suitable for generating rasterized images of the full network. The second, smaller graph applies a stricter edge threshold, producing a more compact network that is optimized for interactive exploration and analysis in tools such as Gephi. Edge normalization is performed in two stages: initial scaling of raw counts to a 0 - 1 range, followed by removal of edges below a configurable percentile threshold and renormalization of the remaining edges. This ensures that weak or spurious connections are filtered out while preserving meaningful relationships.

Finally, the script exports the smaller graph in Gephi-compatible CSV format, including separate files for nodes and edges. Nodes are labeled by their entity names, and edges include the normalized weight and are marked as undirected. Both graph versions, as well as the raw edge count data, are written to the specified output directory, providing datasets suitable for visual analysis, statistical evaluation, and further downstream applications such as graph-based feature extraction or community detection.
