from argparse import Namespace
from enum import Enum


class SafeNamespace(Namespace):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __getattr__(self, _):
        return None


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
