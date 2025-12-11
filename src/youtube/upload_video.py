#!/usr/bin/python

import httplib2
import os
import random
import time
import logging
from typing import Optional

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from src.my_types import Privacy, SafeNamespace, UploadStatus
from src.youtube.auth import get_authenticated_service

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


def initialize_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category
        ),
        status=dict(
            privacyStatus=options.privacyStatus
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request, options.title)

# This method implements an exponential backoff strategy to resume a
# failed upload.


def resumable_upload(insert_request, title) -> str:
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            logger.info(f"Uploading video {title}...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    logger.info("Video id '%s' was successfully uploaded." %
                          response['id'])
                    return response['id']
                else:
                    raise Exception("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            logger.warning(error)
            retry += 1
            if retry > MAX_RETRIES:
                raise Exception(f"Failed {MAX_RETRIES} times. No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            logger.warning("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)

def main(
        file: str, 
        title: str,
        privacy_status: Optional[Privacy] = Privacy.PRIVATE
    ) -> tuple[UploadStatus, Optional[str]]:

    args = SafeNamespace(
        file=file,
        title=title,
        privacyStatus=privacy_status.value,
        logging_level='ERROR',
        noauth_local_webserver=True
    )

    if not os.path.exists(args.file):
        logger.exception(f"File does not exist: {args.file}")
        return UploadStatus.FAILED, None

    youtube = get_authenticated_service(args)
    try:
        video_id = initialize_upload(youtube, args)
        return UploadStatus.UPLOADED, video_id
    except HttpError as e:
        logger.exception("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
        return UploadStatus.FAILED, None
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        return UploadStatus.FAILED, None
