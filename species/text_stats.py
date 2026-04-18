import re

def run(text):
    words = text.split()
    return {"words": len(words), "chars": len(text)}