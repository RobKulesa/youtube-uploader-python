import pandas as pd
import psycopg2
import logging
import os
from typing import Dict
from psycopg2.extensions import connection
from src.youtube.upload_video import UploadStatus, Privacy

DATABASE_CONFIG = {
    "host": "192.168.4.98",
    "port": "5432",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres"
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_uploads() -> pd.DataFrame:
    stmt = "SELECT * FROM volleyball_uploader.uploads"
    return connect_and_read(stmt)

def insert_upload(file: str, privacy: Privacy) -> None:
    path, filename = os.path.split(file)
    stmt = f"INSERT INTO volleyball_uploader.uploads (filename, status, privacy, path) VALUES ('{filename}', '{UploadStatus.PENDING}', '{privacy}', '{path}')"
    connect_and_execute(DATABASE_CONFIG, stmt)
    return

def update_upload_status(filename: str, status: UploadStatus) -> None:
    stmt = f"UPDATE volleyball_uploader.uploads SET status = '{status}' WHERE filename = '{filename}'"
    connect_and_execute(DATABASE_CONFIG, stmt)
    return

def create_conn(database_config: Dict, connect_timeout: int = 5) -> connection:
    try:
        conn = psycopg2.connect(dbname=database_config["database"], user=database_config["user"],
                                host=database_config["host"],
                                password=database_config["password"], connect_timeout=connect_timeout)
        return conn
    except Exception as e:
        logger.exception("Error:" + str(e))

def connect_and_read(stmt) -> pd.DataFrame:
    try:
        conn = create_conn(DATABASE_CONFIG)
        res = pd.read_sql(stmt, conn)
        conn.close()
        return res
    except Exception as e:
        logger.exception("Error:" + str(e))

def connect_and_execute(database_config, *stmts) -> None:
    try:
        conn = create_conn(database_config)
        curs = conn.cursor()
        for stmt in stmts:
            if pd.notna(stmt):
                curs.execute(stmt)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception("Error:" + str(e))

