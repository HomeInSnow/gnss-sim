# -*- coding: utf-8 -*-
"""Create GitHub Releases and upload the packaged desktop builds.

Usage: python release_uploader.py <TOKEN>
Token is read from argv only; never stored.
"""
import json
import os
import sys
import urllib.error
import urllib.request

OWNER = "HomeInSnow"
TAG = "v2026.11.19b"
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))

RELEASES = [
    {
        "repo": "gnss-sim-desktop",
        "branch": "main",
        "name": "gnss-sim-desktop v2026.11.19b (Windows x64)",
        "body_file": ".workbuddy/release_body_gnss.md",
        "zip": "dist/release/gnss-sim-desktop_v2026.11.19b_win-x64.zip",
    },
    {
        "repo": "pocketSDR-desktop",
        "branch": "master",
        "name": "pocketSDR-desktop v2026.11.19b (Windows x64)",
        "body_file": ".workbuddy/release_body_pocket.md",
        "zip": "dist/release/pocketSDR-desktop_v2026.11.19b_win-x64.zip",
    },
]


def api(method, url, data=None):
    headers = {
        "Authorization": "token " + TOKEN,
        "Accept": "application/vnd.github+json",
        "User-Agent": "release-uploader",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with NO_PROXY.open(req, timeout=120) as f:
        return json.loads(f.read() or b"{}")


def upload_asset(rel_id, repo, zip_path):
    fname = os.path.basename(zip_path)
    size = os.path.getsize(zip_path)
    url = ("https://uploads.github.com/repos/%s/%s/releases/%s/assets"
           "?name=%s" % (OWNER, repo, rel_id, fname))
    headers = {
        "Authorization": "token " + TOKEN,
        "Accept": "application/vnd.github+json",
        "User-Agent": "release-uploader",
        "Content-Type": "application/zip",
        "Content-Length": str(size),
    }
    with open(zip_path, "rb") as fh:
        req = urllib.request.Request(url, data=fh, headers=headers, method="POST")
        with NO_PROXY.open(req, timeout=3600) as f:
            return json.loads(f.read() or b"{}")


def main():
    for spec in RELEASES:
        repo = spec["repo"]
        base = "https://api.github.com/repos/%s/%s" % (OWNER, repo)
        with open(spec["body_file"], "r", encoding="utf-8") as f:
            body = f.read()
        # reuse existing release for this tag if present
        try:
            rel = api("GET", base + "/releases/tags/" + TAG)
            print(repo, ": release exists id=", rel.get("id"))
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            rel = api("POST", base + "/releases", {
                "tag_name": TAG,
                "target_commitish": spec["branch"],
                "name": spec["name"],
                "body": body,
                "draft": False,
                "prerelease": False,
            })
            print(repo, ": release created id=", rel.get("id"))
        fname = os.path.basename(spec["zip"])
        have = {a["name"]: a for a in rel.get("assets", [])}
        if fname in have and have[fname]["size"] == os.path.getsize(spec["zip"]):
            print(repo, ": asset already uploaded, skipped:", fname)
            continue
        asset = upload_asset(rel["id"], repo, spec["zip"])
        print(repo, ": uploaded", asset["name"],
              "size=", asset["size"], "state=", asset.get("state"),
              "url=", asset.get("browser_download_url"))
    print("ALL-DONE")


if __name__ == "__main__":
    TOKEN = sys.argv[1]
    sys.exit(main())
