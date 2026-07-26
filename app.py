from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import threading
import uuid
import shutil
import re

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
download_progress = {}

class VideoDownloader:
    def download_video(self, url, format_id=None, download_id=None):
    if download_id is None:
        download_id = str(uuid.uuid4())
    
    download_progress[download_id] = {
        'status': 'starting', 'progress': 0, 'speed': '', 'eta': '', 'filename': '', 'error': None
    }
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            try:
                percent = float(d['_percent_str'].replace('%', '').strip())
                download_progress[download_id].update({
                    'status': 'downloading', 'progress': percent,
                    'speed': d.get('_speed_str', 'N/A'), 'eta': d.get('_eta_str', 'N/A')
                })
            except:
                pass
        elif d['status'] == 'finished':
            download_progress[download_id].update({'status': 'processing', 'progress': 100})
    
    try:
        output_path = os.path.join(DOWNLOAD_FOLDER, download_id)
        os.makedirs(output_path, exist_ok=True)
        
        ydl_opts = {
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
        
        if format_id:
            ydl_opts['format'] = format_id
        else:
            ydl_opts['format'] = 'best[ext=mp4]/best'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            actual_file = None
            for f in os.listdir(output_path):
                if f.endswith(('.mp4', '.mkv', '.webm', '.mp3', '.m4a')):
                    actual_file = os.path.join(output_path, f)
                    break
            
            download_progress[download_id].update({
                'status': 'completed', 'progress': 100, 'filename': actual_file
            })
            
            return {
                'success': True,
                'download_id': download_id,
                'filename': os.path.basename(actual_file) if actual_file else 'video.mp4',
                'title': info.get('title', 'Video')
            }
            
    except Exception as e:
        download_progress[download_id].update({'status': 'error', 'error': str(e)})
        return {'success': False, 'error': str(e)}

    def detect_platform(self, url):
        platforms = {
            r'youtube\.com|youtu\.be': 'YouTube',
            r'instagram\.com': 'Instagram',
            r'tiktok\.com': 'TikTok',
            r'facebook\.com|fb\.com': 'Facebook',
            r'twitter\.com|x\.com': 'Twitter/X',
            r'vimeo\.com': 'Vimeo',
        }
        for pattern, name in platforms.items():
            if re.search(pattern, url): return name
        return 'Other'

    def download_video(self, url, format_id=None, download_id=None):
        if download_id is None: download_id = str(uuid.uuid4())
        download_progress[download_id] = {'status': 'starting', 'progress': 0, 'speed': '', 'eta': '', 'filename': '', 'error': None}
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent = float(d['_percent_str'].replace('%', '').strip())
                    download_progress[download_id].update({'status': 'downloading', 'progress': percent, 'speed': d.get('_speed_str', 'N/A'), 'eta': d.get('_eta_str', 'N/A')})
                except: pass
            elif d['status'] == 'finished':
                download_progress[download_id].update({'status': 'processing', 'progress': 100})
        
        try:
            output_path = os.path.join(DOWNLOAD_FOLDER, download_id)
            os.makedirs(output_path, exist_ok=True)
            ydl_opts = {'outtmpl': f'{output_path}/%(title)s.%(ext)s', 'progress_hooks': [progress_hook], 'quiet': True, 'no_warnings': True, 'merge_output_format': 'mp4'}
            if format_id: ydl_opts['format'] = format_id
            else: ydl_opts['format'] = 'best[ext=mp4]/best'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                actual_file = None
                for f in os.listdir(output_path):
                    if f.endswith(('.mp4', '.mkv', '.webm')): actual_file = os.path.join(output_path, f); break
                download_progress[download_id].update({'status': 'completed', 'progress': 100, 'filename': actual_file})
                return {'success': True, 'download_id': download_id, 'filename': os.path.basename(actual_file) if actual_file else 'video.mp4', 'title': info.get('title', 'Video')}
        except Exception as e:
            download_progress[download_id].update({'status': 'error', 'error': str(e)})
            return {'success': False, 'error': str(e)}

downloader = VideoDownloader()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url', '')
    if not url: return jsonify({'success': False, 'error': 'URL required'})
    return jsonify(downloader.get_video_info(url))

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url', '')
    if not url: return jsonify({'success': False, 'error': 'URL required'})
    format_id = data.get('format_id', None)
    download_id = str(uuid.uuid4())
    thread = threading.Thread(target=downloader.download_video, args=(url, format_id, download_id))
    thread.daemon = True
    thread.start()
    return jsonify({'success': True, 'download_id': download_id})

@app.route('/api/progress/<download_id>')
def get_progress(download_id):
    return jsonify(download_progress.get(download_id, {'status': 'not_found', 'progress': 0}))

@app.route('/api/download-file/<download_id>')
def download_file(download_id):
    progress = download_progress.get(download_id, {})
    if progress.get('status') != 'completed': return jsonify({'success': False, 'error': 'Download not complete'})
    filepath = progress.get('filename')
    if not filepath or not os.path.exists(filepath): return jsonify({'success': False, 'error': 'File not found'})
    return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))

@app.route('/api/cleanup/<download_id>', methods=['DELETE'])
def cleanup(download_id):
    if download_id in download_progress:
        filepath = download_progress[download_id].get('filename')
        if filepath and os.path.exists(filepath): os.remove(filepath)
        dirpath = os.path.join(DOWNLOAD_FOLDER, download_id)
        if os.path.exists(dirpath): shutil.rmtree(dirpath)
        del download_progress[download_id]
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
