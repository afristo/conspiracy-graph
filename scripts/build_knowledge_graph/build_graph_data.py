# Import native libraries
from collections import defaultdict
import logging
import json
import os

# Import third-party libraries
import pandas as pd


# Set constant values for the script, enforcing them with a class
class Constants:
    """
    A class specifically for enforcing constant values in the script.
    """

    CONFIG = "./scripts/build_knowledge_graph/build_graph_config.json"
    LARGE_RENORMALIZATION_THRESHOLD = 10
    SMALL_RENORMALIZATION_THRESHOLD = 98


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


def ingest_data(directory_path):
    """
    Ingests the filtered triples for building the knowledge graph.

    :param directory_path: Path to the input data files.
    :return merged_input_data: All input data merged into a list of dictionaries.
    """

    merged_input_data = []

    # Loop through all files in the directory
    for filename in os.listdir(directory_path):

        # Ensure we only ingest .jsonl files
        if filename.endswith(".jsonl"):

            # Construct the full filepath
            file_path = os.path.join(directory_path, filename)

            # Open the individual file
            with open(file_path, "r", encoding="utf-8") as f:

                # Parse each line as a JSON object
                for line in f:

                    # Remove potential space
                    line = line.strip()

                    # Skip empty lines
                    if line:

                        try:

                            # Parse and append the data
                            merged_input_data.append(json.loads(line))

                        except json.JSONDecodeError as e:

                            logging.error("Error parsing line in %s: %s", filename, e)
                            logging.error("Json line: %s", line)

    return merged_input_data


def output_data(data, output_dir, filename):
    """
    Writes a list of dictionaries to a JSON file.

    :param data: The data to write
    :param output_dir: The location to write to
    :param filename: The filename for the output data
    """

    # Ensure output directory exists
    if not os.path.exists(output_dir):

        os.makedirs(output_dir)

    # Ensure .json is the extension
    if not filename.endswith(".json"):

        filename += ".json"

    # Create the full output path
    output_path = os.path.join(output_dir, filename)

    logging.info("Writing %s records to %s...", len(data), output_path)

    # Write the data
    with open(output_path, "w", encoding="utf-8") as f:

        json.dump(data, f)

    logging.info("JSON write complete.")


def generate_raw_edge_counts(kg_nodes_edges):
    """
    Counts unique pairs of linked_head and linked_tail (both directions) and returns a
    list of dictionaries with head, tail, and raw_edge_weight.

    :param kg_nodes_edges: A list of nodes and edges.
    :return distinct_kg_nodes_edges: A list of dictionaries containing the distinct counts of
    triples.
    """

    # Generate an object to store the data
    edge_counts = defaultdict(int)

    # Enumerate over the data
    for row in kg_nodes_edges:

        # Extract the head and tail values
        h = row["linked_head"]
        t = row["linked_tail"]

        # Ignore cases where a node is related to itself
        if h == t:
            continue

        # Sort the pair so (A, B) and (B, A) are treated identically
        key = tuple(sorted([h, t]))

        # Increase the count for this node pair
        edge_counts[key] += 1

    # Convert counts to list of dictionaries
    distinct_kg_nodes_edges = [
        {"head": k[0], "tail": k[1], "raw_edge_weight": v}
        for k, v in edge_counts.items()
    ]

    return distinct_kg_nodes_edges


