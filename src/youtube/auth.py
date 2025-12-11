import httplib2
import os
import sys

from googleapiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

from src.my_types import SafeNamespace

CLIENT_SECRETS_FILE = os.environ.get("CLIENT_SECRETS_FILE", "client_secrets.json")
YOUTUBE_API_SCOPES = os.environ.get(
    "YOUTUBE_SCOPES", "https://www.googleapis.com/auth/youtube.upload,https://www.googleapis.com/auth/youtube"
).split(",")
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MISSING_CLIENT_SECRETS_MESSAGE = f"""
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   {os.path.abspath(os.path.join(os.path.dirname(__file__), CLIENT_SECRETS_FILE))}

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""


def get_authenticated_service(args):
    client_secrets_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), CLIENT_SECRETS_FILE)
    )
    flow = flow_from_clientsecrets(
        client_secrets_path,
        scope=YOUTUBE_API_SCOPES,
        message=MISSING_CLIENT_SECRETS_MESSAGE,
    )

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()),
    )


if __name__ == "__main__":
    get_authenticated_service(
        args=SafeNamespace(
            noauth_local_webserver=False,
            logging_level="DEBUG",
            auth_host_name="localhost",
            auth_host_port=[8080, 8090],
        )
    )

    import shutil
    shutil.copy(
        "src/youtube/auth.py-oauth2.json",
        "/Volumes/appdata/youtube-uploader-python/oauth/uploader-oauth2.json",
    )
