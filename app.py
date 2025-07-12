from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, Response
import re
import os
import logging
import threading
import time
import subprocess
import json
import requests
from werkzeug.utils import secure_filename
from mimetypes import guess_type

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit
app.config['STREAM_CHUNK_SIZE'] = 8 * 1024 * 1024  # 1MB chunks for streaming

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create downloads folder
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Validate time format (HH:MM:SS or MM:SS or SS)
def validate_time(time_str):
    return re.match(r'^(\d{1,2}:)?([0-5]?\d:)?[0-5]?\d$', time_str)

# Convert time string to seconds
def time_to_seconds(time_str):
    parts = list(map(int, time_str.split(':')))
    parts.reverse()  # Now parts are [seconds, minutes, hours] if they exist
    multipliers = [1, 60, 3600]
    seconds = 0
    for i in range(len(parts)):
        seconds += parts[i] * multipliers[i]
    return seconds

# Track download status
download_status = {}
download_lock = threading.Lock()

# YouTube cookies and headers
YT_COOKIES = cookies = {
    "__Secure-3PSID": "g.a000yAjvXKH56cEEfOdN8kQpE0wZ2ULSITkgpWv8CsPbwYcjM53Q00EdfLUo6tcTExqAmPoxLAACgYKAQ4SARMSFQHGX2MiiUQVGiZCzU_eTJQm1GD9iBoVAUF8yKrbBrK4slE8z9SHCr_Qfvj_0076",
    "SIDCC": "AKEyXzWIqBpZl8rlvo1RdV6adIyNcfDtiMeeqsi4YozGVwKCLUHjZEdRafTEBmCoB3f2-V02tA9g",
    "SID": "g.a000yAjvXKH56cEEfOdN8kQpE0wZ2ULSITkgpWv8CsPbwYcjM53QG-pHduqj4H9e0mLycbJm-wACgYKAZkSARMSFQHGX2Mitj_HNFT65dL-POGr8fxnUBoVAUF8yKrRlvrhuQtztaXZT4Qty5Ec0076",
    "__Secure-1PSIDTS": "sidts-CjEB5H03P3aOnF4aDyfSMeOxRRGXQcjXfP_xFSYwzKdaWkJR3wg7vMTPu_v-ObfA2dSPEAA",
    "SAPISID": "9T54xbVWOf_zIW-v/AXsazo3XdLyUhcCs1",
    "__Secure-1PSIDCC": "AKEyXzUXX5TIMupnq2ows5Qq3pcDk7FEIwtiaQhZym34i_ROwwJZ68l8-uo8Jjdxuo-KKa6AD9c",
    "SSID": "Aw6sllZ63la0Q_Nq3",
    "__Secure-1PAPISID": "9T54xbVWOf_zIW-v/AXsazo3XdLyUhcCs1",
    "__Secure-1PSID": "g.a000yAjvXKH56cEEfOdN8kQpE0wZ2ULSITkgpWv8CsPbwYcjM53QC8tC62UscAo0aMGZuEOjzgACgYKAW0SARMSFQHGX2MiczsPAXISbyuvO26w7xxRtxoVAUF8yKqS1nJIZ0oX5Dh1mTAF0S_m0076",
    "__Secure-3PAPISID": "9T54xbVWOf_zIW-v/AXsazo3XdLyUhcCs1",
    "__Secure-3PSIDCC": "AKEyXzU4Xh4s0TlhNxMvA6zvcAbwNNhAOchPR2C3B-NaXPrv4_9waDP_wUfMfRJqmBNZNHafIasv",
    "__Secure-3PSIDTS": "sidts-CjEB5H03P3aOnF4aDyfSMeOxRRGXQcjXfP_xFSYwzKdaWkJR3wg7vMTPu_v-ObfA2dSPEAA",
    "APISID": "o6mZWZfO8DN-iuTH/AE8hwYgkeRNylE5H0",
    "HSID": "AndK1lFdxIin_WUV4",
    "LOGIN_INFO": "AFmmF2swRQIgF7auZVQ3czCEzHP1dYNpFkN1oUyBnsULnjY1PTR2wT0CIQDLQBeIyrMv2ge3d7kqvHcDOGomKg2DEzyU1RySMIlUxw:QUQ3MjNmdy1kLUV3b05RS0kyMGszbURyTUEyVzg3YVN6S3A0b1FpQjNpazRNdkp6eTRNejZuWWxIMTVZdWxSTktTUW1yc0JkbXRlSTV1UHhDaElHcVdiMEp6Y19pSnV2Y2ltbGFEVExZYkRVVmtHTzZELVN4NGR2Y014ZVAtdFBWQ2h4dFB2SlJnWkJpRmVBQWlGMEtod3dfRGNFaTZ0dUhR",
    "PREF": "f4=4000000&f6=40000000&tz=Asia.Calcutta&f7=100"
}

