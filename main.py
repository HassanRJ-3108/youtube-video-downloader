import streamlit as st
import yt_dlp
import os
from pathlib import Path
import re
import time
import datetime
import base64
import tempfile
import shutil
import subprocess
import urllib.request

# Page configuration
st.set_page_config(
    page_title="YouTube HD Downloader",
    page_icon="🎬",
    layout="centered"
)

# Header
st.title("YouTube HD Downloader")
st.write("Download high-quality videos")

# Initialize session state
if 'download_started' not in st.session_state:
    st.session_state.download_started = False
if 'download_complete' not in st.session_state:
    st.session_state.download_complete = False
if 'download_error' not in st.session_state:
    st.session_state.download_error = None
if 'download_path' not in st.session_state:
    st.session_state.download_path = None
if 'filename' not in st.session_state:
    st.session_state.filename = None
if 'video_info' not in st.session_state:
    st.session_state.video_info = None
if 'download_data' not in st.session_state:
    st.session_state.download_data = None

# Input for YouTube URL
youtube_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

# Clean ANSI color codes from text
def clean_ansi(text):
    if not text:
        return ""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Function to get video info
def get_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Create format options with sizes
            formats = {}
            
            # Add specific resolution options including lower resolutions
            resolutions = [
                {"name": "2160p (4K)", "height": 2160},
                {"name": "1440p (2K)", "height": 1440},
                {"name": "1080p (Full HD)", "height": 1080},
                {"name": "720p (HD)", "height": 720},
                {"name": "480p", "height": 480},
                {"name": "360p", "height": 360},
                {"name": "240p", "height": 240},
                {"name": "144p", "height": 144}
            ]
            
            for res in resolutions:
                # For higher resolutions, we'll use a different approach
                if res["height"] >= 720:
                    format_id = f"bestvideo[height<={res['height']}]+bestaudio"
                else:
                    format_id = f"best[height<={res['height']}]"
                
                size = estimate_size(info, format_id, res['height'])
                
                formats[res["name"]] = {
                    'format_id': format_id,
                    'size': size,
                    'height': res['height']
                }
            
            # Add audio-only option
            formats["Audio Only (MP3)"] = {
                'format_id': 'bestaudio',
                'size': estimate_size(info, 'bestaudio', 0, audio_only=True),
                'height': 'Audio'
            }
            
            return {
                'id': info.get('id', 'unknown'),
                'title': info.get('title', 'Unknown'),
                'channel': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'views': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats
            }
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None

# Estimate file size based on resolution and duration
def estimate_size(info, format_id, height=None, audio_only=False):
    try:
        duration = info.get('duration', 0)
        if not duration:
            return None
        
        # Estimate size based on resolution and duration
        if audio_only:
            # Audio: ~1MB per minute
            return duration * 1024 * 1024 / 60
        elif height is not None:  # Check if height is not None
            # Video: size depends on resolution
            if height >= 2160:
                return duration * 20 * 1024 * 1024 / 60  # ~20MB per minute for 4K
            elif height >= 1440:
                return duration * 15 * 1024 * 1024 / 60  # ~15MB per minute for 2K
            elif height >= 1080:
                return duration * 10 * 1024 * 1024 / 60  # ~10MB per minute for 1080p
            elif height >= 720:
                return duration * 5 * 1024 * 1024 / 60   # ~5MB per minute for 720p
            elif height >= 480:
                return duration * 2.5 * 1024 * 1024 / 60 # ~2.5MB per minute for 480p
            elif height >= 240:
                return duration * 1.2 * 1024 * 1024 / 60 # ~1.2MB per minute for 240p
            else:
                return duration * 0.8 * 1024 * 1024 / 60 # ~0.8MB per minute for 144p
        else:
            # Default estimate: ~5MB per minute
            return duration * 5 * 1024 * 1024 / 60
    except:
        # If estimation fails, return None
        return None

# Format file size for display
def format_size(size_bytes):
    if size_bytes is None:  # Check if size_bytes is None
        return "Unknown size"
    
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

