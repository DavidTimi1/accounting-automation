import datetime
import json

def log_error(error, error_type="runtime"):
    log_file = f"data/logs/{error_type}.log"

    with open(log_file, "a") as f:
        data = {
            "error": error,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        f.write(json.dumps(data) + "\n")


def log_info(info, log_type="runtime", show_in_terminal=True):
    log_file = f"data/logs/{log_type}.log"

    with open(log_file, "a") as f:
        data = {
            "info": info,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        f.write(json.dumps(data) + "\n")

    if show_in_terminal:
        print(data)