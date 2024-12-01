# Import third party libraries
import spacy

# Import native libraries
import logging.handlers
import json
import os

# Set up logging configuration
log = logging.getLogger("logger")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())

# Load spaCy"s pre-trained NER model
nlp = spacy.load("en_core_web_sm")


def filter_entries(text):
    """
    Takes a string of text and determines if it is worth feeding into the model. If so, it is returned.

    :param text: The text that is being evaluated.
    """

    # If the text has less than 10 words, drop the text
    if len(text.split()) < 10:

        return None
    
    # Apply named entity recognition to the text
    doc = nlp(text)

    # If there are no entities, drop the text
    if len(doc.ents) == 0:

        return None
    
    # If the tests are passed, return the original text
    return text


def clean_comments(extracted_data_filepath):
    """
    Reads a JSONL file line by line, applies conditional logic, and writes matching lines to a new file.

    :param extracted_data_filepath: Path to the input JSONL file.
    """

    # Split the path into components
    directory, filename = os.path.split(extracted_data_filepath)

    # Replace the directory from "raw_data" to "prepped_data"
    new_directory = directory.replace("extracted_data", "prepped_data")

    # Rename the new file by appending "_prepped.jsonl" to the end
    new_filename = os.path.splitext(filename)[0] + "_prepped.jsonl"

    # Construct the new file path
    jsonl_output_file = os.path.join(new_directory, new_filename)

    # Open the input and output files
    with open(extracted_data_filepath, "r") as infile, open(jsonl_output_file, "w") as outfile:

        # Use a list to accumulate valid lines for batch writing
        valid_lines = []

        # Enumerate through each line in the input file
        for line in infile:

            try:

                # Parse the line as JSON
                obj = json.loads(line.strip())

                # Try to extract title and body
                author = obj.get("author")
                body = obj.get("body")

                # Remove lines where the AutoModerator is commenting
                if author == "AutoModerator":

                    log.debug(f"Skipping line due to AutoModerator comment: {obj}")

                    continue

                # Pass the body through the filter
                body = filter_entries(body)

                # If body passed the filter, add it
                if body is not None:

                    valid_lines.append(json.dumps({"text": body}))

            except json.JSONDecodeError:
                log.info(f"Skipping invalid JSON line: {line.strip()}")

            # Batch write to the output file after every 100 lines for efficiency
            if len(valid_lines) >= 100:

                # Write the lines to the output file
                outfile.write("\n".join(valid_lines) + "\n")

                # Reset the batch list
                valid_lines.clear()

        # After finishing the loop, write any remaining valid lines
        if valid_lines:

            # Write the lines to the output file
            outfile.write("\n".join(valid_lines) + "\n")


def clean_submissions(extracted_data_filepath):
    """
    Reads a JSONL file line by line, applies conditional logic, and writes matching lines to a new file.

    :param extracted_data_filepath: Path to the input JSONL file.
    """

    # Split the path into components
    directory, filename = os.path.split(extracted_data_filepath)

    # Replace the directory from "raw_data" to "prepped_data"
    new_directory = directory.replace("extracted_data", "prepped_data")

    # Rename the new file by appending "_prepped.jsonl" to the end
    new_filename = os.path.splitext(filename)[0] + "_prepped.jsonl"

    # Construct the new file path
    jsonl_output_file = os.path.join(new_directory, new_filename)

    # Open the input and output files
    with open(extracted_data_filepath, "r") as infile, open(jsonl_output_file, "w") as outfile:

        # Use a list to accumulate valid lines for batch writing
        valid_lines = []

        # Enumerate through each line in the input file
        for line in infile:

            try:

                # Parse the line as JSON
                obj = json.loads(line.strip())

                # Try to extract title and body
                title = obj.get("title")
                body = obj.get("body")

                # Pass the title and body through the filter
                title = filter_entries(title)
                body = filter_entries(body)

                # If title passed the filter, add it
                if title is not None:

                    valid_lines.append(json.dumps({"text": title}))

                # If body passed the filter, add it
                if body is not None:

                    valid_lines.append(json.dumps({"text": body}))

            except json.JSONDecodeError:
                log.info(f"Skipping invalid JSON line: {line.strip()}")

            # Batch write to the output file after every 100 lines for efficiency
            if len(valid_lines) >= 100:

                # Write the lines to the output file
                outfile.write("\n".join(valid_lines) + "\n")

                # Reset the batch list
                valid_lines.clear()

        # After finishing the loop, write any remaining valid lines
        if valid_lines:

            # Write the lines to the output file
            outfile.write("\n".join(valid_lines) + "\n")


if __name__ == "__main__":
    """
    Main function for the program. Uses a basic JSON config file to enumerate
    over the four files that contain the extracted text we want to prep for
    the transformer model.
    """

    # Load spaCy"s pre-trained named entity recognition model
    nlp = spacy.load("en_core_web_sm")

    # Open the config JSON file
    with open("./scripts/prep_data_config.json", "r") as file:

        # Read the data into a dictionary
        config = json.load(file)

    # Enumerate over the top-level keys and values in the config file
    for key, value in config.items():

        log.info(f"Processing {key} data...")

        # Extract the filepath and the values we want to extract from the raw files
        extracted_data_filepath = value.get("path")
        type = value.get("type")

        # If we have submissions data, call the function specific for cleaning up the submissions data
        if type == "submissions":

            clean_submissions(extracted_data_filepath)

        # If we have comment data, call the function specific for cleaning up the comment data
        elif type == "comments":

            clean_comments(extracted_data_filepath)

        else:

            log.info(f"The {key} data did not fit predetermined logic, check your config file...")

    log.info("All files have been processed.")