YT_HEADERS = {
    'Connection': 'keep-alive',
    'User-Agent': 'com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
    'X-Youtube-Client-Name': '5',
    'X-Youtube-Client-Version': '20.10.4',
    'Origin': 'https://www.youtube.com',
    'X-Goog-Visitor-Id': 'CgtneWx0QzE2MmpKWSjpibnCBjIKCgJJThIEGgAgZw%3D%3D'
}

YT_PARAMS = {'prettyPrint': 'false'}

def extract_streams(streams):
    """Find the best video and audio streams from YouTube adaptive formats"""
    best_video = best_audio = None
    max_video = (0, 0)  # (resolution, bitrate)
    max_audio = 0  # bitrate
    
    for s in streams:
        mime = s.get('mimeType', '')
        if 'video/' in mime:
            res = s.get('width', 0) * s.get('height', 0)
            br = s.get('bitrate', 0)
            if res > max_video[0] or (res == max_video[0] and br > max_video[1]):
                best_video = s
                max_video = (res, br)
        elif 'audio/' in mime and "mp4a" in mime:
            br = s.get('bitrate', 0)
            if br > max_audio:
                best_audio = s
                max_audio = br
                
    return best_video, best_audio

def get_youtube_streams(video_id):
    """Get video and audio streams from YouTube API"""
    json_data = {
        'context': {
            'client': {
                'clientName': 'IOS',
                'clientVersion': '20.10.4',
                'deviceMake': 'Apple',
                'deviceModel': 'iPhone16,2',
                'userAgent': 'com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)',
                'osName': 'iPhone',
                'osVersion': '18.3.2.22D82',
                'hl': 'en',
                'timeZone': 'UTC',
                'utcOffsetMinutes': 0,
            },
        },
        'videoId': video_id,
        'playbackContext': {
            'contentPlaybackContext': {
                'html5Preference': 'HTML5_PREF_WANTS',
                'signatureTimestamp': 20249,
            },
        },
        'contentCheckOk': True,
        'racyCheckOk': True,
    }
    
    response = requests.post(
        'https://www.youtube.com/youtubei/v1/player',
        params=YT_PARAMS,
        cookies=YT_COOKIES,
        headers=YT_HEADERS,
        json=json_data,
    )
    
    if response.status_code != 200:
        raise Exception(f"YouTube API request failed: {response.status_code}")
    
    data = response.json()
    streaming_data = data.get("streamingData", {})
    adaptive_formats = streaming_data.get("adaptiveFormats", [])
    
    if not adaptive_formats:
        raise Exception("No adaptive formats found in YouTube response")
    
    return extract_streams(adaptive_formats)

