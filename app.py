import csv
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file
import os

app = Flask(__name__)
app.config["UPLOADS_DIR"] = "uploads"
app.config["EXPORTS_DIR"] = "exports"

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file found"

        file = request.files["file"]

        if file.filename == "":
            return "File name is empty"

        file_path = os.path.join(app.config["UPLOADS_DIR"], file.filename)
        file.save(file_path)

        # Modify the CSV file and get a new file path
        modified_file = modify_csv(file_path)

        return redirect(url_for("confirmation", filename=file.filename))

    return render_template("upload.html")

def modify_csv(file_path):
    # Generate the new file name
    new_file_path = os.path.splitext(file_path)[0]
    modified_file = new_file_path + "_modified.csv"
    exports_dir = app.config["EXPORTS_DIR"]
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

    return modified_file

@app.route("/confirmation/<filename>")
def confirmation(filename):
    return render_template("confirmation.html", filename=filename)

@app.route("/download/<filename>")
def download(filename):
    exports_dir = app.config["EXPORTS_DIR"]
    return send_from_directory(exports_dir, filename, as_attachment=True)

if __name__ == "__main__":
    app.run()
