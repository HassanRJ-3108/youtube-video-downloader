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
if 'ffmpeg_available' not in st.session_state:
    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        st.session_state.ffmpeg_available = True
    except (subprocess.SubprocessError, FileNotFoundError):
        st.session_state.ffmpeg_available = False

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
            
            # Get all available formats with both video and audio
            available_formats = []
            for fmt in info.get('formats', []):
                # Only include formats that have both video and audio
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    height = fmt.get('height', 0)
                    if height > 0:  # Only include formats with valid height
                        available_formats.append({
                            'format_id': fmt['format_id'],
                            'height': height,
                            'ext': fmt.get('ext', 'mp4'),
                            'filesize': fmt.get('filesize', 0)
                        })
            
            # Sort by height (resolution)
            available_formats.sort(key=lambda x: x['height'], reverse=True)
            
            # Group by common resolutions
            resolution_groups = {
                "2160p (4K)": 2160,
                "1440p (2K)": 1440,
                "1080p (Full HD)": 1080,
                "720p (HD)": 720,
                "480p": 480,
                "360p": 360,
                "240p": 240,
                "144p": 144
            }
            
            # Find the best format for each resolution group
            for name, target_height in resolution_groups.items():
                best_format = None
                
                # Find the highest quality format that doesn't exceed the target height
                for fmt in available_formats:
                    if fmt['height'] <= target_height:
                        if best_format is None or fmt['height'] > best_format['height']:
                            best_format = fmt
                
                if best_format:
                    # Calculate estimated size
                    size = best_format.get('filesize', 0)
                    if not size:
                        size = estimate_size(info, best_format['format_id'], best_format['height'])
                    
                    formats[name] = {
                        'format_id': best_format['format_id'],
                        'size': size,
                        'height': best_format['height'],
                        'ext': best_format['ext']
                    }
            
            # Add audio-only option
            formats["Audio Only (MP3)"] = {
                'format_id': 'bestaudio',
                'size': estimate_size(info, 'bestaudio', 0, audio_only=True),
                'height': 'Audio',
                'ext': 'mp3'
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
def download_video(url, format_id, quality, selected_format):
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
                'noplaylist': not is_playlist,
                # Try to extract audio without FFmpeg if possible
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                # Important: Don't abort if FFmpeg is not available
                'ignoreerrors': True,
                'abort_on_error': False
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
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
                    
                    # Find the downloaded file
                    # Try with mp3 extension first (if FFmpeg worked)
                    mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                    mp3_path = os.path.join(temp_dir, os.path.basename(mp3_filename))
                    
                    if os.path.exists(mp3_path):
                        return os.path.basename(mp3_path), mp3_path
                    
                    # If mp3 not found, look for any audio file
                    for file in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path):
                            return os.path.basename(file_path), file_path
                    
                    raise Exception("Downloaded file not found")
                    
                except Exception as e:
                    # If the first attempt fails, try with a simpler approach
                    status_text.text("Retrying with a different method...")
                    
                    # Try a simpler approach without FFmpeg
                    simple_ydl_opts = {
                        'format': 'bestaudio',
                        'outtmpl': filename_template,
                        'progress_hooks': [progress_hook],
                        'noplaylist': not is_playlist,
                        # No postprocessors
                    }
                    
                    with yt_dlp.YoutubeDL(simple_ydl_opts) as simple_ydl:
                        info = simple_ydl.extract_info(url, download=True)
                        if info is None:
                            raise Exception("Failed to extract video information")
                        
                        # Handle playlist vs single video differently
                        if is_playlist and 'entries' in info:
                            # For playlists, we'll just take the first successful download
                            for entry in info['entries']:
                                if entry:
                                    filename = simple_ydl.prepare_filename(entry)
                                    break
                        else:
                            # For single videos
                            filename = simple_ydl.prepare_filename(info)
                        
                        # Find the downloaded file
                        final_path = os.path.join(temp_dir, os.path.basename(filename))
                        if not os.path.exists(final_path):
                            # Try to find the file with a similar name
                            for file in os.listdir(temp_dir):
                                file_path = os.path.join(temp_dir, file)
                                if os.path.isfile(file_path):
                                    final_path = file_path
                                    break
                        
                        return os.path.basename(final_path), final_path
        
        # For video downloads
        else:
            # Use the specific format ID that we know has both video and audio
            ydl_opts = {
                'format': format_id,
                'outtmpl': filename_template,
                'progress_hooks': [progress_hook],
                'noplaylist': not is_playlist,
                # Important: Don't abort if FFmpeg is not available
                'ignoreerrors': True,
                'abort_on_error': False
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
                
                # Find the downloaded file
                final_path = os.path.join(temp_dir, os.path.basename(filename))
                if not os.path.exists(final_path):
                    # Try to find the file with a similar name
                    for file in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path):
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

# Show FFmpeg status
if not st.session_state.ffmpeg_available:
    st.info("ℹ️ FFmpeg is not installed on the server. High-resolution videos (720p+) will be downloaded as separate video and audio files that you can play together.")

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
    
    # Get the selected format
    selected_format = video_info['formats'][selected_quality]
    
    # Add warning for high-resolution videos
    if selected_format['height'] in [1440, 2160]:
        st.warning(f"⚠️ **Note:** {selected_quality} videos may not play smoothly on some devices due to high resolution. VLC or a powerful media player is recommended.")
    
    # Show file size
    size_str = format_size(selected_format['size'])
    st.info(f"File size: **{size_str}**")
    
    # Special note for formats that need FFmpeg but it's not available
    if selected_format.get('needs_ffmpeg', False):
        st.info("📝 This quality will download as separate video and audio files in a ZIP archive. Instructions for playing them together will be included.")
    
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
                filename, filepath = download_video(youtube_url, format_id, selected_quality, selected_format)
            
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
        
        elif st.session_state.download_complete and st.session_state.download_data:
            st.success("✅ Download Complete!")
            
            # Determine file extension and mime type
            filename = st.session_state.filename
            file_ext = os.path.splitext(filename)[1][1:] if '.' in filename else 'mp4'
            mime_type = f"video/{file_ext}" if file_ext != "mp3" else "audio/mp3"
            
            # Create a safe filename
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
                mime=mime_type
            )
            
            # Special instructions for ZIP files (separate video/audio)
            if file_ext == "zip":
                st.info("""
                **Important: This download contains separate video and audio files**
                
                1. Extract the ZIP file after downloading
                2. Read the included README.txt file for instructions
                3. You can play both files together using VLC Media Player
                """)
            
            # For high-resolution videos, add a playback tip
            elif selected_format['height'] in [1440, 2160]:
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
    
    ### High-Resolution Downloads Without FFmpeg
    
    When downloading high-resolution videos (720p and above) without FFmpeg:
    - You'll receive a ZIP file containing separate video and audio files
    - Use VLC Media Player to play both files together
    - Instructions are included in the ZIP file
    
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
