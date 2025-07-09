from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import yt_dlp
import re
import os
import logging
import threading
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create downloads folder
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Validate time format (HH:MM:SS or MM:SS)
def validate_time(time_str):
    return re.match(r'^([0-9]{1,2}:)?[0-5][0-9]:[0-5][0-9]$', time_str)

# Track download status
download_status = {}
download_lock = threading.Lock()

def download_thread(link, ss, to, output, request_id):
    try:
        # Calculate duration
        start_sec = sum(x * int(t) for x, t in zip([3600, 60, 1], ss.split(":")[::-1]))
        end_sec = sum(x * int(t) for x, t in zip([3600, 60, 1], to.split(":")[::-1]))
        duration = end_sec - start_sec
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], output),
            'download_ranges': [{'start_time': ss, 'end_time': to}],
            'force_keyframes_at_cuts': True,
            'progress_hooks': [lambda d: progress_hook(d, request_id)],
            'socket_timeout': 30,
            'noprogress': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
        }
        
        # Update status
        with download_lock:
            download_status[request_id] = {
                'status': 'downloading',
                'progress': 0,
                'filename': output,
                'message': 'Starting download...'
            }
        
        # Download the clip
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        
        # Final status update
        with download_lock:
            download_status[request_id] = {
                'status': 'completed',
                'progress': 100,
                'filename': output,
                'message': 'Download completed!'
            }
            
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        with download_lock:
            download_status[request_id] = {
                'status': 'error',
                'progress': 0,
                'filename': output,
                'message': f'Error: {str(e)}'
            }

def progress_hook(d, request_id):
    if d['status'] == 'downloading':
        progress = 0
        if '_percent_str' in d:
            try:
                progress = float(d['_percent_str'].strip('%'))
            except:
                pass
        
        with download_lock:
            if request_id in download_status:
                download_status[request_id]['progress'] = progress
                download_status[request_id]['message'] = d.get('_message', 'Downloading...')
                
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
            start_sec = sum(x * int(t) for x, t in zip([3600, 60, 1], ss.split(":")[::-1]))
            end_sec = sum(x * int(t) for x, t in zip([3600, 60, 1], to.split(":")[::-1]))
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
        args=(link, ss, to, safe_output, request_id))
    thread.start()
    
    if request.is_json:
        return jsonify({
            "request_id": request_id,
            "filename": safe_output
        })
    else:
        return redirect(url_for("download_status_page", request_id=request_id))

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
