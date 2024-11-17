from datetime import datetime

def get_current_datetime():
    return datetime.now().strftime("%A, %B %d, %Y, %H:%M")