# Import third-party libraries
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

# Import native libraries
import logging
import json
import os

# Set up logging configuration for concise console output
log = logging.getLogger("logger")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())

# Enable tokenizer parallelism to improve performance
os.environ["TOKENIZERS_PARALLELISM"] = "true"

def update_progress_config(key_path, value):
    """
    Updates a nested key in the progress JSON file with a given value if the key path exists.

    :param key_path: List of keys representing the path to the nested key.
    :param value: The new value to assign to the key.
    """

    # Set the path for the config file
    json_file_path = "./scripts/extract_entities/extract_entities_progress.json"

    try:

        # Load the JSON progress file
        with open(json_file_path, "r") as progress_file:

            progress_config = json.load(progress_file)

        # Navigate to the nested dictionary
        current_level = progress_config

        # Traverse all but the last key
        for key in key_path[:-1]:

            if key in current_level:

                current_level = current_level[key]

            else:

                print(f"Key path \"{" -> ".join(key_path)}\" not found in the JSON file.")

                # Exit if any key in the path doesn"t exist
                return

        # Update the value of the last key
        last_key = key_path[-1]

        if last_key in current_level:

            current_level[last_key] = value

        else:

            print(f"Key \"{last_key}\" not found in the JSON file.")

            return

        # Write the updated dictionary back to the file
        with open(json_file_path, "w") as progress_file:

            # Output the new config
            json.dump(
                progress_config,
                progress_file,
                indent=4 # Save with indentation for readability
                )

        print(f"Updated key path \"{' -> '.join(key_path)}\" with value \"{value}\" in {json_file_path}.")

    except FileNotFoundError:

        print(f"File {json_file_path} not found.")

    except json.JSONDecodeError:

        print(f"Error decoding JSON from file {json_file_path}.")

    except Exception as e:

        print(f"An error occurred: {e}")


def extract_triplets(text):
    """
    Extracts triplets (subject, relation, object) from a given text.
    Triplets are identified by markers: <triplet>, <subj>, and <obj>.

    :param text: Input text containing triplet markers.
    :return: A list of dictionaries representing extracted triplets.
    """

    # Define a list to hold triplets
    triplets = []

    # Initialize components for each triplet
    relation, subject, object_ = "", "", ""

    # Keeps track of the part of the triplet currently being processed
    current = "x"

    # Process tokens, removing extra markers
    for token in text.replace("<s>", "").replace("<pad>", "").replace("</s>", "").split():

        if token == "<triplet>":

            # Start of a new triplet; save previous triplet if it exists
            current = "t"

            if relation:

                triplets.append({"head": subject.strip(), "type": relation.strip(), "tail": object_.strip()})

                relation, subject, object_ = "", "", ""  # Reset for the next triplet

        elif token == "<subj>":

            # Start of a subject
            current = "s"

            if relation:

                triplets.append({"head": subject.strip(), "type": relation.strip(), "tail": object_.strip()})

                subject, object_ = "", ""  # Reset object

        elif token == "<obj>":

            # Start of an object
            current = "o"

            relation = ""  # Reset relation

        else:

            # Accumulate tokens into the appropriate triplet component
            if current == "t":

                subject += " " + token

            elif current == "s":

                object_ += " " + token

            elif current == "o":

                relation += " " + token

    # Append the last triplet if valid
    if subject and relation and object_:

        triplets.append({"head": subject.strip(), "type": relation.strip(), "tail": object_.strip()})
    
    return triplets


def prep_model_inputs(tokenizer, model, gen_kwargs, text):
    """
    Prepares batched inputs for the model and generates predictions for each text.

    :param tokenizer: The tokenizer to encode input texts.
    :param model: The pre-trained model to generate predictions.
    :param gen_kwargs: Generation arguments for the model.
    :param text: The input texts to process.
    :return: List of decoded predictions for each text.
    """

    # Tokenize the batch of texts for model input
    model_inputs = tokenizer(
        text,
        max_length=256,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )
    
    # Generate output predictions from the model in batch
    generated_tokens = model.generate(
        model_inputs["input_ids"].to(model.device),
        attention_mask=model_inputs["attention_mask"].to(model.device),
        **gen_kwargs
    )
    
    # Decode predictions to readable text format
    return tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)


