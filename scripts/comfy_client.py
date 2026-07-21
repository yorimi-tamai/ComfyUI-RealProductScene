"""Minimal ComfyUI API client (stdlib only).

Talks to a running ComfyUI server over HTTP:
  - upload an image into ComfyUI's input folder
  - submit an API-format workflow graph to /prompt
  - poll /history until the run finishes
  - download output images via /view

No third-party deps — uses urllib so it runs in any Python that has the
imaging libs (the ComfyUI venv already does).
"""

from __future__ import annotations

import json
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path


class ComfyUIError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, server: str = "127.0.0.1:8188", timeout: float = 5.0):
        # accept "host:port" or a full "http://host:port"
        server = server.replace("http://", "").replace("https://", "").rstrip("/")
        self.base = f"http://{server}"
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    # ---- low-level helpers -------------------------------------------------
    def _get(self, path: str) -> bytes:
        url = f"{self.base}{path}"
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            return r.read()

    def _post_json(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}{path}", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    # ---- public API --------------------------------------------------------
    def ping(self) -> bool:
        """True if the server answers. Use to fail fast with a clear message."""
        try:
            self._get("/system_stats")
            return True
        except Exception:
            return False

    def upload_image(self, path: str | Path, overwrite: bool = True) -> str:
        """Upload a local image into ComfyUI's input dir. Returns the name
        LoadImage should reference."""
        path = Path(path)
        if not path.exists():
            raise ComfyUIError(f"image not found: {path}")
        boundary = f"----psg{uuid.uuid4().hex}"
        body = bytearray()

        def field(name, value):
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body.extend(f"{value}\r\n".encode())

        field("overwrite", "true" if overwrite else "false")
        field("type", "input")
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="image"; '
            f'filename="{path.name}"\r\n'.encode())
        body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
        body.extend(path.read_bytes())
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            f"{self.base}/upload/image", data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            info = json.loads(r.read().decode("utf-8"))
        name = info["name"]
        if info.get("subfolder"):
            name = f"{info['subfolder']}/{name}"
        return name

    def submit(self, graph: dict) -> str:
        """Queue an API-format graph. Returns prompt_id."""
        resp = self._post_json("/prompt", {"prompt": graph, "client_id": self.client_id})
        if "prompt_id" not in resp:
            raise ComfyUIError(f"unexpected /prompt response: {resp}")
        return resp["prompt_id"]

    def wait(self, prompt_id: str, poll: float = 1.0, max_wait: float = 300.0) -> dict:
        """Block until the prompt finishes; return its history entry."""
        waited = 0.0
        while waited < max_wait:
            raw = self._get(f"/history/{prompt_id}")
            hist = json.loads(raw.decode("utf-8"))
            if prompt_id in hist:
                entry = hist[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise ComfyUIError(f"ComfyUI run errored: {status}")
                if entry.get("outputs"):
                    return entry
            time.sleep(poll)
            waited += poll
        raise ComfyUIError(f"timed out after {max_wait}s waiting for {prompt_id}")

    def output_images(self, history_entry: dict) -> list[dict]:
        """Extract {filename, subfolder, type} for every SaveImage output."""
        out = []
        for node_out in history_entry.get("outputs", {}).values():
            for img in node_out.get("images", []):
                out.append(img)
        return out

    def download(self, image_ref: dict) -> bytes:
        q = urllib.parse.urlencode({
            "filename": image_ref["filename"],
            "subfolder": image_ref.get("subfolder", ""),
            "type": image_ref.get("type", "output"),
        })
        return self._get(f"/view?{q}")

    def run(self, graph: dict, save_to: str | Path | None = None) -> list[bytes]:
        """Submit graph, wait, return output image bytes; optionally save first
        image to `save_to`."""
        pid = self.submit(graph)
        entry = self.wait(pid)
        images = [self.download(ref) for ref in self.output_images(entry)]
        if save_to and images:
            Path(save_to).parent.mkdir(parents=True, exist_ok=True)
            Path(save_to).write_bytes(images[0])
        return images
