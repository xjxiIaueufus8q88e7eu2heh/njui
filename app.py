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
import shutil

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['STREAM_CHUNK_SIZE'] = 8 * 1024 * 1024
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

def cleanup_old_files():
    """Delete files older than 5 minutes from download folder"""
    now = time.time()
    folder = app.config['DOWNLOAD_FOLDER']
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            mtime = os.path.getmtime(file_path)
            if now - mtime > 300:  # 5 minutes in seconds
                try:
                    os.remove(file_path)
                    logging.info(f"Cleaned up old file: {filename}")
                except Exception as e:
                    logging.error(f"Error cleaning up file {filename}: {str(e)}")

# Track download status
download_status = {}
download_lock = threading.Lock()

# YouTube cookies and headers
YT_COOKIES = {
    'ST-1jl44ru': 'csn=GSlEKOZq6K08Ueal&itct=CM0CEPxaIhMIhZqfsc63jgMVvvlMAh2IqxmJMgpnLWhpZ2gtcmVjWg9GRXdoYXRfdG9fd2F0Y2iaAQYQjh4YngE%3D',
    'SIDCC': 'AKEyXzXyj_SzsukeBKYKt6KRQrRPNlBA9caUki-7UOr0fgMHmDGS6Ts0gEngxbIpBpmgU2eP',
    '__Secure-1PSIDCC': 'AKEyXzVHK8GpGvy3h80vk8zdui0DNgONDcS3CgvTomQx3sHd0b2gvzD2PcJEmImh7Cwi91Gn2Q',
    '__Secure-3PSIDCC': 'AKEyXzXIPLwYsOShHjMFug5j1Ge4VTO0V5iO55-X7ZSaLmBw4ATPK2Rc4YECQeqtJi5rW5Z27Q',
    'LOGIN_INFO': 'AFmmF2swRQIhAKYGKe7Sz7aX6eOLqJIuQQhsWLxzGsWHukXH34cavXXAAiBUF2yEanpm3sAvSLWV8FmaQ2CTo6ooZM5rtzsU56RqbQ:QUQ3MjNmenlxclAwVHgyWUtONVloRnp5ZzRFWXZpZjlRTF9teEdsVVpVc1k0ZDgyMFM3elQ2cmdUUFB4bUJBSXJkbXRuT0o5WFpuUFF3aE9sRkhrUTJBQ0dDYVFCbThQczJsSlhPLWMwZDBfSmpmRllEN3VJcjJMd3RWcHRrTWh1d2FiV3JrVDc1Q18xQVlFRGdTSkhFOU1ZN2N0UWdwRmpB',
    'PREF': 'f6=40000000&tz=Asia.Calcutta',
    'VISITOR_INFO1_LIVE': 'TcvRURFXwZY',
    'VISITOR_PRIVACY_METADATA': 'CgJJThIEGgAgGA%3D%3D',
    'APISID': '85qI8fAsn7Q7PDxs/As53UNrIdO7bFBb7_',
    'HSID': 'A97_ROvAFpYFtsVdh',
    'SAPISID': 'ODeTM781gRL7UdID/A0F_qMb_UUlhxnLLG',
    'SID': 'g.a000ygi68HtoGmv9lLjtAslbXj7bKXhKGVjiJJHuvHg4zbyuRZHUQ_gZiiKCTN4K6YodkIGcHAACgYKAWgSARASFQHGX2MioKs3RgKaqWrj6cXihhkcmhoVAUF8yKobO02jpijtoTnobwnbaAql0076',
    'SSID': 'AZOBIRYi4YggP0ums',
    '__Secure-1PAPISID': 'ODeTM781gRL7UdID/A0F_qMb_UUlhxnLLG',
    '__Secure-1PSID': 'g.a000ygi68HtoGmv9lLjtAslbXj7bKXhKGVjiJJHuvHg4zbyuRZHUSmMl70EYHUbMQ1TH3_pqnQACgYKASUSARASFQHGX2MiEBRH99728DA_T8vMzP8AQBoVAUF8yKpMSd_bPkE54UQnkGcDJmFd0076',
    '__Secure-1PSIDTS': 'sidts-CjIB5H03P4WGCa1oFBq6mL_67uwjsWfDwqJ-c7wY5SvKKdGMKUdxTmrg8o-Y7rRJNHUYJBAA',
    '__Secure-3PAPISID': 'ODeTM781gRL7UdID/A0F_qMb_UUlhxnLLG',
    '__Secure-3PSID': 'g.a000ygi68HtoGmv9lLjtAslbXj7bKXhKGVjiJJHuvHg4zbyuRZHU3qBVxpjNt2GYA4snYiifhwACgYKAQYSARASFQHGX2Mig48oKFGXpAoyKPkgocbPfBoVAUF8yKoXblmrpX5-ZQvvR3xMJO_e0076',
    '__Secure-3PSIDTS': 'sidts-CjIB5H03P4WGCa1oFBq6mL_67uwjsWfDwqJ-c7wY5SvKKdGMKUdxTmrg8o-Y7rRJNHUYJBAA',
    '__Secure-ROLLOUT_TOKEN': 'CPf809iXw5bMzQEQh_7Fms63jgMYsYjdqc63jgM%3D',
    'GPS': '1',
    'YSC': '8iWzeSTOyHg'
}

