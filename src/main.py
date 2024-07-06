from typing import Optional, List
from enum import Enum
import os
import argparse
import logging
from src.youtube.upload_video import main as upload_video, Privacy, UploadStatus
from src import database as db

VIDEO_FILE_TYPES = ['.mp4', '.mov', '.mkv']

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def scan_dir(directory: str, recursive: bool) -> List[str]:
    # Scan the directory for files, only recursively if specified
    if recursive:
        return [os.path.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames if os.path.splitext(f)[1].lower() in VIDEO_FILE_TYPES]
    else:
        return [os.path.join(directory, f) for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in VIDEO_FILE_TYPES]

def main():
    parser = argparse.ArgumentParser(description="Scan directory for new volleyball videos to upload to YouTube")
    parser.add_argument("--directory", type=str, required=False, help="The directory to scan for new volleyball videos", default="/mnt/user/media/volleyball")
    parser.add_argument("--recursive", required=False, action="store_true", help="Scan the directory recursively", default=False)
    parser.add_argument("--force", required=False, action="store_true", help="Force the upload of all videos", default=False)
    parser.add_argument("--privacy", type=Privacy, choices=list(Privacy), required=False, help="The privacy setting for the video", default=Privacy.PRIVATE)
    args = parser.parse_args()

    uploads = db.get_uploads()

    files = scan_dir(args.directory, args.recursive)
    for file in files:
        filename = os.path.basename(file)
        if filename in uploads[uploads["status"].isin([UploadStatus.UPLOADED, UploadStatus.PENDING])].filename.values:
            logger.info(f"Skipping {file} as it has already been uploaded")
            continue

        db.insert_upload(file, args.privacy)
        logger.debug(f"Inserted {file} into the database")

        status = upload_video(file, filename, args.privacy)
        logger.info(f"Upload status for {file}: {status}")

        db.update_upload_status(filename, status)
        logger.debug(f"Updated status for {file} to {status}")

if __name__ == "__main__":
    main()