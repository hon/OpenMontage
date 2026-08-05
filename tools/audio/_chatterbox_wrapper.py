"""Chatterbox inference wrapper — pre-patches pkuseg download before importing chatterbox.

This wrapper exists solely to work around the network-bound pkuseg Chinese
segmentation model download that triggers on first import.  It:

  1. Patches spacy_pkuseg.download._download_url_to_file to use a 600s timeout
  2. Falls through to the real inference script passed via -c

Usage:  python3 _chatterbox_wrapper.py -c "the real inline script"
"""

import os
import sys

# Forward HTTP_PROXY to the requests library that pkuseg uses internally
_HTTP_PROXY = "http://127.0.0.1:50889"
os.environ.setdefault("HTTP_PROXY", _HTTP_PROXY)
os.environ.setdefault("HTTPS_PROXY", _HTTP_PROXY)
os.environ.setdefault("http_proxy", _HTTP_PROXY)
os.environ.setdefault("https_proxy", _HTTP_PROXY)
os.environ.setdefault("REQUESTS_CA_BUNDLE", "")

# ---------------------------------------------------------------------------
# Pre-patch spacy_pkuseg before chatterbox imports it
# ---------------------------------------------------------------------------
_PATCH_CODE = r"""
import spacy_pkuseg.download as _pkuseg_dl

# Patch 1: extend pkuseg download timeout from 5s to 600s
_orig_download = _pkuseg_dl._download_url_to_file

def _patched_download(url, filename, hash_prefix=None, progress=True):
    import requests
    timeout = 600
    chunk_size = 8192
    print(f"[chatterbox_wrapper] Downloading {url} to {filename} (timeout={timeout}s)...", flush=True)
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    with open(filename, "wb") as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)
    print(f"[chatterbox_wrapper] Download complete: {filename}", flush=True)

_pkuseg_dl._download_url_to_file = _patched_download
if hasattr(_pkuseg_dl, 'authenticate'):
    _pkuseg_dl.authenticate = lambda url=None, headers=None: None
print("[chatterbox_wrapper] pkuseg download patched (timeout=600s)", flush=True)

# Patch 2: make ChineseCangjieConverter._init_segmenter tolerate
# any error (not just ImportError), so the model loads even when
# the pkuseg model download fails entirely.
import chatterbox.models.tokenizers.tokenizer as _tok_mod

_orig_init_segmenter = _tok_mod.ChineseCangjieConverter._init_segmenter

def _safe_init_segmenter(self):
    try:
        _orig_init_segmenter(self)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            f"pkuseg segmenter init failed: {exc} — continuing without segmentation"
        )
        self.segmenter = None

_tok_mod.ChineseCangjieConverter._init_segmenter = _safe_init_segmenter
print("[chatterbox_wrapper] ChineseCangjieConverter._init_segmenter hardened", flush=True)
"""

if __name__ == "__main__":
    exec(_PATCH_CODE, globals())
    # Forward all remaining args as a new process
    # Usage: python3 _chatterbox_wrapper.py -c "the inline script"
    # or:    python3 _chatterbox_wrapper.py <file.py>
    if len(sys.argv) > 1:
        if sys.argv[1] == "-c" and len(sys.argv) > 2:
            # python3 wrapper.py -c "script text"
            exec(sys.argv[2], globals())
        elif not sys.argv[1].startswith("-"):
            # python3 wrapper.py script.py
            exec(open(sys.argv[1]).read(), globals())
        else:
            # Treat as raw script text (backward compat)
            exec(sys.argv[1], globals())
    else:
        print("[chatterbox_wrapper] no script provided", file=sys.stderr)
        sys.exit(1)