def normalize_edges(kg_data_raw_edge_counts, renormalization_threshold):
    """
    Normalizes raw edge weights between 0 and 1, removes the bottom X percent, and renormalizes
    the remaining edges.

    :param kg_data_raw_edge_counts: A list of nodes and edges with raw counts for their edge
    weight.
    :param renormalization_threshold: The cutoff for renormalization, represented as an integer
    between 0 and 100.
    
    :return kg_data_raw_edge_counts: A list of dictionaries containing the head, tail and edge
    weight normalized between 0 and 1.
    """

    # Protect input from mutation
    kg_data_raw_edge_counts = [e.copy() for e in kg_data_raw_edge_counts]

    # Extract raw weights
    raw_weights = [e['raw_edge_weight'] for e in kg_data_raw_edge_counts]

    # Conduct initial normalization
    min_w = min(raw_weights)
    max_w = max(raw_weights)

    # Handle cases where all values are equal
    if max_w == min_w:

        normalized_weights = [1.0 for _ in raw_weights]

    # Handle cases where all values are not equal
    else:

        normalized_weights = [(w - min_w) / (max_w - min_w) for w in raw_weights]

    # Attach normalized weight temporarily
    for e, nw in zip(kg_data_raw_edge_counts, normalized_weights):

        e['_normalized'] = nw

    # Remove bottom X percent based on the threshold
    if renormalization_threshold > 0:

        threshold = (
            sorted(normalized_weights)[
                int(len(normalized_weights) * renormalization_threshold / 100)
                ]
            )

        kg_data_raw_edge_counts = (
            [e for e in kg_data_raw_edge_counts if e['_normalized'] > threshold]
            )

    # Renormalize the remaining edges
    if kg_data_raw_edge_counts:

        nw_remaining = [e['_normalized'] for e in kg_data_raw_edge_counts]

        min_r = min(nw_remaining)
        max_r = max(nw_remaining)

        # Handle cases where all values are equal
        if max_r == min_r:

            renormalized = [1.0 for _ in nw_remaining]

        # Handle cases where all values are not equal
        else:

            renormalized = [(w - min_r) / (max_r - min_r) for w in nw_remaining]

        # Replace key
        for e, ew in zip(kg_data_raw_edge_counts, renormalized):

            e['edge weight'] = ew
            del e['_normalized']
            del e['raw_edge_weight']

    # Log final graph stats
    num_edges = len(kg_data_raw_edge_counts)

    nodes = set()

    for e in kg_data_raw_edge_counts:

        nodes.add(e['head'])
        nodes.add(e['tail'])

    num_nodes = len(nodes)

    logging.info("After renormalization: %s nodes, %s edges", num_nodes, num_edges)

    return kg_data_raw_edge_counts


def export_gephi_csv(edge_data, output_dir, basename):
    """
    Exports Gephi-compatible CSV files (edges + nodes).

    :param edge_data: List of dicts with keys: head, tail, edge weight
    :param output_dir: Directory to write CSV files
    :param basename: Base name for output files
    """

    # Ensure the path exists
    if not os.path.exists(output_dir):

        os.makedirs(output_dir)

    # Build edges DataFrame
    edges_df = pd.DataFrame(edge_data)

    edges_df = edges_df.rename(
        columns={
            "head": "Source",
            "tail": "Target",
            "edge weight": "Weight"
        }
    )

    edges_df["Source"] = edges_df["Source"].astype(str)
    edges_df["Target"] = edges_df["Target"].astype(str)
    edges_df["Weight"] = edges_df["Weight"].astype(float)
    edges_df["Type"] = "Undirected"

    # Write the file containing the graph edges as a CSV
    edges_path = os.path.join(output_dir, f"{basename}_edges.csv")
    edges_df.to_csv(edges_path, index=False, encoding="utf-8")

    logging.info("Gephi edges CSV written to %s", edges_path)

    # Build nodes DataFrame
    nodes = set(edges_df["Source"]).union(edges_df["Target"])

    nodes_df = pd.DataFrame(
        {
            "Id": list(nodes),
            "Label": list(nodes)
        }
    )

    nodes_df["Id"] = nodes_df["Id"].astype(str)
    nodes_df["Label"] = nodes_df["Label"].astype(str)

    # Write the file containing the graph nodes as a CSV
    nodes_path = os.path.join(output_dir, f"{basename}_nodes.csv")
    nodes_df.to_csv(nodes_path, index=False, encoding="utf-8")

    logging.info("Gephi nodes CSV written to %s", nodes_path)


if __name__ == "__main__":

    # Setup logging functionality
    setup_logging()

    logging.info("Loading script config file...")

    # Load the JSON config file
    with open(file=Constants.CONFIG, mode="r", encoding="utf-8") as config_file:

        config = json.load(config_file)

    logging.info("Ingesting source data...")

    # Ingest the data
    raw_kg_triples = ingest_data(directory_path=config["input_directory"])

    logging.info("Aggregating raw edge counts...")

    # Collapse raw data into edge counts
    raw_kg_data = generate_raw_edge_counts(raw_kg_triples)

    # Output the raw counts data to a json file
    output_data(raw_kg_data, config["output_directory"], "raw_kg_data.json")

    logging.info("Normalizing edge counts...")

    # Normalize edge weights, use a low threshold to build a large graph
    large_kg_data = normalize_edges(raw_kg_data, Constants.LARGE_RENORMALIZATION_THRESHOLD)

    # Output the large kg data to a json file
    output_data(large_kg_data, config["output_directory"], "large_kg_data.json")

    # Normalize edge weights, use a low threshold to build a smaller graph
    small_kg_data = normalize_edges(raw_kg_data, Constants.SMALL_RENORMALIZATION_THRESHOLD)

    # Output the small kg data to a json file
    output_data(small_kg_data, config["output_directory"], "small_kg_data.json")

    # Export data for analysis in Gephi or a similar KG specific tool
    export_gephi_csv(small_kg_data, config["output_directory"], "conspiracy_graph")