def download_thread(link, ss, to, output, request_id):
    try:
        # Calculate duration using new time_to_seconds function
        start_sec = time_to_seconds(ss)
        end_sec = time_to_seconds(to)
        duration = end_sec - start_sec
        
        # Update initial status
        with download_lock:
            download_status[request_id] = {
                'status': 'downloading',
                'progress': 0,
                'filename': output,
                'message': 'Getting stream info from YouTube...'
            }
        
        # Extract video ID
        if "?" in link:
            video_id = link.split("?")[0].split("/")[-1]
        else:
            video_id = link.split("/")[-1]
        
        # Get streams from YouTube
        video_stream, audio_stream = get_youtube_streams(video_id)
        
        if not video_stream or not audio_stream:
            raise Exception("No suitable video or audio stream found")
        
        # Prepare output path
        output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], output)
        
        # Update status
        with download_lock:
            download_status[request_id]['message'] = 'Starting download with FFmpeg...'
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file without asking
            '-ss', ss,
            '-to', to,
            '-i', video_stream['url'],
            '-ss', ss,
            '-to', to,
            '-i', audio_stream['url'],
            '-c', 'copy',
            '-preset', 'ultrafast',
            output_path
        ]
        
        # Run FFmpeg command
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Monitor progress
        total_duration = duration
        time_regex = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
        
        for line in process.stdout:
            match = time_regex.search(line)
            if match:
                hours, minutes, seconds = match.groups()
                current_sec = int(hours)*3600 + int(minutes)*60 + float(seconds)
                progress = min(100, (current_sec / total_duration) * 100)
                
                with download_lock:
                    download_status[request_id] = {
                        'status': 'downloading',
                        'progress': progress,
                        'filename': output,
                        'message': f'Downloading: {progress:.1f}%'
                    }
        
        process.wait()
        
        if process.returncode == 0:
            with download_lock:
                download_status[request_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'filename': output,
                    'message': 'Download completed!'
                }
        else:
            raise Exception(f"FFmpeg failed with exit code {process.returncode}")
            
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        with download_lock:
            download_status[request_id] = {
                'status': 'error',
                'progress': 0,
                'filename': output,
                'message': f'Error: {str(e)}'
            }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    
    # Handle both form and JSON requests
    if request.is_json:
        data = request.get_json()
        link = data.get("link", "").strip()
        ss = data.get("ss", "").strip()
        to = data.get("to", "").strip()
        output = data.get("output", "").strip()
    else:
        link = request.form.get("link", "").strip()
        ss = request.form.get("ss", "").strip()
        to = request.form.get("to", "").strip()
        output = request.form.get("output", "").strip()
    
    # Validate inputs
    errors = []
    if not link.startswith(("https://www.youtube.com/", "https://youtu.be/")):
        errors.append("Invalid YouTube URL")
    if not validate_time(ss):
        errors.append("Invalid start time format (use HH:MM:SS or MM:SS)")
    if not validate_time(to):
        errors.append("Invalid end time format (use HH:MM:SS or MM:SS)")
    if not output or not output.endswith(('.mp4', '.mkv', '.webm')):
        errors.append("Invalid output filename (use .mp4, .mkv or .webm)")
    
    # Calculate duration in seconds
    if not errors:
        try:
            start_sec = time_to_seconds(ss)
            end_sec = time_to_seconds(to)
            duration = end_sec - start_sec
            
            if duration <= 0:
                errors.append("End time must be after start time")
            elif duration > 300:  # 5 minutes
                errors.append("Clip duration cannot exceed 5 minutes")
        except Exception as e:
            errors.append(f"Error processing times: {str(e)}")
    
    if errors:
        if request.is_json:
            return jsonify({"errors": errors}), 400
        else:
            for error in errors:
                flash(error, "error")
            return redirect(url_for("index"))
    
    # Generate unique request ID
    request_id = os.urandom(16).hex()
    safe_output = secure_filename(output)
    
    # Start download in background thread
    thread = threading.Thread(
        target=download_thread,
        args=(link, ss, to, safe_output, request_id)
    )
    thread.start()
    
    if request.is_json:
        return jsonify({
            "request_id": request_id,
            "filename": safe_output
        })
    else:
        return redirect(url_for("download_status_page", request_id=request_id))

@app.route("/stream/<filename>")
def stream_file(filename):
    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], safe_filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)
    
    # Determine MIME type based on file extension
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska'
    }
    mime_type = mime_types.get(ext, 'video/mp4')

    if not range_header:
        # Initial request - return the whole file with streaming headers
        response = Response(
            file_iterator(file_path),
            status=200,
            mimetype=mime_type,
            direct_passthrough=True
        )
        response.headers['Content-Length'] = file_size
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # Parse range header
    start, end = parse_range_header(range_header, file_size)
    content_length = end - start + 1

    # Create response with partial content
    response = Response(
        file_iterator(file_path, start, end),
        status=206,
        mimetype=mime_type,
        direct_passthrough=True
    )
    
    response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response.headers['Content-Length'] = content_length
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

def parse_range_header(range_header, file_size):
    """Parse range header and return start/end bytes"""
    unit, ranges = range_header.split('=')
    if unit != 'bytes' or ',' in ranges:
        raise ValueError('Invalid range header')
    
    start, end = ranges.split('-')
    start = int(start) if start else 0
    end = int(end) if end else file_size - 1
    
    # Ensure end isn't beyond file size
    end = min(end, file_size - 1)
    return start, end

def file_iterator(file_path, start=None, end=None, chunk_size=1024*1024):
    """Generator function to stream file in chunks"""
    with open(file_path, 'rb') as f:
        if start is not None:
            f.seek(start)
        
        remaining = None
        if end is not None:
            remaining = end - start + 1
        
        while True:
            if remaining is not None and remaining <= 0:
                break
                
            bytes_to_read = min(chunk_size, remaining) if remaining is not None else chunk_size
            data = f.read(bytes_to_read)
            
            if not data:
                break
                
            if remaining is not None:
                remaining -= len(data)
                
            yield data
        
@app.route("/status/<request_id>")
def download_status_page(request_id):
    return render_template("status.html", request_id=request_id)

@app.route("/progress/<request_id>")
def download_progress(request_id):
    with download_lock:
        status = download_status.get(request_id, {
            'status': 'unknown',
            'progress': 0,
            'filename': '',
            'message': 'Request not found'
        })
    return status

@app.route("/download/<filename>")
def download_file(filename):
    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], safe_filename)
    
    if not os.path.exists(file_path):
        flash("File not found or has expired", "error")
        return redirect(url_for("index"))
    
    return send_file(file_path, as_attachment=True)

@app.route("/cleanup/<filename>")
def cleanup_file(filename):
    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], safe_filename)
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return "File cleaned up", 200
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9999))
    app.run(debug=True, host='0.0.0.0', port=port)
