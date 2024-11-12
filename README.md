# conspiracy-graph
## Repository Contents
- `data/`: Where raw and preprocessed data is written. The files are too large to host in Github so this directory is included in the .gitignore file.
- `data_extraction/`: Where the python files for extracting the raw data live. Inspiration was taken from [PushshiftDumps](https://github.com/Watchful1/PushshiftDumps/tree/master) and modified for this use case.
- `data_models/`: Representations of data inputs/outputs for different scripts.
  
## Data Sources
Archived reddit post and comment data was pulled from [The-Eye](https://the-eye.eu/redarcs/). Files were downloaded to the ```data/``` directory. As mentioned above, the data was not uploaded to Github due to the sheer size of files.

### r/conspiracy
- Posts: https://the-eye.eu/redarcs/files/conspiracy_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/conspiracy_comments.zst

### r/conspiracytheories
- Posts: https://the-eye.eu/redarcs/files/conspiracytheories_submissions.zst
- Comments: https://the-eye.eu/redarcs/files/conspiracytheories_comments.zst

## Python Environment Setup
Some useful commands for setting up the python environment are included below. The requirements.txt file contains the packages used for this project as well. Package versions are locked for stability.

- Create the python environment: ```python3 -m venv .conspiracy_graph_env```
- Activate the environment: ```source .conspiracy_graph_env/bin/activate```
- Update Pip: ```pip3 install --upgrade pip```
- Install packages:  `pip install {PACKAGE}`
- Deactivate it:  `deactivate`
- Save packages:  `pip freeze > requirements.txt`
- Recreate environment:  `pip install -r requirements.txt`
