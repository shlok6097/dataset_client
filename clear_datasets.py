"""
Clear Datasets Utility
Safely removes all generated dataset files, checkpoints, manifest, and SQLite DB
to restart generation fresh from 0.
"""

import os
import shutil
from config import CONFIG
from logger import logger

def clear_all_datasets():
    target_dir = CONFIG.get("output_dir", "output_datasets")
    if os.path.exists(target_dir):
        for fname in os.listdir(target_dir):
            fpath = os.path.join(target_dir, fname)
            try:
                if os.path.isfile(fpath) or os.path.islink(fpath):
                    os.unlink(fpath)
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
            except Exception as e:
                logger.error(f"Failed to delete {fpath}: {e}")
        logger.info(f"Successfully cleared all generated datasets in '{target_dir}'.")
    else:
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Created fresh directory '{target_dir}'.")

if __name__ == "__main__":
    clear_all_datasets()
    print("SUCCESS: Generated dataset and checkpoint state completely cleared!")

