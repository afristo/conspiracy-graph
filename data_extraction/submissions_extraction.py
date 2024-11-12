# Import third-party packages
import zstandard

# Import native packages
from datetime import datetime, timezone
import logging.handlers
import json
import sys
import os

# Set up logging configuration
log = logging.getLogger("bot")
log.setLevel(logging.DEBUG)
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
    # Read a chunk of dead
    chunk = reader.read(chunk_size)

    # Increment a read counter
    bytes_read += chunk_size 

    # Append chunk to next chunk
    if previous_chunk is not None:
        chunk = previous_chunk + chunk

    try:

        # Attempt to decode the chunk to a UTF-8 string
        return chunk.decode()

    except UnicodeDecodeError:

        # If decoding fails and max window size exceeded, raise an error
        if bytes_read > max_window_size:

            raise UnicodeError(f"Unable to decode frame after reading {bytes_read:,} bytes")

        log.info(f"Decoding error with {bytes_read:,} bytes, reading another chunk")

        # Recursive call to continue reading if there was a decoding issue
        return read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)


def read_lines_zst(file_name):
    """
    Reads lines from a Zstandard-compressed file, yielding each line individually.
    
    :param file_name: Path to the Zstandard-compressed file.
    :yield: Each line from the decompressed file along with the current byte offset.
    """

    # Open the file
    with open(file_name, 'rb') as file_handle:

        # Create a temporary buffer for storing partial lines between reads
        buffer = ''

        # Initialize a Zstandard decompression reader with a specified max window size
        reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(file_handle)

        while True:

            # Read and decode a large chunk from the compressed file
            chunk = read_and_decode(reader, 2**27, (2**29) * 2)

            # Exit the loop if no more data is returned
            if not chunk:
                break

            # Split the buffer + chunk on newline to separate lines
            lines = (buffer + chunk).split("\n")

            # Yield each line except the last incomplete line
            for line in lines[:-1]:

                # Yield line and current byte offset in file
                yield line, file_handle.tell()  

            # Save the last partial line for the next iteration
            buffer = lines[-1]

        # Close the decompression reader
        reader.close()


if __name__ == "__main__":

      # Get the file path from command line arguments
    file_path = sys.argv[1]

    # Get the size of the file in bytes
    file_size = os.stat(file_path).st_size

    # Initialize counter for total lines processed
    file_lines = 0

    # Initialize counter for bytes processed
    file_bytes_processed = 0

    # Initialize variable to store the timestamp of each line
    created = None

    # Make an empty list to hold the extracted data
    data = []

    # Counter for lines that could not be parsed
    bad_lines = 0

    for line, file_bytes_processed in read_lines_zst(file_path):

        try:

            # Attempt to parse each line as JSON
            obj = json.loads(line)

            # Extract the fields from the parsed JSON as a dictionary
            record = {
                "title": obj.get("title", None),
                "body": obj.get("selftext", None),
                "number_of_comments": obj.get("num_comments", None),
                "upvotes": obj.get("ups", None),
                "downvotes": obj.get("downs", None),
                "score": obj.get("score", None),
                "created": obj.get("created_utc", None),
                "reddit_url": "https://www.reddit.com/" + str(obj.get("permalink", ""))
            }

            # Add the dictionary to a list
            data.append(record)

            # Get 'created_utc' timestamp and convert to a UTC-aware datetime object
            created = datetime.fromtimestamp(int(obj['created_utc']), tz=timezone.utc)

        except (KeyError, json.JSONDecodeError) as err:

            # Increment count of malformed or missing JSON lines
            bad_lines += 1

        # Increment the count of lines processed
        file_lines += 1 

        # Log progress every 100,000 lines
        if file_lines % 100000 == 0:

            log.info(f"{created.strftime('%Y-%m-%d %H:%M:%S')} : {file_lines:,} : {bad_lines:,} : {file_bytes_processed:,}:{(file_bytes_processed / file_size) * 100:.0f}%")

    # Log completion stats
    log.info(f"Complete : {file_lines:,} : {bad_lines:,}")

    # Remove .zst extension and add .json instead
    json_file = os.path.splitext(file_path)[0] + '.json'

    # Open the file in write mode and use json.dump to write the list to the file
    with open(json_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    log.info(f"Data has been written to {json_file}")
