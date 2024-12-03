# Import third-party libraries
from fuzzywuzzy import fuzz
import requests

# Import native libraries
from collections import defaultdict
import logging
import json
import os


def setup_logging():
    """
    Sets up logging configuration.
    """

    # Set the logging config
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def update_progress_config(key_path, value):
    """
    Updates a nested key in the progress JSON file with a given value if the key path exists.

    :param key_path: List of keys representing the path to the nested key.
    :param value: The new value to assign to the key.
    """

    # Set the path for the config file
    json_file_path = "./scripts/filter_entities/filter_entities.json"

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


def search_wikidata(entity_name):
    """
    Query Wikidata for a given entity name.

    :param entity_name: The name of the entity to search for.
    :return: A list of potential matches from Wikidata, each as a dictionary containing 'id', 'label', and other metadata.
    """

    # Set eh wikidata URL
    url = "https://www.wikidata.org/w/api.php"
    
    # Set parameters for the call
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "search": entity_name,
    }

    # Send the request
    response = requests.get(url, params=params)

    # If we get a successful response, return the response
    if response.status_code == 200:

        results = response.json().get("search", [])

        return results
    
    else:

        logging.error(f"Error querying Wikidata for '{entity_name}': {response.status_code}")

        return []


def filter_wikidata_results(original_name, wikidata_results, threshold):
    """
    Filter Wikidata search results based on Levenshtein similarity, 
    retaining only results that meet the threshold and selecting the top match.

    :param original_name: The original name of the entity from the input data.
    :param wikidata_results: A list of Wikidata search results for the entity.
    :param threshold: The minimum similarity score to accept a match (0-100).
    :return: The label of the best matching Wikidata entity if it meets the threshold; otherwise, None.
    """
    # Initialize variables to track the best match
    best_match = None
    highest_similarity = 0

    print("We got a total of " + str(len(wikidata_results)) + " results from wikidata")

    # Iterate through results to calculate similarity
    for result in wikidata_results:

        # Use levenstein similarity
        similarity = fuzz.ratio(original_name, result["label"])

        # Only consider matches that meet the threshold
        if similarity >= threshold and similarity > highest_similarity:

            # Store the best match and similarity if the threshold is passed
            best_match = result["label"]
            highest_similarity = similarity

    # Return the best match, or None if no results passed the threshold
    return best_match


def filter_entities(file, input_file, output_file, threshold, current_line):
    """
    Process a knowledge graph by reading input data, linking entities to Wikidata,
    collapsing duplicate edges, and normalizing edge strengths.

    :param input_file: Path to the input .jsonl file containing knowledge graph data.
    :param output_file: Path to the output .jsonl file to save processed graph data.
    :param threshold: The minimum similarity score for entity linking (0-100).
    """

    # Store the list of triples
    triplets = []

    logging.info(f"Starting entity filtering. Reading input from {input_file}")

    # Open the file
    with open(input_file, "r") as infile, open(output_file, "w") as out_file:

        line_number = 0

        # Enumerate the lines in the file
        for line_number, line in enumerate(infile, start=line_number):

            # Increment line counter for logging
            line_number += 1

            # Skip the line if we've already processed it
            if line_number < current_line:

                continue

            # Read in the record
            record = json.loads(line)
            head = record["head"]
            tail = record["tail"]

            # Log progress every 100 lines
            if line_number % 100 == 0:

                logging.info(f"Processed {line_number} lines...")

                for triplet in triplets:

                    json.dump(triplet, out_file)

                    out_file.write("\n")

                # Update the config with our progress
                update_progress_config(
                    key_path=[file, "line"],
                    value=line_number
                    )

                # Clear the batches for the next round
                triplets = []

            # Entity linking for the head entity
            head_results = search_wikidata(head)
            linked_head = filter_wikidata_results(head, head_results, threshold)

            # Entity linking for the tail entity
            tail_results = search_wikidata(tail)
            linked_tail = filter_wikidata_results(tail, tail_results, threshold)

            # Add to triples if both entities were successfully linked
            if linked_head and linked_tail:

                triplets.append(
                    {
                        "linked_head": linked_head,
                        "original_head": head,
                        "type": record["type"],
                        "linked_tail": linked_tail,
                        "original_tail": tail
                    }
                )

            else:

                logging.warning(
                    f"Failed to link entities: head='{head}', tail='{tail}'. Skipping line {line_number}."
                )

        # If any triplets are left still, write them to the output file
        if triplets:

            for triplet in triplets:

                json.dump(triplet, out_file)

                out_file.write("\n")

            # Update the config with our progress
            update_progress_config(
                key_path=[file, "line"],
                value=line_number
                )

            # Clear the batches for the next round
            triplets = []


if __name__ == "__main__":
    """
    Main function to process JSONL files for entity linking.
    """

    # Setup logging functionality
    setup_logging()

    # Load the JSON config file
    with open("./scripts/filter_entities/filter_entities_config.json", "r") as config_file:

        config = json.load(config_file)

    # Enumerate over the individual files we're going to process
    for file in config:

        logging.info(f"Filtering {file}")

        # Do not process the file if we've already processed it
        if config[file]["status"] == True:

            continue

        # Extract the filepath and current line we are on
        input_file = config[file]["path"]
        current_line = config[file]["line"]

        # Split the path into components
        directory, filename = os.path.split(input_file)

        # Replace the directory and filename
        new_directory = directory.replace("raw_entities", "filtered_entities")
        new_filename = filename.replace("_raw_entities", "_filtered_entities")

        # Construct the output file path
        output_file = os.path.join(new_directory, new_filename)

        # Set the similarity threshold for Wikidata results
        similarity_threshold = 80

        # Filter entities
        filter_entities(file, input_file, output_file, similarity_threshold, current_line)

    logging.info("All entities filtered.")
