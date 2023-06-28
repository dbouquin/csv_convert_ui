from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from csv_transformer import modify_csv
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
        modified_file_path = modify_csv(file_path)
        modified_file_name = os.path.basename(modified_file_path)

        return redirect(url_for("confirmation", filename=modified_file_name))

    return render_template("upload.html")

@app.route("/confirmation/<filename>")
def confirmation(filename):
    return render_template("confirmation.html", filename=filename)

@app.route("/download/<filename>")
def download(filename):
    exports_dir = app.config["EXPORTS_DIR"]
    return send_from_directory(exports_dir, filename, as_attachment=True)

if __name__ == "__main__":
    app.run()

#%%
