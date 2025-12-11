from typing import List
import os
import argparse
import logging
import pathlib
from src.youtube.upload_video import main as upload_video, Privacy, UploadStatus
from src.youtube.auth import get_authenticated_service
from src import database as db
from src.my_types import SafeNamespace
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VIDEO_FILE_TYPES = ['.mp4', '.mov', '.mkv']

def scan_dir(directory: str, recursive: bool) -> List[str]:
    # Scan the directory for files, only recursively if specified
    if recursive:
        return [os.path.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames if os.path.splitext(f)[1].lower() in VIDEO_FILE_TYPES]
    else:
        return [os.path.join(directory, f) for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in VIDEO_FILE_TYPES]

def main():
    parser = argparse.ArgumentParser(
        description="Scan directory for new videos to upload to YouTube"
    )
    parser.add_argument(
        "--directory",
        type=str,
        required=False,
        help="The directory to scan for new videos",
        default="/videos",
    )
    parser.add_argument(
        "--recursive",
        required=False,
        action="store_true",
        help="Scan the directory recursively for new videos",
        default=False,
    )
    parser.add_argument(
        "--force",
        required=False,
        action="store_true",
        help="Force the upload of all videos, whether they have already been uploaded or not",
        default=False,
    )
    parser.add_argument(
        "--privacy",
        type=Privacy,
        choices=list(Privacy),
        required=False,
        help="The privacy setting for the video",
        default=Privacy.PRIVATE,
    )
    parser.add_argument(
        "--concurrent-uploads",
        type=int,
        required=False,
        help="The number of concurrent uploads to perform (default 10)",
        default=10,
    )
    parser.add_argument(
        "--playlist",
        type=str,
        required=False,
        help="Name of playlist to add the uploaded videos to. Visibility will match the --privacy setting",
        default=None,
    )
    args = parser.parse_args()

    youtube_api = get_authenticated_service(
        args=SafeNamespace(
            noauth_local_webserver=True,
            logging_level="INFO",
        )
    )

    playlist_id = None
    if args.playlist:
        playlists = db.get_playlists()["title"]

        if args.playlist in playlists.values:
            logger.info(f"Playlist '{args.playlist}' already exists in the database, skipping creation")
        else:
            logger.info(f"Creating playlist '{args.playlist}'")

            try:
                response = youtube_api.playlists().insert(
                    part="snippet,status",
                    body={
                        "snippet": {
                            "title": args.playlist,
                            "defaultLanguage": "en",
                        },
                        "status": {
                            "privacyStatus": args.privacy.value.lower(),
                        },
                    },
                ).execute()
                playlist_id = response["id"]
            except Exception as e:
                logger.exception(f"Failed to create playlist '{args.playlist}': {e}")
            else:
                db.insert_playlist(args.playlist, response["id"], args.privacy)
                logger.info(f"Playlist '{args.playlist}' created with ID {response['id']} and privacy {args.privacy.value}")
            
    files = scan_dir(args.directory, args.recursive)
    if len(files) == 0:
        logger.info(f"No videos found in {args.directory}")
        return
    
    with ThreadPoolExecutor(max_workers=args.concurrent_uploads) as executor:
        future_to_file = {}
        for i, file in enumerate(sorted(files)):
            filename = pathlib.Path(file).name
            stem = pathlib.Path(file).stem
            uploads = db.get_uploads()
            if not args.force and filename in uploads[uploads["status"].isin([UploadStatus.UPLOADED.value, UploadStatus.PENDING.value])].filename.values:
                logger.info(f"Skipping {file} as it has already been uploaded")
                continue

            try:
                db.insert_upload(file, filename, args.privacy)
                logger.debug(f"Inserted {file} into the database")
            except Exception as e:
                logger.exception(f"Failed to insert {file} into the database: {e}")
                continue

            future = executor.submit(
                upload_video,
                file,
                stem.replace("_", " ").replace(":", "/"),
                args.privacy,
            )
            future_to_file[future] = (file, filename)

        for future in as_completed(future_to_file):
            file, filename = future_to_file[future]
            try:
                status, video_id = future.result()
                logger.info(f"Upload status for {file}: {status}")
            except Exception as e:
                logger.exception(f"Failed to upload {file}: {e}")
                db.update_upload_status(filename, UploadStatus.FAILED)
            else:
                db.update_upload_status(filename, status)
                if video_id:
                    db.update_video_id(filename, video_id)
                    logger.info(f"Updated status for {file} to {status} with video_id {video_id}")
                else:
                    logger.info(f"Updated status for {file} to {status}")
                
                if args.playlist and status == UploadStatus.UPLOADED and playlist_id is not None:
                    try:
                        youtube_api.playlistItems().insert(
                            part="snippet",
                            body={
                                "snippet": {
                                    "playlistId": playlist_id,
                                    "position": i,
                                    "resourceId": {
                                        "kind": "youtube#video",
                                        "videoId": video_id,
                                    },
                                }
                            },
                        ).execute()
                    except Exception as e:
                        logger.exception(f"Failed to add video {video_id} to playlist '{args.playlist}': {e}")
                    else:
                        logger.info(f"Added video {video_id} to playlist '{args.playlist}'")
    

if __name__ == "__main__":
    main()