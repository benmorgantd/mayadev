import json

def load(filepath):
    
    with open(filepath, "r") as f:
        buildData = json.load(f)

    return buildData

def save(filepath, data):

    with open(filepath, "w+") as f:
        json.dump(data, f, indent=4)

