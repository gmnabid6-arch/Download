# Install:  pip install flask flask-cors yt-dlp
# Also install ffmpeg on the server
# Run:      python server.py
import os, tempfile, shutil
from flask import Flask, request, send_file, jsonify, after_this_request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
# After deploying, replace "*" with your GitHub Pages address, e.g. "https://username.github.io"
CORS(app, origins="*", expose_headers=["Content-Disposition"])

AUDIO = {"mp3", "m4a", "wav", "ogg", "flac", "aac"}
CODEC = {"ogg": "vorbis"}

@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    fmt = data.get("format", "mp4")
    q = data.get("quality", "best")
    if not url.startswith(("http://", "https://")):
        return jsonify(error="Invalid link."), 400
    if fmt not in AUDIO | {"mp4", "webm"}:
        return jsonify(error="Unsupported format."), 400

    tmp = tempfile.mkdtemp()
    opts = {"outtmpl": os.path.join(tmp, "%(title).80B.%(ext)s"),
            "noplaylist": True, "quiet": True}
    h = f"[height<={q}]" if q.isdigit() else ""

    if fmt in AUDIO:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": CODEC.get(fmt, fmt),
            "preferredquality": {"best": "320", "1080": "256", "720": "192", "480": "128"}.get(q, "192"),
        }]
    elif fmt == "mp4":
        opts["format"] = f"bv*{h}+ba/b{h}/b"
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = f"bv*{h}+ba/b{h}/b"
        opts["merge_output_format"] = "webm"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
        files = os.listdir(tmp)
        path = os.path.join(tmp, files[0])
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        return jsonify(error="Could not download this link."), 400

    @after_this_request
    def cleanup(resp):
        shutil.rmtree(tmp, ignore_errors=True)
        return resp

    return send_file(path, as_attachment=True, download_name=os.path.basename(path))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
