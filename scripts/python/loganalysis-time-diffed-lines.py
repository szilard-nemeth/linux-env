# CHATGPT: TODO ADD LINK

import re
import argparse
from datetime import datetime

# Function to parse the timestamp and convert it to a datetime object
def parse_timestamp(line):
    timestamp_str = line.split()[0] + " " + line.split()[1]  # 'YYYY/MM/DD HH:MM:SS'
    return datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")

# Main function
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Process logs and compute time differences between 'Detected terminal status' and 'Requesting GET from Airflow API'.")
    parser.add_argument("logfile", help="Path to the input log file.")
    parser.add_argument("outputfile", help="Path to the output file where results will be saved.")
    
    args = parser.parse_args()

    # Define the regex patterns for matching the relevant log lines
    detected_pattern = r"DEBUG runs.go:1005 Detected terminal status.*\[(requestId [^\]]+)\]"
    requesting_pattern = r"DEBUG airflow.go:400 Requesting GET from Airflow API.*\[(requestId [^\]]+)\]"

    # Read the log file
    with open(args.logfile, 'r') as file:
        lines = file.readlines()

    # Store the last "Detected terminal status" line and its timestamp
    last_detected = None
    last_detected_idx = 0
    last_detected_time = None
    lines_between = 0

    # Loop through the lines and process each one
    with open(args.outputfile, 'w') as output_file:
        for i, line in enumerate(lines):
            detected_match = re.search(detected_pattern, line)
            if detected_match:
                # Store the line and the timestamp
                last_detected = line
                last_detected_idx = i
                last_detected_time = parse_timestamp(line)
                continue  # Move to the next line
            
            requesting_match = re.search(requesting_pattern, line)
            if requesting_match and last_detected:
                # Extract the timestamp of the "Requesting GET from Airflow API" line
                requesting_time = parse_timestamp(line)
                
                # Compute the time difference in seconds
                time_diff = (requesting_time - last_detected_time).total_seconds()
                idx_diff = i - last_detected_idx
                
                # Write the results to the output file
                output_file.write(f"{last_detected.strip()}\n{line.strip()}\nTime Difference: {int(time_diff)} seconds; Lines between: {idx_diff - 1}\n\n")
                
                # Reset the last_detected to None after pairing
                last_detected = None
                last_detected_idx = 0
                last_detected_time = None

    print(f"Time differences have been written to {args.outputfile}")

if __name__ == "__main__":
    main()
