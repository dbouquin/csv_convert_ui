import csv
import os

def modify_csv(file_path):
    # Generate the new file name
    new_file_path = os.path.splitext(file_path)[0]
    modified_file = new_file_path + "_modified.csv"
    exports_dir = os.path.join(os.path.dirname(file_path), "../exports")
    os.makedirs(exports_dir, exist_ok=True)
    modified_file_path = os.path.join(exports_dir, os.path.basename(modified_file))

    with open(file_path, "r", newline="") as input_file, open(modified_file_path, "w", newline="") as output_file:
        reader = csv.reader(input_file)
        writer = csv.writer(output_file)

        # Modify the header row
        header = next(reader)
        header[0] = "SUCCESS"
        writer.writerow(header)

        # Copy the remaining rows
        for row in reader:
            writer.writerow(row)

    return modified_file_path
