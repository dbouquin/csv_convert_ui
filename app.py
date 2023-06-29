from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from task_manager.task_manager import TaskManager
import uuid
import time
import os

app = Flask(__name__)
task_manager = TaskManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if request.method == 'POST':
        # Start a new task and get the task identifier
        task_id = task_manager.start_task()

        # Retrieve the uploaded file
        file = request.files['file']

        # Process the file asynchronously in the task manager
        task_manager.process_file(task_id, file)

        # Return the task identifier to the client
        return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def progress(task_id):
    # Get the progress and estimated time remaining for the task
    progress, estimated_time = task_manager.get_task_progress(task_id)

    # Return the progress information to the client
    return jsonify({'progress': progress, 'estimated_time': estimated_time})

if __name__ == '__main__':
    app.run(debug=True)
