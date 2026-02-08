# Import native libraries
import logging
import json
import sys
import os

# Import third-party libraries
from fuzzywuzzy import fuzz
import requests


# Set constant values for the script, enforcing them with a class
class Constants:
    """
    A class specifically for enforcing constant values in the script.
    """

    CONFIG = "./scripts/filter_entities/filter_entities_config.json"
    SIMILARITY_THRESHOLD = 70


def setup_logging():
    """
    Sets up the logging configuration for the script.
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

    # Load the JSON progress file
    with open(file=Constants.CONFIG, mode="r+", encoding="utf-8") as progress_file:

        progress_config = json.load(progress_file)

        # Navigate to the nested dictionary
        current_level = progress_config

        # Traverse all but the last key
        for key in key_path[:-1]:

            if key in current_level:

                current_level = current_level[key]

            else:

                logging.info("Key path \"%s\" not found in the JSON file.", " -> ".join(key_path))

                # Exit if any key in the path doesn"t exist
                return

        # Update the value of the last key
        last_key = key_path[-1]

        if last_key in current_level:

            current_level[last_key] = value

        else:

            logging.info("Key \"%s\" not found in the JSON file.", last_key)

            return

        # Output the new config
        progress_file.seek(0)
        json.dump(progress_config, progress_file, indent=4)

        # Truncate the rest of the file if the new content is shorter
        progress_file.truncate()

        logging.info("Updated key path \"%s\" with value \"%s\".", " -> ".join(key_path), value,)


def best_single_record_similarity(original_term, record):
    """
    Each Wikidata result contains a label and 0 or more aliases. This function gets the best
    similarity from all of these. For example, if we search "CIA" we may get a result labeled
    "Central Intelligence Agency" that has an alias "CIA". In this case, we want to take the
    similarity for the alias "CIA", not the label "Central Intelligence Agency.

    :param original_term: The original search term to get results from Wikidata.
    :param record: A single record from Wikidata with a label and potential aliases.
    :return: The best similarity across the label and all aliases.
    """

    # Extract the label and aliases
    aliases = record.get("aliases", [])

    # Combine the label and aliases into a single list
    candidates = [record["label"]] + aliases

    # Calculate the similarity for each candidate and track the highest
    best_similarity = max(fuzz.ratio(candidate, original_term) for candidate in candidates)

    return best_similarity


def search_wikidata(term):
    """
    This function queries Wikidata with a value.

    :param term: The term to search for.
    :return: A list of dictionaries, containing the results of the search from Wikidata.
    """

    # Set the wikidata URL
    url = "https://www.wikidata.org/w/api.php"

    # Set parameters for the call
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "search": term,
    }

    # Set headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0"
    }

    # Send the request
    response = requests.get(
        url=url,
        params=params,
        headers=headers,
        timeout=15
        )

    # If we get a successful response, return the response
    if response.status_code == 200:

        return response.json().get("search", [])

    # If we get an unauthorized error, stop the script immediately to avoid more
    elif response.status_code == 403:

        logging.error("403 forbidden error querying Wikidata, exiting.")

        sys.exit(1)

    logging.error("Error querying Wikidata for '%s': %s", term, response.status_code)

    return []


def filter_wikidata_results(original_term, wikidata_results, threshold):
    """
    Filter Wikidata search results based on Levenshtein similarity, retaining only results that
    meet the threshold and selecting the top match.

    :param original_name: The original name of the entity from the input data.
    :param wikidata_results: A list of Wikidata search results for the entity.
    :param threshold: The minimum similarity score to accept a match (0-100).
    :return: The label of the best matching Wikidata entity if it meets the threshold; otherwise,
    return None.
    """

    # Initialize variables to track the best match
    best_match = None
    highest_similarity = 0

    # Iterate through results to calculate similarity
    for result in wikidata_results:

        # For all labels and aliases for a single wikidata result, find the best similarity
        similarity = best_single_record_similarity(original_term, result)

        # If a record has a perfect similarity, return it immediately
        if similarity == 100:

            return result["label"]

        # Only consider matches that meet the threshold and are better than the current best match
        if similarity > highest_similarity and similarity >= threshold:

            # Store the best match and similarity if the threshold is passed
            best_match = result["label"]
            highest_similarity = similarity

    # Return the best match, or None if no results passed the threshold
    return best_match


def process_and_link_entities(data_source_name, input_file_path, output_file_path, current_line):
    """
    Process a knowledge graph by reading input data, linking entities to Wikidata,
    collapsing duplicate edges, and normalizing edge strengths.

    :param file: Name of the file being processed (used for logging and progress tracking).
    :param input_file: Path to the input .jsonl file containing raw knowledge graph entities.
    :param output_file: Path to the output .jsonl file to save filtered knowledge graph entities.
    :param threshold: The minimum similarity score for entity linking (0-100).
    :param current_line: Line number from which to resume processing.
    """

    logging.info("Starting entity filtering. Reading input from %s", input_file_path)

    # Open input and output files
    with open(file=input_file_path, mode="r", encoding="utf-8") as in_file, \
        open(file=output_file_path, mode="a", encoding="utf-8") as out_file:

        # Set default starting line number
        line_number = 1

        # List to accumulate the triplets
        triplets = []

        for line_number, input_file_line in enumerate(iterable=in_file, start=line_number):

            # If a line has already been processed, skip it
            if line_number < current_line:

                # Skip already processed lines
                continue

            # Load the entities
            record = json.loads(input_file_line)
            head = record["head"]
            tail = record["tail"]

            # Entity linking for head and tail
            head_results = search_wikidata(head)
            linked_head = filter_wikidata_results(
                head,
                head_results,
                Constants.SIMILARITY_THRESHOLD
                )

            tail_results = search_wikidata(tail)
            linked_tail = filter_wikidata_results(
                tail,
                tail_results,
                Constants.SIMILARITY_THRESHOLD
                )

            # If both the head and tail of the triplet were linked, add it to the list
            if linked_head and linked_tail:

                # Create the triplet and write it directly to the file
                triplet = {
                    "linked_head": linked_head,
                    "original_head": head,
                    "type": record["type"],
                    "linked_tail": linked_tail,
                    "original_tail": tail
                }

                triplets.append(triplet)

            else:

                logging.warning(
                    "Failed to link entities: head=%s, tail=%s. Skipping line %s.",
                    head,
                    tail,
                    line_number
                )

            # Log progress every 100 lines
            if line_number % 100 == 0:

                logging.info("Processed %s lines...", line_number)

                # Write the accumulated triplets to the output file
                if triplets:

                    for triplet in triplets:

                        json.dump(triplet, out_file)
                        out_file.write("\n")

                    # Clear the list after writing
                    triplets.clear()

                # Update progress in the config
                update_progress_config(
                    key_path=[data_source_name, "line"],
                    value=line_number
                )

        # Final write if there are remaining triplets
        if triplets:

            for triplet in triplets:

                json.dump(triplet, out_file)
                out_file.write("\n")

            # Clear the list after writing
            triplets.clear()

        # Final progress update
        update_progress_config(
            key_path=[data_source_name, "line"],
            value=line_number
        )

    logging.info("Entity filtering completed. Output written to %s.", output_file_path)


if __name__ == "__main__":

    # Setup logging functionality
    setup_logging()

    # Load the JSON config file
    with open(file=Constants.CONFIG, mode="r", encoding="utf-8") as config_file:

        config = json.load(config_file)

    # Enumerate over the individual files we're going to process
    for data_source in config:

        logging.info("Filtering %s...", data_source)

        # Do not process the file if we've already processed it (e.g. "True")
        if config[data_source]["status"] is True:

            continue

        # Extract the filepath and current line we are on
        input_file = config[data_source]["path"]
        line = config[data_source]["line"]

        # Split the path into components
        directory, filename = os.path.split(input_file)

        # Replace the directory and filename
        new_directory = directory.replace("raw_entities", "filtered_entities")
        new_filename = filename.replace("_raw_entities", "_filtered_entities")

        # Construct the output file path
        output_file = os.path.join(new_directory, new_filename)

        # Filter entities
        process_and_link_entities(data_source, input_file, output_file, line)

        # Update the config with our progress
        update_progress_config(
            key_path=[data_source, "status"],
            value=True
            )

    logging.info("All entities filtered.")