def process_file(file_name, input_file_path, tokenizer, model):
    """
    Processes a JSONL file, extracts triplets, and writes them in batches to an output file.
    
    :param file_name: The name of the type of data to process.
    :param input_file_path: Path to the input JSONL file.
    :param tokenizer: The tokenizer to encode text.
    :param model: The model for generating predictions.
    """

    # Set a list to hold the triplets extracted from the text
    triplet_batches = []

    # Configuration for model generation parameters:
    gen_kwargs = {
        "max_length": 256,            # Limits the maximum length of generated sequences to 256 tokens.
        "length_penalty": 0,          # Controls length preference; 0 means no preference for longer or shorter sequences.
        "num_beams": 3,               # Uses beam search with 3 beams to enhance the quality of generated sequences.
        "num_return_sequences": 3,    # Generates 3 distinct sequences for each input, providing multiple outputs.
    }

    # Load the JSON progress file
    with open("./scripts/extract_entities/extract_entities_progress.json", "r") as progress_file:

        # Load the file as JSON
        progress_config = json.load(progress_file)

        # Determine what line we were last on
        start_line_num = int(progress_config[file_name]["line"])

    # Split the path into components
    directory, filename = os.path.split(input_file_path)

    # Replace the directory from "raw_data" to "prepped_data"
    new_directory = directory.replace("prepped_data", "raw_entities")

    new_filename = filename.replace("_prepped", "_raw_entities")

    # Construct the new file path
    output_file_path = os.path.join(new_directory, new_filename)

    # Open and read the JSONL file
    with open(input_file_path, "r") as input_file, open(output_file_path, "w") as output_file:

        # Set the line number for logging
        line_num = 0

        # Enumerate over lines in the JSON file
        for line in input_file:

            # Increment line counter for logging
            line_num += 1

            # Skip the line if we've already processed it
            if line_num < start_line_num:

                continue

            # Parse the line as JSON
            data = json.loads(line.strip())

            # Set an empty list to store the extracted text
            text_to_extract = []

            # Check if the "text" key in the dictionary exists and is populated with an useful value
            if data.get("text"):

                text_to_extract.append(data["text"])

            # If there is text to extract, run the model
            if len(text_to_extract) > 0:

                # Enumerate over each piece of text to extract
                for text in text_to_extract:

                    # Generate predictions for each piece of text
                    decoded_preds = prep_model_inputs(tokenizer, model, gen_kwargs, text)
                    
                    # Extract triplets from each prediction
                    for sentence in decoded_preds:
                        
                        # Extract triplets
                        extracted_triplets = extract_triplets(sentence)

                        # Add extracted triplets to the running batch
                        triplet_batches.extend(extracted_triplets)

                # Clear text for the next round
                text_to_extract = []

            # Process the text batch if it reaches the specified size
            if line_num % 25 == 0:

                # Log progress and write batch to output
                log.info(f"Processed {line_num} lines.")

                # Enumerate through each tiplet in the batch
                for triplet in triplet_batches:

                    # Write the triplet to the output file
                    output_file.write(json.dumps(triplet) + "\n")

                # Update the config with our progress
                update_progress_config(
                    key_path=[file_name, "line"],
                    value=line_num
                    )

                # Clear the batches for the next round
                triplet_batches = []

        # If there are remaining triplets but no more text output the final triplet values
        if triplet_batches:

            # Log progress and write batch to output
            log.info(f"Processed {line_num} lines.")

            # Enumerate through each tiplet in the batch
            for triplet in triplet_batches:

                # Write the triplet to the output file
                output_file.write(json.dumps(triplet) + "\n")

            # Update the config with our progress
            update_progress_config(
                key_path=[file_name, "line"],
                value=line_num
                )

            # Clear the triplet batches for the next round
            triplet_batches = []


if __name__ == "__main__":
    """
    Main function to load the model, process JSONL files, and extract triplets.
    """

    log.info("Loading model and tokenizer...")

    # Load the tokenizer
    tokenizer = AutoTokenizer.from_pretrained("Babelscape/rebel-large")

    # Load the model
    model = AutoModelForSeq2SeqLM.from_pretrained("Babelscape/rebel-large")

    log.info("Model and tokenizer loaded successfully.")

    # Check if GPU is available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    log.info(f"Using device: {device}")

    # Move the model to the GPU if it is available
    model = model.to(device)

    # Open the config JSON file
    with open("./scripts/extract_entities/extract_entities_config.json", "r") as config_file:

        # Read the data into a dictionary
        config = json.load(config_file)

    # Open the config JSON file
    with open("./scripts/extract_entities/extract_entities_progress.json", "r") as progress_file:

        # Read the data into a dictionary
        progress_config = json.load(progress_file)

    # Enumerate over the top-level keys and values in the config file
    for key, value in config.items():

        log.info(f"Processing {key} data...")

        # Use the current file we are processing to check if it has already been processed
        if progress_config[key]["status"] == True:

            # If it has, skip to the next file
            continue

        # Extract the filepath and the values we want to extract from the raw files
        prepped_data_filepath = value["path"]

        # Process the file
        process_file(key, prepped_data_filepath, tokenizer, model)

        # Update the config with our progress
        update_progress_config(
            key_path=[key, "status"],
            value=True
            )

    log.info("All files processed.")
