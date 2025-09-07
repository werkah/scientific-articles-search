import os, urllib.parse, socket


def is_elasticsearch_reachable():
    try:
        socket.gethostbyname_ex("elasticsearch")
        return True
    except:
        return False


ELASTICSEARCH_HOST = os.getenv(
    "ELASTICSEARCH_HOST",
    "elasticsearch" if is_elasticsearch_reachable() else "localhost",
)
ELASTICSEARCH_PORT = int(os.getenv("ELASTICSEARCH_PORT", 9200))
ELASTICSEARCH_URL = os.getenv(
    "ELASTICSEARCH_URL", f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}"
)

_parsed = urllib.parse.urlparse(ELASTICSEARCH_URL)
HOST = _parsed.hostname or ELASTICSEARCH_HOST
PORT = _parsed.port or ELASTICSEARCH_PORT
