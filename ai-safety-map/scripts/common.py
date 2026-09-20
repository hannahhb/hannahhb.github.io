"""Shared helpers: polite HTTP, caching, name normalisation."""
import hashlib, json, os, re, time, unicodedata, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CACHE = os.path.join(HERE, ".cache")
UA = "ai-safety-field-map/1.0 (research project; +https://hannahhb.github.io/)"
MAILTO = "drvkbansal@gmail.com"          # OpenAlex polite pool
# A free OpenAlex key gets its own budget instead of sharing one per IP address.
# Get one at https://help.openalex.org/api/authentication/ then:
#     export OPENALEX_API_KEY=...



def _read_key(env_var, filename):
    """Keys live outside the repo. This directory is published to the web,
    so a key committed here would be public the moment it is pushed."""
    val = os.environ.get(env_var, "").strip()
    if val:
        return val
    path = os.path.expanduser(f"~/.config/ai-safety-map/{filename}")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read().strip()
    return ""


S2_KEY = _read_key("S2_API_KEY", "s2_key")
OPENALEX_KEY = _read_key("OPENALEX_API_KEY", "openalex_key")

os.makedirs(CACHE, exist_ok=True)
os.makedirs(DATA, exist_ok=True)


def _cache_path(key):
    return os.path.join(CACHE, hashlib.sha1(key.encode()).hexdigest() + ".json")


def get(url, *, data=None, headers=None, cache=True, pause=0.12, retries=6):
    """GET/POST with on-disk caching and backoff. Returns decoded text."""
    key = url + (data.decode() if isinstance(data, bytes) else (data or ""))
    path = _cache_path(key)
    if cache and os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))["body"]

    hdr = {"User-Agent": UA}
    if OPENALEX_KEY and "api.openalex.org" in url:
        hdr["Authorization"] = "Bearer " + OPENALEX_KEY
    if headers:
        hdr.update(headers)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdr)
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
            if cache:
                json.dump({"body": body}, open(path, "w", encoding="utf-8"))
            time.sleep(pause)
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429 and not OPENALEX_KEY and "api.openalex.org" in url:
                raise RuntimeError(
                    "OpenAlex daily budget for this IP is exhausted. Get a free key at "
                    "https://help.openalex.org/api/authentication/ and re-run with "
                    "OPENALEX_API_KEY=... set; cached queries still work meanwhile."
                ) from e
            if e.code in (429, 500, 502, 503):
                time.sleep(min(60, 5 * (2 ** attempt)))   # 5,10,20,40,60,60s
                continue
            raise
        except Exception as e:                      # timeouts, resets
            last = e
            time.sleep(2 ** attempt)
    raise last


def norm_name(s):
    """Fold a display name to a comparison key."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    s = re.sub(r"\b(dr|prof|professor|phd)\b\.?", " ", s.lower())
    s = re.sub(r"[^a-z ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def save(name, obj):
    path = os.path.join(DATA, name)
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"  wrote {os.path.relpath(path, HERE)} ({os.path.getsize(path)//1024} KB)")
    return path


def load(name, default=None):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))
