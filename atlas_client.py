"""Small client for the official World Labs Atlas beta API.

Credentials stay in WLT_API_KEY or the ignored .env file. Local curl supplies
the system certificate store; secrets go through stdin rather than argv.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

BASE = "https://api.atlas-beta.worldlabs.ai/api/v2"


class Atlas:
    def __init__(self):
        self.key = os.environ.get("WLT_API_KEY")
        if not self.key:
            for line in Path(__file__).with_name(".env").read_text().splitlines():
                if line.startswith("WLT_API_KEY="):
                    self.key = line.partition("=")[2].strip()
        if not self.key or any(c in self.key for c in '\r\n"'):
            raise ValueError("Set WLT_API_KEY in .env or the environment")

    def request(self, method, path, body=None, idempotency=None):
        config = f'header = "WLT-Api-Key: {self.key}"\n'
        command = ["curl", "--config", "-", "--silent", "--show-error",
                   "--max-time", "50", "--request", method,
                   "--write-out", "\n%{http_code}", BASE + path]
        with tempfile.TemporaryDirectory() as temp:
            if body is not None:
                payload = Path(temp) / "request.json"
                payload.write_text(json.dumps(body))
                command += ["--header", "Content-Type: application/json", "--data-binary", "@" + str(payload)]
            if idempotency:
                command += ["--header", "Idempotency-Key: " + idempotency]
            result = subprocess.run(command, input=config, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError("Atlas connection failed: " + result.stderr.replace(self.key, "[redacted]"))
        data, _, status = result.stdout.rpartition("\n")
        if not status.startswith("2"):
            raise RuntimeError(f"Atlas HTTP {status}: " + data.replace(self.key, "[redacted]")[:2000])
        return json.loads(data)

    def submit(self, task, body, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        request_path = directory / "request.json"
        if request_path.exists() and json.loads(request_path.read_text()) != body:
            raise ValueError("Use a new output directory for a different request")
        request_path.write_text(json.dumps(body))
        key_path = directory / "idempotency.txt"
        if not key_path.exists():
            key_path.write_text(str(uuid.uuid4()))
        existing = directory / "operation.json"
        if existing.exists():
            return json.loads(existing.read_text())
        operation = self.request("POST", "/tasks:" + task, body, key_path.read_text())
        existing.write_text(json.dumps(operation, indent=2))
        return operation

    def poll(self, directory):
        directory = Path(directory)
        current = json.loads((directory / "operation.json").read_text())
        operation = self.request("GET", "/operations/" + current["id"])
        (directory / "operation.json").write_text(json.dumps(operation, indent=2))
        if operation.get("done") and not operation.get("error"):
            (directory / "response.json").write_text(json.dumps(operation["response"], indent=2))
        return operation

    def download(self, reference, destination):
        url = reference.get("url")
        if not url:
            url = self.request("POST", "/assets/" + reference["assetId"] + ":createReadUrl")["readUrl"]
        subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                        "--max-time", "60", url, "--output", str(destination)], check=True)


def summary(operation):
    print(json.dumps({key: operation.get(key) for key in ("id", "done", "error", "metadata")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    pose = sub.add_parser("pose")
    pose.add_argument("image")
    pose.add_argument("output")
    video = sub.add_parser("pose-video")
    video.add_argument("video")
    video.add_argument("output")
    video.add_argument("--frames", type=int, default=24)
    poll = sub.add_parser("poll")
    poll.add_argument("output")
    submit = sub.add_parser("submit")
    submit.add_argument("task")
    submit.add_argument("request")
    submit.add_argument("output")
    args = parser.parse_args()
    api = Atlas()
    if args.action == "pose-video":
        directory = Path(args.output)
        images = directory / "source-frames"
        images.mkdir(parents=True, exist_ok=True)
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", args.video
        ], text=True)
        duration = float(json.loads(probe)["format"]["duration"])
        for index in range(args.frames):
            image = images / f"{index:03d}.jpg"
            if not image.exists():
                timestamp = .2 + index * max(0, duration - .5) / max(1, args.frames - 1)
                subprocess.run([
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(timestamp),
                    "-i", args.video, "-frames:v", "1", "-vf", "scale=720:1280:force_original_aspect_ratio=decrease",
                    "-q:v", "3", str(image)
                ], check=True)
        request = {"frames": [{"imageAsset": {"base64": "data:image/jpeg;base64," +
                    base64.b64encode((images / f"{index:03d}.jpg").read_bytes()).decode()}}
                    for index in range(args.frames)],
                   "canonicalizeToFirstFrame": True, "targetResolution": [720, 1280], "refinePoses": True}
        summary(api.submit("images2PosedRGBD", request, directory))
    elif args.action == "pose":
        encoded = base64.b64encode(Path(args.image).read_bytes()).decode()
        request = {"frames": [{"imageAsset": {"base64": "data:image/jpeg;base64," + encoded}}],
                   "canonicalizeToFirstFrame": True, "targetResolution": [1280, 720]}
        summary(api.submit("images2PosedRGBD", request, args.output))
    elif args.action == "poll":
        summary(api.poll(args.output))
    else:
        summary(api.submit(args.task, json.loads(Path(args.request).read_text()), args.output))
