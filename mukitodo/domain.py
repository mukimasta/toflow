class TodoItemDomain:
    def __init__(self, title: str, status: str = "active"):
        self.title = title
        self.status = status

    def mark_sleeping(self):
        self.status = "sleeping"

    def mark_active(self):
        self.status = "active"

    def mark_completed(self):
        self.status = "completed"