# Function to download video
def download_video(url, format_id, quality):
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Calculate progress
                progress = 0  # Default to 0
                
                # Safely calculate progress
                if 'total_bytes' in d and d['total_bytes'] and d['total_bytes'] > 0:
                    progress = d['downloaded_bytes'] / d['total_bytes']
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] and d['total_bytes_estimate'] > 0:
                    progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                
                # Update progress bar
                progress_bar.progress(min(progress, 1.0))
                
                # Update status text (clean up ANSI codes)
                percent = d.get('_percent_str', '0%')
                percent = clean_ansi(percent).strip()
                
                speed = d.get('_speed_str', '0 B/s')
                speed = clean_ansi(speed).strip()
                
                status_text.text(f"Downloading: {percent} at {speed}")
            
            elif d['status'] == 'finished':
                progress_bar.progress(1.0)
                status_text.text("Processing video... Almost done!")
        
        # Generate a timestamp-based filename to ensure it appears at the top in file explorer
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine if this is a playlist
        is_playlist = False
        if "playlist" in url.lower() or "&list=" in url:
            is_playlist = True
            
        # Prepare filename template with playlist index if needed
        if is_playlist:
            filename_template = os.path.join(temp_dir, f"{current_time}_(1)_%(title)s.%(ext)s")
        else:
            filename_template = os.path.join(temp_dir, f"{current_time}_%(title)s.%(ext)s")
        
        # For audio-only downloads
        if "Audio Only" in quality:
            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': filename_template,
                'progress_hooks': [progress_hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': not is_playlist,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise Exception("Failed to extract video information")
                
                # Handle playlist vs single video differently
                if is_playlist and 'entries' in info:
                    # For playlists, we'll just take the first successful download
                    for entry in info['entries']:
                        if entry:
                            filename = ydl.prepare_filename(entry)
                            break
                else:
                    # For single videos
                    filename = ydl.prepare_filename(info)
                
                # Ensure the extension is correct
                filename = os.path.splitext(filename)[0] + '.mp3'
                
                # Find the downloaded file
                final_path = os.path.join(temp_dir, os.path.basename(filename))
                if not os.path.exists(final_path):
                    # Try to find the file with a similar name
                    for file in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path) and file.endswith('.mp3'):
                            final_path = file_path
                            break
                
                return os.path.basename(final_path), final_path
        
        # For video downloads
        else:
            # For higher resolutions (720p+), we need to use a special approach
            if "+" in format_id:  # This indicates separate video and audio streams
                # We'll use yt-dlp's built-in functionality but with explicit settings
                ydl_opts = {
                    'format': format_id,
                    'outtmpl': filename_template,
                    'progress_hooks': [progress_hook],
                    'merge_output_format': 'mp4',
                    'noplaylist': not is_playlist,
                    # Force FFmpeg to properly merge video and audio
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }],
                    # Add extra FFmpeg arguments to ensure audio is included
                    'postprocessor_args': {
                        'FFmpegVideoConvertor': ['-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental'],
                    },
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info is None:
                        raise Exception("Failed to extract video information")
                    
                    # Handle playlist vs single video differently
                    if is_playlist and 'entries' in info:
                        # For playlists, we'll just take the first successful download
                        for entry in info['entries']:
                            if entry:
                                filename = ydl.prepare_filename(entry)
                                break
                    else:
                        # For single videos
                        filename = ydl.prepare_filename(info)
                    
                    # Ensure the extension is correct
                    if not filename.endswith('.mp4'):
                        filename = os.path.splitext(filename)[0] + '.mp4'
                    
                    # Find the downloaded file
                    final_path = os.path.join(temp_dir, os.path.basename(filename))
                    if not os.path.exists(final_path):
                        # Try to find the file with a similar name
                        for file in os.listdir(temp_dir):
                            file_path = os.path.join(temp_dir, file)
                            if os.path.isfile(file_path) and file.endswith('.mp4'):
                                final_path = file_path
                                break
                    
                    # Verify that the file has audio
                    try:
                        # Use FFprobe to check if the file has an audio stream
                        cmd = [
                            'ffprobe',
                            '-v', 'error',
                            '-select_streams', 'a:0',
                            '-show_entries', 'stream=codec_type',
                            '-of', 'default=noprint_wrappers=1:nokey=1',
                            final_path
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if 'audio' not in result.stdout:
                            # No audio stream found, try a different approach
                            raise Exception("No audio stream found in the downloaded file")
                    except:
                        # If FFprobe check fails or no audio found, try a different approach
                        # We'll download again with a different format string
                        status_text.text("Retrying with a different method...")
                        
                        # Try a more compatible format string
                        retry_ydl_opts = {
                            'format': 'best',  # Use the best combined format
                            'outtmpl': filename_template,
                            'progress_hooks': [progress_hook],
                            'merge_output_format': 'mp4',
                            'noplaylist': not is_playlist,
                        }
                        
                        with yt_dlp.YoutubeDL(retry_ydl_opts) as retry_ydl:
                            info = retry_ydl.extract_info(url, download=True)
                            if info is None:
                                raise Exception("Failed to extract video information")
                            
                            # Handle playlist vs single video differently
                            if is_playlist and 'entries' in info:
                                # For playlists, we'll just take the first successful download
                                for entry in info['entries']:
                                    if entry:
                                        filename = retry_ydl.prepare_filename(entry)
                                        break
                            else:
                                # For single videos
                                filename = retry_ydl.prepare_filename(info)
                            
                            # Ensure the extension is correct
                            if not filename.endswith('.mp4'):
                                filename = os.path.splitext(filename)[0] + '.mp4'
                            
                            # Find the downloaded file
                            final_path = os.path.join(temp_dir, os.path.basename(filename))
                            if not os.path.exists(final_path):
                                # Try to find the file with a similar name
                                for file in os.listdir(temp_dir):
                                    file_path = os.path.join(temp_dir, file)
                                    if os.path.isfile(file_path) and file.endswith('.mp4'):
                                        final_path = file_path
                                        break
                    
                    return os.path.basename(final_path), final_path
            
            # For lower resolutions, we can use the standard approach
            else:
                ydl_opts = {
                    'format': format_id,
                    'outtmpl': filename_template,
                    'progress_hooks': [progress_hook],
                    'merge_output_format': 'mp4',
                    'noplaylist': not is_playlist,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info is None:
                        raise Exception("Failed to extract video information")
                    
                    # Handle playlist vs single video differently
                    if is_playlist and 'entries' in info:
                        # For playlists, we'll just take the first successful download
                        for entry in info['entries']:
                            if entry:
                                filename = ydl.prepare_filename(entry)
                                break
                    else:
                        # For single videos
                        filename = ydl.prepare_filename(info)
                    
                    # Ensure the extension is correct
                    if not filename.endswith('.mp4'):
                        filename = os.path.splitext(filename)[0] + '.mp4'
                    
                    # Find the downloaded file
                    final_path = os.path.join(temp_dir, os.path.basename(filename))
                    if not os.path.exists(final_path):
                        # Try to find the file with a similar name
                        for file in os.listdir(temp_dir):
                            file_path = os.path.join(temp_dir, file)
                            if os.path.isfile(file_path) and file.endswith('.mp4'):
                                final_path = file_path
                                break
                    
                    return os.path.basename(final_path), final_path
    
    except Exception as e:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        raise Exception(f"Download failed: {str(e)}")

# Always show the "Fetch Video Info" button
if st.button("Fetch Video Info"):
    if youtube_url:
        with st.spinner("Fetching video information..."):
            try:
                start_time = time.time()
                st.session_state.video_info = get_video_info(youtube_url)
                fetch_time = time.time() - start_time
                
                if st.session_state.video_info:
                    st.success(f"Video information fetched in {fetch_time:.2f} seconds")
                else:
                    st.error("Failed to fetch video information. Please check the URL and try again.")
            except Exception as e:
                st.error(f"Error fetching video info: {str(e)}")
    else:
        st.error("Please enter a YouTube URL first")

# Display video information if available
if st.session_state.video_info:
    video_info = st.session_state.video_info
    
    # Display video information
    st.subheader(f"Video: {video_info['title']}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if video_info['thumbnail']:
            st.image(video_info['thumbnail'], width=180)
        else:
            st.write("No thumbnail available")
    
    with col2:
        st.write(f"**Channel:** {video_info['channel']}")
        
        # Format duration
        minutes = video_info['duration'] // 60
        seconds = video_info['duration'] % 60
        st.write(f"**Length:** {minutes}m {seconds}s")
        st.write(f"**Views:** {video_info['views']:,}")
    
    # Download options
    st.subheader("Download Options")
    
    # Quality selection
    quality_options = list(video_info['formats'].keys())
    selected_quality = st.selectbox("Select Quality:", quality_options)
    
    # Add warning for high-resolution videos
    selected_format = video_info['formats'][selected_quality]
    if selected_format['height'] in [1440, 2160]:
        st.warning(f"⚠️ **Note:** {selected_quality} videos may not play smoothly on some devices due to high resolution. VLC or a powerful media player is recommended.")
    
    # Show file size
    size_str = format_size(selected_format['size'])
    st.info(f"File size: **{size_str}**")
    
    # Check if URL is a playlist
    is_playlist = "playlist" in youtube_url.lower() or "&list=" in youtube_url
    if is_playlist:
        st.info("📋 This appears to be a playlist. The first video will be downloaded.")
    
    # Download button - always visible
    if st.button("Download Now", type="primary"):
        st.session_state.download_started = True
        st.session_state.download_complete = False
        st.session_state.download_error = None
        st.session_state.download_data = None
        
        try:
            # Start download with spinner
            with st.spinner("Downloading video..."):
                format_id = video_info['formats'][selected_quality]['format_id']
                filename, filepath = download_video(youtube_url, format_id, selected_quality)
            
            # Update session state
            st.session_state.download_complete = True
            st.session_state.filename = filename
            st.session_state.download_path = filepath
            
            # Read the file data for download link
            with open(filepath, 'rb') as f:
                st.session_state.download_data = f.read()
            
            # Clean up the file
            try:
                os.remove(filepath)
                os.path.dirname(filepath) and shutil.rmtree(os.path.dirname(filepath), ignore_errors=True)
            except:
                pass
            
            # Force refresh
            st.rerun()
        
        except Exception as e:
            st.session_state.download_error = str(e)
    
    # Show download status
    if st.session_state.download_started:
        if st.session_state.download_error:
            st.error(f"Download failed: {st.session_state.download_error}")
            
            # Provide more specific error guidance
            error_msg = str(st.session_state.download_error).lower()
            if "http error 403" in error_msg:
                st.error("This video may be restricted or not available for download.")
            elif "signature" in error_msg:
                st.error("YouTube may have changed their system. Try updating yt-dlp.")
            elif "network" in error_msg or "connection" in error_msg:
                st.error("Network error. Check your internet connection and try again.")
            elif "ffmpeg not found" in error_msg or "ffprobe" in error_msg:
                st.error("FFmpeg is required for high-quality downloads. Please contact the administrator to install FFmpeg.")
        
        elif st.session_state.download_complete and st.session_state.download_data:
            st.success("✅ Download Complete!")
            
            # Create download link
            file_ext = "mp3" if "Audio Only" in selected_quality else "mp4"
            safe_title = re.sub(r'[^\w\-_\. ]', '_', video_info['title'])
            
            # Add (1) for playlist items
            if is_playlist:
                download_filename = f"{safe_title} (1).{file_ext}"
            else:
                download_filename = f"{safe_title}.{file_ext}"
            
            # Create a download button
            st.download_button(
                label="⬇️ Download File",
                data=st.session_state.download_data,
                file_name=download_filename,
                mime="video/mp4" if file_ext == "mp4" else "audio/mp3"
            )
            
            # For high-resolution videos, add a playback tip
            if selected_format['height'] in [1440, 2160]:
                st.warning("For smooth playback of high-resolution videos, use VLC Media Player or another powerful video player.")

# Instructions
with st.expander("How to use"):
    st.write("""
    ### Instructions
    
    1. Enter a YouTube URL and click "Fetch Video Info"
    2. Select your preferred quality (up to 4K if available)
    3. Click "Download Now"
    4. Wait for the download to complete
    5. Click the "Download File" button to save the video to your device
    
    ### Quality Selection
    
    - **4K (2160p)** and **2K (1440p)** videos are very high quality but may not play smoothly on all devices
    - **1080p (Full HD)** is recommended for most users - good quality and compatible with most devices
    - **HD (720p)** is a good balance of quality and file size
    - **480p** and **360p** are lower quality but smaller file size
    - **240p** and **144p** are very low quality but smallest file size
    - **Audio Only (MP3)** will extract just the audio track
    
    ### Troubleshooting
    
    - If downloads fail, try a different quality setting
    - Make sure you have a stable internet connection
    - Some videos may be restricted and cannot be downloaded
    - If you get an error, try again or try a different video
    - For high-resolution videos (2K/4K), use VLC Media Player for best playback
    """)

# Footer
st.markdown("---")
st.caption("Made with Streamlit and yt-dlp • Click the Download File button to save your video")
