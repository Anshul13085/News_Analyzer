import os

# Force Transformers to not load TensorFlow
os.environ["TRANSFORMERS_NO_TF"] = "1"

# Now import your actual app AFTER setting env var
from backend.app import app
