#!/usr/bin/python

from argparse import Namespace
from collections import namedtuple
import httplib2
import os
import random
import sys
import time
import logging
from enum import Enum
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


class UploadStatus(Enum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"

class Privacy(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"

    def __str__(self):
        return self.value

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.cloud.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))


def get_authenticated_service(args):
    client_secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), CLIENT_SECRETS_FILE))
    flow = flow_from_clientsecrets(client_secrets_path,
                                   scope=YOUTUBE_UPLOAD_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))


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

    resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.


def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            logger.info("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    logger.info("Video id '%s' was successfully uploaded." %
                          response['id'])
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
    ) -> UploadStatus:
    argparser.add_argument("--file", required=True, help="Video file to upload")
    argparser.add_argument("--title", required=True, help="Video title")
    argparser.add_argument("--privacyStatus", type=str , default=Privacy.PRIVATE.value, help="Video privacy status.")
    argparser.add_argument("--description", help="Video description", default="")
    argparser.add_argument("--category", default="22", help="Numeric video category. " + "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    argparser.add_argument("--keywords", help="Video keywords, comma separated", default="")
    args = argparser.parse_args([
        "--file", file,
        "--title", title,
        "--privacyStatus", privacy_status.value,
        "--noauth_local_webserver"
    ])

    if not os.path.exists(args.file):
        logger.exception(f"File does not exist: {args.file}")
        return UploadStatus.FAILED

    youtube = get_authenticated_service(args)
    try:
        initialize_upload(youtube, args)
        return UploadStatus.UPLOADED
    except HttpError as e:
        logger.exception("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
        return UploadStatus.FAILED
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        return UploadStatus.FAILED
