import os
import shutil
import tarfile

def package_model():
    # Create directories
    os.makedirs("model/code", exist_ok=True)
    os.makedirs("model/model", exist_ok=True)
    
    # Copy files
    files_to_copy = {
        "inference.py": "model/code/",
        "requirements.txt": "model/code/",
        # Add any other necessary files
    }
    
    for src, dest in files_to_copy.items():
        shutil.copy2(src, dest)
    
    # Create tar.gz
    with tarfile.open("model.tar.gz", "w:gz") as tar:
        tar.add("model", arcname=".")
    
    print("Created model.tar.gz")

if __name__ == "__main__":
    package_model()