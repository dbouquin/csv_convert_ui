import time

class TaskManager:
    def __init__(self):
        self.tasks = {}

    def start_task(self):
        task_id = self._generate_task_id()
        self.tasks[task_id] = {
            'progress': 0,
            'start_time': time.time()
        }
        return task_id

    def process_file(self, task_id, file):
        # Example long-running file processing
        # Modify this method with your actual file processing logic

        # Here, we simulate a time-consuming task by sleeping for 2 seconds
        time.sleep(2)

        # Update the task progress to 100% after processing is complete
        self.tasks[task_id]['progress'] = 100

    def get_task_progress(self, task_id):
        task = self.tasks.get(task_id)
        if task:
            progress = task['progress']
            elapsed_time = time.time() - task['start_time']
            estimated_time = self._calculate_estimated_time(progress, elapsed_time)
            return progress, estimated_time
        return None, None

    def _generate_task_id(self):
        # Generate a unique task ID, e.g., using UUID
        # Modify this method according to your requirements
        return str(uuid.uuid4())

    def _calculate_estimated_time(self, progress, elapsed_time):
        # Calculate the estimated time remaining based on progress and elapsed time
        if progress == 0:
            return None
        estimated_time = (elapsed_time / progress) * (100 - progress)
        return round(estimated_time, 2)