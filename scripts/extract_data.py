# Import third-party libraries
import zstandard

# Import native libraries
from datetime import datetime, timezone
import logging.handlers
import json
import time
import sys
import os

# Set up logging configuration
log = logging.getLogger("logger")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


def read_and_decode(reader, chunk_size, max_window_size, previous_chunk=None, bytes_read=0):
    """
    Reads a chunk of data from a reader, attempts to decode it to a string, and recursively tries 
    to read more data if a Unicode decoding error occurs. This handles files that may have incomplete 
    UTF-8 sequences at chunk boundaries.
    
    :param reader: The reader object from which data is read.
    :param chunk_size: Number of bytes to read per chunk.
    :param max_window_size: Maximum number of bytes to attempt reading in case of decoding error.
    :param previous_chunk: The previous chunk of data to append in case of error (for recursive reads).
    :param bytes_read: Counter for the total number of bytes read.
    :return: The decoded chunk of data as a string.
    """
    
    # Read a chunk of the file
    chunk = reader.read(chunk_size)

    # Increment the total bytes read
    bytes_read += chunk_size

    # Append the previous chunk to next chunk
    if previous_chunk is not None:

        chunk = previous_chunk + chunk

    try:

        # Attempt to decode the chunk to a UTF-8 string
        return chunk.decode()
    
    except UnicodeDecodeError:

        # If decoding fails and max window size exceeded, raise an error
        if bytes_read > max_window_size:

            raise UnicodeError(f"Unable to decode frame after reading {bytes_read:,} bytes")

        # Log the decoding error and continue reading
        log.info(f"Decoding error with {bytes_read:,} bytes, reading another chunk")
        
        # Recursively attempt to decode with additional data
        return read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)


def read_lines_zst(file_name):
    """
    Reads lines from a Zstandard-compressed file, yielding each line individually.
    
    :param file_name: Path to the Zstandard-compressed file.
    :yield: Each line from the decompressed file along with the current byte offset.
    """
    
    # Open the compressed file in binary mode
    with open(file_name, 'rb') as file_handle:
        
        # Initialize a buffer to store partial lines between reads
        buffer = ''
        
        # Set up a Zstandard decompression reader with max window size
        reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(file_handle)

        while True:

            # Read and decode a large chunk from the compressed file
            chunk = read_and_decode(reader, 2**27, (2**29) * 2)

            # Exit the loop if no more data is returned
            if not chunk:

                break

            # Combine buffer and chunk, then split on newline to separate lines
            lines = (buffer + chunk).split("\n")

            # Yield each line except the last incomplete line
            for line in lines[:-1]:

                # Yield line and current byte offset in file
                yield line, file_handle.tell()
            
            # Save the last partial line for the next iteration
            buffer = lines[-1]

        # Close the decompression reader
        reader.close()


def process_file(raw_data_filepath, extraction_keys):
    """
    Carries out the decoding, reading and extraction of data from one compressed zst file.
    
    :param file_name: Path to the Zstandard-compressed file.
    :yield: Each line from the decompressed file along with the current byte offset.
    """

    # Get the size of the file in bytes
    file_size = os.stat(raw_data_filepath).st_size

    # Initialize counters and placeholders
    file_lines = 0                # Total lines processed
    file_bytes_processed = 0      # Bytes processed so far
    created = None                # Timestamp for progress tracking
    bad_lines = 0                 # Count of malformed or missing JSON lines

    # Split the path into components
    directory, filename = os.path.split(raw_data_filepath)

    # Replace the directory from 'raw_data' to 'extracted_data'
    new_directory = directory.replace("raw_data", "extracted_data")

    # Set the file extension to '.jsonl'
    new_filename = os.path.splitext(filename)[0] + ".jsonl"

    # Construct the new file path
    jsonl_output_file = os.path.join(new_directory, new_filename)

    # Open output file in write mode
    with open(jsonl_output_file, 'w', encoding='utf-8') as output_file:
        
        # Read lines from the Zstandard-compressed file
        for line, file_bytes_processed in read_lines_zst(raw_data_filepath):

            try:

                # Attempt to parse each line as JSON
                obj = json.loads(line)

                # Create an empty dictionary to store the information we need
                record = {}

                # Enumerate through the list of dictionaries in the config file
                for mapping in extraction_keys:

                    # Extract the original key and new key from each dictionary
                    original_key, new_key = next(iter(mapping.items()))

                    # Extract the value using the key name in the raw data file
                    value = obj.get(original_key, None)  # The .get function will handle empty and null strings

                    # Handle special case for the 'permalink' key
                    if original_key == "permalink" and value:

                        # Build the full post URL
                        value = "https://www.reddit.com/" + str(value)
                    
                    # Add the key to the dictionary with the new names (e.g. instead of "ups" we want "upvotes")
                    record[new_key] = value
                
                # Write the dictionary to the JSONL file as a JSON string
                output_file.write(json.dumps(record) + '\n')
                
                # Convert 'created_utc' to a UTC-aware datetime object for progress tracking
                created = datetime.fromtimestamp(int(obj['created_utc']), tz=timezone.utc)
            
            except (KeyError, json.JSONDecodeError):

                # Increment count of malformed lines
                bad_lines += 1

            # Increment the line counter
            file_lines += 1

            # Log progress every 100,000 lines processed
            if file_lines % 100000 == 0:
                log.info(f"{created.strftime('%Y-%m-%d %H:%M:%S')} : {file_lines:,} : {bad_lines:,} : {file_bytes_processed:,}:{(file_bytes_processed / file_size) * 100:.0f}%")

    # Log final completion statistics
    log.info(f"Complete : {file_lines:,} : {bad_lines:,}")
    log.info(f"Data has been written to {jsonl_output_file}")


if __name__ == "__main__":
    """
    Main function for the program. Uses a basic JSON config file to enumerate
    over the four files that contain the text we want for our analysis.
    """

    # Open the config JSON file
    with open("./scripts/extract_data_config.json", 'r') as file:

        # Read the data into a dictionary
        config = json.load(file)

    # Enumerate over the top-level keys and values in the config file
    for key, value in config.items():

        log.info(f"Processing {key} data...")

        # Extract the filepath and the values we want to extract from the raw files
        raw_data_filepath = value["path"]
        extraction_keys = value["values"]

        process_file(raw_data_filepath, extraction_keys)

    log.info("All files have been processed.")
