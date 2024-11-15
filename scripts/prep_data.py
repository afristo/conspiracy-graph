# Import native libraries
import logging.handlers
import json
import os

# Set up logging configuration
log = logging.getLogger("logger")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


def clean_comments(extracted_data_filepath):
    """
    Reads a JSONL file line by line, applies conditional logic, and writes matching lines to a new file.
    Optimized version to minimize file I/O and improve efficiency.

    :param extracted_data_filepath: Path to the input JSONL file.
    """

    # Split the path into components
    directory, filename = os.path.split(extracted_data_filepath)

    # Replace the directory from 'raw_data' to 'prepped_data'
    new_directory = directory.replace("extracted_data", "prepped_data")

    # Rename the new file by appending "_prepped.jsonl" to the end
    new_filename = os.path.splitext(filename)[0] + "_prepped.jsonl"

    # Construct the new file path
    jsonl_output_file = os.path.join(new_directory, new_filename)

    # Open the input and output files
    with open(extracted_data_filepath, 'r') as infile, open(jsonl_output_file, 'w') as outfile:

        # Use a list to accumulate valid lines for batch writing
        valid_lines = []

        # Enumerate through each line in the input file
        for line in infile:

            try:

                # Parse the line as JSON
                obj = json.loads(line.strip())

                # Remove lines where the AutoModerator is commenting
                if obj["author"] == "AutoModerator":

                    log.debug(f"Skipping line due to AutoModerator comment: {obj}")

                    continue

                # Remove lines where the comment has been removed or deleted
                if obj["body"] == "[deleted]" or obj["body"] == "[removed]":

                    log.debug(f"Skipping line due to comment being deleted: {obj}")

                    continue

                # Remove lines where the comment is incredibly short
                if len(obj["body"].split()) < 3:

                    log.debug(f"Skipping line due to length: {obj}")

                    continue

                # If no errors, accumulate the valid line
                valid_lines.append(json.dumps(obj))

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
    Optimized version to minimize file I/O and improve efficiency.

    :param extracted_data_filepath: Path to the input JSONL file.
    """

    # Split the path into components
    directory, filename = os.path.split(extracted_data_filepath)

    # Replace the directory from 'raw_data' to 'prepped_data'
    new_directory = directory.replace("extracted_data", "prepped_data")

    # Rename the new file by appending "_prepped.jsonl" to the end
    new_filename = os.path.splitext(filename)[0] + "_prepped.jsonl"

    # Construct the new file path
    jsonl_output_file = os.path.join(new_directory, new_filename)

    # Open the input and output files
    with open(extracted_data_filepath, 'r') as infile, open(jsonl_output_file, 'w') as outfile:

        # Use a list to accumulate valid lines for batch writing
        valid_lines = []

        # Use strings to identify deleted or removed post components
        deleted_or_removed = [
            "[deleted]",
            "deleted",
            "[deleted",
            "deleted]",
            "[removed]",
            "removed",
            "[removed",
            "removed]"
            ]

        # Enumerate through each line in the input file
        for line in infile:

            try:

                # Parse the line as JSON
                obj = json.loads(line.strip())

                # Remove lines where the title and body are both incredibly short
                if len(obj["title"].split()) < 3 and len(obj["body"].split()) < 3:

                    log.debug(f"Skipping line due to length: {obj}")

                    continue

                # If the body was deleted or removed, set it None
                if obj["body"] in deleted_or_removed:

                    log.debug(f"Skipping line due to length: {obj}")

                    obj["body"] = None

                # If no errors, accumulate the valid line
                valid_lines.append(json.dumps(obj))

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

    # Open the config JSON file
    with open("./scripts/prep_data_config.json", 'r') as file:

        # Read the data into a dictionary
        config = json.load(file)

    # Enumerate over the top-level keys and values in the config file
    for key, value in config.items():

        log.info(f"Processing {key} data...")

        # Extract the filepath and the values we want to extract from the raw files
        extracted_data_filepath = value["path"]

        # If we have submissions data, call the function specific for cleaning up the submissions data
        if key in ("Conspiracy Theories Submissions", "Conspiracy Submissions"):

            clean_submissions(extracted_data_filepath)

        # If we have comment data, call the function specific for cleaning up the comment data
        elif key in ("Conspiracy Theories Comments", "Conspiracy Comments"):

            clean_comments(extracted_data_filepath)

        else:

            log.info(f"The {key} data did not fit predetermined logic, check your config file...")

    log.info("All files have been processed.")
