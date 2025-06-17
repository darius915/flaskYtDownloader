from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import threading
import re
import os

app = Flask(__name__)
download_progress = {}
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/formats', methods=['POST'])
def list_formats():
    url = request.get_json(force=True).get("url")
    video_id = extract_video_id(url)
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = []
            for f in info_dict.get("formats", []):
                resolution = f.get("format_note") or f.get("resolution") or f"{f.get('height', '')}p"
                if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("height", 0) in [360, 480]:
                    formats.append({
                        "format_id": f["format_id"],
                        "resolution": resolution,
                        "ext": f["ext"],
                        "has_audio": True,
                        "has_video": True
                    })
            formats.append({
                "format_id": "bestaudio",
                "resolution": "audio only (mp3)",
                "ext": "mp3",
                "has_audio": True,
                "has_video": False
            })
            return jsonify({"formats": formats, "video_id": video_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json(force=True)
    url = data.get("url")
    format_id = data.get("format_id")
    video_id = extract_video_id(url)

    def run_download():
        is_audio_only = format_id == 'bestaudio'
        ydl_opts = {
            'format': 'bestaudio' if is_audio_only else format_id,
            'progress_hooks': [lambda d: download_progress.update({video_id: d})],
            'outtmpl': f'{DOWNLOAD_FOLDER}/{video_id}.%(ext)s',
            'merge_output_format': 'mp3' if is_audio_only else 'mp4',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if is_audio_only else [],
            'quiet': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            }
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            download_progress[video_id] = {'status': 'finished'}
        except Exception as e:
            download_progress[video_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=run_download).start()
    return jsonify({
        "message": "Download started",
        "video_id": video_id,
        "download_url": f"/downloaded/{video_id}"
    })

@app.route('/progress/<video_id>')
def progress(video_id):
    return jsonify(download_progress.get(video_id, {"status": "unknown"}))

@app.route('/downloaded/<video_id>')
def serve_file(video_id):
    for ext in ['mp4', 'mp3']:
        file_path = os.path.join(DOWNLOAD_FOLDER, f'{video_id}.{ext}')
        if os.path.exists(file_path):
            return send_from_directory(DOWNLOAD_FOLDER, f'{video_id}.{ext}', as_attachment=True)
    return "File not found", 404

def extract_video_id(url):
    match = re.search(r"(?:v=|youtu.be/)([\w-]+)", url)
    return match.group(1) if match else "unknown"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug = True,host='0.0.0.0', port=port)
