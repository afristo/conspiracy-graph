
# conspiracy-graph
## Repository Contents
-  `data/`: Where all data is written. For many of the directories, the files are incredibly large. In this case, the directories are uploaded to github but the files are included in the .gitignore file.
	- `data_models/`: Contains basic json files representing individual lines of the raw, compressed .zst files and the wikidata response json format.
	- `extracted_data/` Contains the data extracted from the raw files (e.g. creation timestamp, links to original posts, the body of the posts, etc.).
	- `final_graph/`: Contains the final data for visualizing the knowledge graph.
	- `prepped_data/`: Contains the cleaned up extracted data we will use as inputs for the transformer model (e.g. AutoModerator comments removed, short posts removed, etc.).
	- `raw_data/`: Contains the original, compressed files pulled from [The-Eye: Reddit Archive](https://the-eye.eu/redarcs/).
	- `raw_entities/`: Contains the outputs of the transformer model with the extracted entities and corresponding relationships to build the knowledge graph.
- `scripts/`: Contains the python code used to transform the data into the knowledge graph and visualize it.
	- `extract_data/` Contains the code to extract the raw compressed reddit data into readable data.
	- `extract_entities/`: Contains the code for extracting entities and relationships for the knowledge graph.
	- `prep_data/`: Contains the code responsible for prepping the data for entity and relationship extraction.
	- `utility/`: Contains code for utility functions, such as validating the presence of a GPU.
## Replication, Creating the Knowledge Graphs
The code contained in this repository can be used to regenerate the knowledge graphs, or be slightly modified to build similar knowledge graphs for other subreddits. The steps to do so are outlined below:
### Step 1: Python Environment Setup
This project was developed using Python 3.12.6. Other versions may have compatibility issues, specifically with pytorch and other dependencies.

Some useful commands for setting up the python environment are included below. The requirements.txt file contains the packages used for this project as well. Package versions are locked for stability.
- Create the python environment: ```python3 -m venv .conspiracy_graph_env```
- Activate the environment: ```source .conspiracy_graph_env/bin/activate```
- Update Pip: ```pip3 install --upgrade pip```
- Install packages: `pip install {PACKAGE}`
- Deactivate it: `deactivate`
- Save packages: `pip freeze > requirements.txt`
- Recreate environment: `pip install -r requirements.txt`

If utilizing a GPU, use the [PyTorch docs](https://pytorch.org/get-started/locally/) to install the relevant torch versions and packages.

- Uninstall Torch: `pip uninstall torch torchvision torchaudio`
- Install Torch w/ Cuda Libraries (example): `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
- Validate Torch and GPU Setup: `./scripts/utility/gpu_validation.py`
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
**Command:** `python ./scripts/extract_data/extract_data.py`

The structure of the raw .zst files is contained in the `data/data_models/` directory. If you want to extract the same information used for the knowledge graphs, simply run the command shown above.

If you would like to modify the information extracted, change the values located in `/scripts/extract_data/extract_data_config.json` file. This will allow the python script to extract different keys from the raw files.
### Step 4: Prepping Model Data
**Command:**  `python ./scripts/prepped_data/prep_data.py`

After extracting the data we are left information we don't want to feed into the model. Some examples include posts by the reddit AutoModerator bot, extremely short posts that don't contain much text and removed comments. This script is responsible for removing this data before feeding it into the transformer model.
### Step 5: Extracting the entities
**Command:**  `python ./scripts/extract_entities/extract_entities.py`

Now that we have data prepped for the model, we can use the transformer model to extract entities and their relationships. We use Bablescape's Rebel Large model (the original paper can be found [here](https://github.com/Babelscape/rebel/blob/main/docs/EMNLP_2021_REBEL__Camera_Ready_.pdf)) to extract entities and their relationships. The script will attempt to utilize a GPU if it is present, and will fallback to the CPU if a GPU is not available for running the model.

The python script relies on two configuration files:
- `extract_entities_config.json`: Identifies the correct files and directories to use as inputs for the model.
- `extract_entities_progress.json`: Tracks progress for entity extraction, allowing the user to stop and start the script if they are using less-powerful compute hardware.

Note: Due to time and compute limits, only entities and relationships from r/conspiracytheories were extracted.
### Step 6: Building the Knowledge Graph
**Command:**  `python ./scripts/build_knowledge_graph.py`

The extracted entities are often useless. For example, the entity "bro" linked to "person" is not really useful in understanding conspiracy theory structure. Furthermore, we need to conduct entity linking. This is done by:
1. Sending our raw entities to Wikidata to find established concepts.
2. Removing concepts that do not pass a similarity (levenstein distance) filter (e.g. if I query "Household", we would drop the result "Tractor" since it is not similar, but we would keep "House").
3. Take the most similar concept of the remaining options (e.g. if we queried "Household" and we still have the results "Home", "Housing Crisis" and "Homestead", we take "House").

The above process for entity linking also filters out concepts that are not easily mapped to the Wikidata knowledge base. We then "collapse" and normalize graph nodes/edges for the final knowledge graph. This is done by assigning higher "strength" to node pairs that are mentioned more often (e.g. if the pair "Elon" and "Twitter" is mentioned 5 times, it gets a strength of 5, which is then normalized relative to all raw strength scores).
