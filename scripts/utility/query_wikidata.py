# Import third-party libraries
from fuzzywuzzy import fuzz
import requests

# Import native libraries
import logging
import json
import time
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

        # Specify the output file path
        output_file = './scripts/utility/wikidata_query_results.json'

        # Open the file in write mode
        #with open(output_file, 'w') as file:

            # Serialize the dictionary to JSON with indentation for readability
            #json.dump(results, file, indent=4)

        return results
    
    else:

        logging.error(f"Error querying Wikidata for '{entity_name}': {response.status_code}")

        return []


def best_single_record_similarity(original_term, record):

    logging.info(f"Calculating similarities for one Wikidata record...")

    # Extract the label and aliases
    label = record.get("label", "")
    aliases = record.get("aliases", [])

    # Combine the label and aliases into a single list
    candidates = [label] + aliases

    # Compute similarity for each candidate
    similarities = {candidate: fuzz.ratio(candidate, original_term) for candidate in candidates}

    logging.info(f"Here are all the similarities: {similarities}")

    time.sleep(2)

    # Initialize variables to track the best match and similarity
    best_match = None
    best_similarity = 0

    # Iterate over the dictionary to find the candidate with the highest similarity
    for candidate, similarity in similarities.items():

        logging.info(f"Checking {candidate} with similarity {similarity} against {original_term}...")

        time.sleep(2)

        if similarity == 100:

            return label, best_similarity

        if similarity > best_similarity:

            best_match = candidate
            best_similarity = similarity

    logging.info(f"For this record, we are using {best_match} with a similarity of {best_similarity}")

    time.sleep(2)

    return best_similarity


def filter_wikidata_results(original_term, wikidata_results, threshold):
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

    # Iterate through results to calculate similarity
    for result in wikidata_results:

        logging.info(f"Original Term: {original_term}")
        logging.info("Wikidata Response: %s", result["label"])

        time.sleep(2)

        # For all labels and aliases for a single wikidata result, find the best similarity
        similarity = best_single_record_similarity(original_term, result)

        logging.info(f"Similarity: {str(similarity)}")

        time.sleep(2)

        # If a record has a perfect similarity, there is no reason to use any other values
        if similarity == 100:

            return result["label"]

        # Only consider matches that meet the threshold
        if similarity >= threshold and similarity > highest_similarity:

            logging.info(f"Threshold passed, replacing {best_match} with " + result["label"])

            time.sleep(2)

            # Store the best match and similarity if the threshold is passed
            best_match = result["label"]
            highest_similarity = similarity

    logging.info(f"BEST MATCH: {best_match}")

    # Return the best match, or None if no results passed the threshold
    return best_match

if __name__ == "__main__":
    """
    Main function to process JSONL files for entity linking.
    """

    # Set manually for testing
    head = "CIA"
    threshold = 70

    # Setup logging functionality
    setup_logging()

    # Entity linking for head and tail
    head_results = search_wikidata(head)
    linked_head = filter_wikidata_results(head, head_results, threshold)
