
# conspiracy-graph
## Repository Contents
-  `data/`: Where all data is written. For many of the directories, the files are incredibly large. In this case, the directories are uploaded to github but the files are included in the .gitignore file.
	- `data_models/`: Contains basic json files representing individual lines of the raw, compressed .zst files.
	- `extracted_data/` Contains the data extracted from the raw files (e.g. creation timestamp, links to original posts, the body of the posts, etc.).
	- `knowledge_graph_entities/`: Contains the outputs of the transformer model with the extracted entities and corresponding relationships to build the knowledge graph.
	- `prepped_data/`: Contains the cleaned up extracted data we will use as inputs for the transformer model (e.g. AutoModerator comments removed, short posts removed, etc.).
	- `raw_data/`: Contains the original, compressed files pulled from [The-Eye: Reddit Archive](https://the-eye.eu/redarcs/).
- `scripts/`: Contains the python code used to extract the raw data, prep the extracted data, and use the transformer models to identify the entities and relationships for the knowledge graph.
## Replication, Creating the Knowledge Graphs
The code contained in this repository can be used to regenerate the knowledge graphs, or slightly modified to build similar knowledge graphs for other subreddits. The steps to do so are outlined below:
### Step 1: Sourcing the data
Archived reddit post and comment data was pulled from [The-Eye: Reddit Archive](https://the-eye.eu/redarcs/). The following files were manually downloaded to the `data/raw_data/` directory. As mentioned above, some of the data was not uploaded to Github due to the sheer size of files.
#### r/conspiracy
- Posts: https://the-eye.eu/redarcs/files/conspiracy_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/conspiracy_comments.zst
#### r/conspiracytheories
- Posts: https://the-eye.eu/redarcs/files/conspiracytheories_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/conspiracytheories_comments.zst
### Step 2: Extracting Relevant Data
**Command:** `python ./scripts/extract_data.py`

The structure of the raw .zst files is contained in the `data/data_models/` directory. If you want to extract the same information used for the knowledge graphs, simply run the command shown above.

If you would like to modify the information extracted, change the values located in `/scripts/extract_data_config.json` file. This will allow the python script to extract different keys from the raw files.
## Python Environment Setup
Some useful commands for setting up the python environment are included below. The requirements.txt file contains the packages used for this project as well. Package versions are locked for stability.
- Create the python environment: ```python3 -m venv .conspiracy_graph_env```
- Activate the environment: ```source .conspiracy_graph_env/bin/activate```
- Update Pip: ```pip3 install --upgrade pip```
- Install packages: `pip install {PACKAGE}`
- Deactivate it: `deactivate`
- Save packages: `pip freeze > requirements.txt`
- Recreate environment: `pip install -r requirements.txt`