YT_HEADERS = {
    'Accept': '*/*',
    'X-Youtube-Client-Version': '20.28.2',
    'Authorization': 'Bearer ya29.a0AS3H6NzStqQkWG5BULD3rbeSdnHx1-GOw1IVNxfraK9YjYNKoirHCgy5dWDMuVerGXHA2LWpGK0GkqFsJlszo6Ex9m9rVwAVCBINFP8qv5cFQKXYGqRkFe5fZuN8xQz3iJVrp294zcsb-hdmp_pNr5n5O67dkOMfuVN0a-timfw6eSs5XP-AOjLVa3jHiRrUDlQTXzChyaWQMBQg0s725PJ2DWo8ijHlJ999kF0n-6Qaefnq5x4V9zOmhIkmDmdNl4Emu0P02rrMdnsQy6xG4NEVOupLWVfmXqK0GQLY9DOpTbSRhEkOH9ntR5Men6CSU3a1pomksZJzCAfdaCgYKAYESARASFQHGX2MiI_5JHAJplQSJIQj04HoGTw0343',
    'X-Youtube-Client-Name': '5',
    'Accept-Language': 'en-IN,en;q=0.9',
    'Cache-Control': 'no-cache',
    'User-Agent': 'com.google.ios.youtube/20.28.2 (iPad11,1; U; CPU iPadOS 18_5 like Mac OS X; en_IN)',
    'X-GOOG-API-FORMAT-VERSION': '2',
    'X-Goog-Visitor-Id': 'CgtBUkpBNThZdkVUOCiszenDBjIKCgJJThIEGgAgPToMCAEg_LOUnsTVmb1oWMKdxsH92fa5ygE%3D',
    'Connection': 'keep-alive',
}

YT_PARAMS = {'prettyPrint': 'false'}

def extract_video_id(url):
    # Patterns to match different YouTube URL formats
    patterns = [
        r"youtube\.com/watch\?v=([^&]+)",         # Standard URL
        r"youtu\.be/([^?]+)",                     # Short URL
        r"youtube\.com/embed/([^/?]+)",           # Embed URL
        r"youtube\.com/v/([^/?]+)",               # Legacy URL
        r"youtube\.com/live/([^/?]+)",            # Live stream URL
        r"youtube\.com/shorts/([^/?]+)",          # Shorts URL
        r"m\.youtube\.com/watch\?v=([^&]+)"       # Mobile URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matched, try to extract from the last part of the URL
    return url.split("/")[-1].split("?")[0]

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
                    'clientVersion': '20.28.2',
                    'deviceMake': 'Apple',
                    'deviceModel': 'iPad',
                    'userAgent': 'com.google.ios.youtube/20.28.2 (iPad11,1; U; CPU iPadOS 18_5 like Mac OS X; en_IN)',
                    'osName': 'iPad',
                    'osVersion': '18_5',
                    'hl': 'en',
                    'timeZone': 'Asia/Calcutta',
                    'utcOffsetMinutes': 330,
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
       # cookies=YT_COOKIES,
        headers=YT_HEADERS,
        json=json_data,
    )
    
    if response.status_code != 200:
        raise Exception(f"YouTube API request failed: {response.status_code}")
    
    data = response.json()
    logging.error(json.dumps(json.loads(response.text)["responseContext"],indent=4))
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
        video_id = extract_video_id(link)
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
    if not re.search(r"youtube\.com|youtu\.be", link):
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

def cleanup_scheduler():
    """Run cleanup every minute"""
    while True:
        cleanup_old_files()
        time.sleep(60)  # Run every minute

if __name__ == "__main__":
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
    cleanup_thread.start()
    
    port = int(os.environ.get("PORT", 9999))
    app.run(debug=True, host='0.0.0.0', port=port)
