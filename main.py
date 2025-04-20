import streamlit as st
import yt_dlp
import os
import tempfile
import time
import re
import base64
import shutil
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="YouTube HD Downloader",
    page_icon="🎬",
    layout="centered"
)

# Header
st.title("YouTube HD Downloader")
st.write("Download videos in any quality (144p to 4K)")

# Initialize session state
if 'downloads' not in st.session_state:
    st.session_state.downloads = {}

# Input for YouTube URL
youtube_url = st.text_input("Enter YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

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
            
            # Get video details
            video_details = {
                'id': info.get('id', 'unknown'),
                'title': info.get('title', 'Unknown'),
                'channel': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'views': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail', ''),
            }
            
            # Create format options
            formats = {}
            
            # Add all resolution options
            resolutions = [
                {"name": "4K (2160p)", "height": 2160},
                {"name": "2K (1440p)", "height": 1440},
                {"name": "1080p (Full HD)", "height": 1080},
                {"name": "720p (HD)", "height": 720},
                {"name": "480p", "height": 480},
                {"name": "360p", "height": 360},
                {"name": "240p", "height": 240},
                {"name": "144p", "height": 144}
            ]
            
            for res in resolutions:
                # Format string for this resolution
                format_id = f"bestvideo[height<={res['height']}]+bestaudio/best[height<={res['height']}]"
                
                # Check if this resolution is available
                available = False
                for f in info.get('formats', []):
                    if f.get('height') == res['height'] or (f.get('height') and f.get('height') < res['height'] and not any(f.get('height') == r['height'] for r in resolutions if r['height'] < res['height'])):
                        available = True
                        break
                
                if available:
                    formats[res["name"]] = {
                        'format_id': format_id,
                        'height': res['height'],
                        'direct_url': None  # Will be filled if direct download is available
                    }
            
            # Check for direct download URLs (formats with both video and audio)
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url'):
                    height = f.get('height', 0)
                    for res in resolutions:
                        if height == res['height']:
                            if res['name'] in formats:
                                formats[res['name']]['direct_url'] = f.get('url')
                                formats[res['name']]['filesize'] = f.get('filesize', 0)
                                formats[res['name']]['ext'] = f.get('ext', 'mp4')
            
            # Add audio-only option
            audio_formats = [f for f in info.get('formats', []) if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
            if audio_formats:
                # Sort by quality
                audio_formats.sort(key=lambda x: x.get('filesize', 0) or 0, reverse=True)
                best_audio = audio_formats[0]
                
                formats["Audio Only (MP3)"] = {
                    'format_id': 'bestaudio/best',
                    'height': 'Audio',
                    'direct_url': best_audio.get('url'),
                    'filesize': best_audio.get('filesize', 0),
                    'ext': 'mp3'
                }
            
            return video_details, formats
    
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None, None

# Format file size for display
def format_size(size_bytes):
    if size_bytes is None or size_bytes == 0:
        return "Unknown size"
    
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

# Format duration for display
def format_duration(seconds):
    if not seconds:
        return "Unknown duration"
    
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    else:
        return f"{minutes}m {seconds}s"

# Function to download video
def download_video(url, format_id, video_id, quality):
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Progress indicators
        progress_placeholder = st.empty()
        progress_bar = progress_placeholder.progress(0)
        status_text = st.empty()
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Calculate progress
                progress = 0
                if 'total_bytes' in d and d['total_bytes'] > 0:
                    progress = d['downloaded_bytes'] / d['total_bytes']
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                    progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                
                # Update progress bar
                progress_bar.progress(min(progress, 1.0))
                
                # Update status text
                percent = d.get('_percent_str', '0%').strip()
                speed = d.get('_speed_str', '0 B/s').strip()
                status_text.text(f"Downloading {quality}: {percent} at {speed}")
            
            elif d['status'] == 'finished':
                progress_bar.progress(1.0)
                status_text.text(f"Processing {quality} video... Almost done!")
        
        # Download settings
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': False,
            'no_warnings': False,
            'noplaylist': True,
        }
        
        # Add audio-only postprocessor if needed
        if "bestaudio" in format_id and "bestvideo" not in format_id:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            # For video, ensure we get mp4 output
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("Failed to extract video information")
                
            filename = ydl.prepare_filename(info)
            
            # Ensure the extension is correct
            if "bestaudio" in format_id and "bestvideo" not in format_id:
                filename = os.path.splitext(filename)[0] + '.mp3'
            else:
                if not filename.endswith('.mp4'):
                    filename = os.path.splitext(filename)[0] + '.mp4'
            
            # Find the downloaded file
            final_path = os.path.join(temp_dir, os.path.basename(filename))
            if not os.path.exists(final_path):
                # Try to find the file with a similar name
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        final_path = file_path
                        break
            
            # Read the file data
            with open(final_path, 'rb') as f:
                file_data = f.read()
            
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            # Clear progress indicators
            progress_placeholder.empty()
            status_text.empty()
            
            return os.path.basename(final_path), file_data
    
    except Exception as e:
        # Clean up
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        raise Exception(f"Download failed: {str(e)}")

# Get Video Info button
if st.button("Get Video Info"):
    if youtube_url:
        with st.spinner("Fetching video information..."):
            try:
                start_time = time.time()
                video_details, formats = get_video_info(youtube_url)
                fetch_time = time.time() - start_time
                
                if video_details and formats:
                    st.success(f"Video information fetched in {fetch_time:.2f} seconds")
                    
                    # Store in session state
                    st.session_state.video_details = video_details
                    st.session_state.formats = formats
                else:
                    st.error("Failed to fetch video information. Please check the URL and try again.")
            except Exception as e:
                st.error(f"Error fetching video info: {str(e)}")
    else:
        st.error("Please enter a YouTube URL first")

# Display video information and download options if available
if 'video_details' in st.session_state and 'formats' in st.session_state:
    video_details = st.session_state.video_details
    formats = st.session_state.formats
    
    # Display video information
    st.subheader(f"Video: {video_details['title']}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if video_details['thumbnail']:
            st.image(video_details['thumbnail'], width=180)
        else:
            st.write("No thumbnail available")
    
    with col2:
        st.write(f"**Channel:** {video_details['channel']}")
        st.write(f"**Length:** {format_duration(video_details['duration'])}")
        st.write(f"**Views:** {video_details['views']:,}")
    
    # Display download options
    st.subheader("Download Options")
    
    # Resolution order (highest to lowest)
    resolution_order = [
        "4K (2160p)", 
        "2K (1440p)", 
        "1080p (Full HD)", 
        "720p (HD)", 
        "480p", 
        "360p", 
        "240p", 
        "144p",
        "Audio Only (MP3)"
    ]
    
    # Create columns for the table header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.write("**Quality**")
    with col2:
        st.write("**Size**")
    with col3:
        st.write("**Download**")
    
    # Display formats in order
    for res in resolution_order:
        if res in formats:
            format_info = formats[res]
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{res}**")
            
            with col2:
                if 'filesize' in format_info:
                    size = format_size(format_info['filesize'])
                    st.write(f"{size}")
                else:
                    st.write("Size varies")
            
            with col3:
                # Check if we have a direct download URL
                if format_info.get('direct_url'):
                    # Create a direct download link
                    download_url = format_info['direct_url']
                    ext = format_info.get('ext', 'mp4')
                    
                    # Make the filename safe
                    safe_title = re.sub(r'[^\w\-_\. ]', '_', video_details['title'])
                    filename = f"{safe_title} - {res}.{ext}"
                    
                    # Use HTML to create a download link with filename
                    st.markdown(
                        f'<a href="{download_url}" download="{filename}" target="_blank">Direct Download</a>', 
                        unsafe_allow_html=True
                    )
                else:
                    # Create a button to download via server
                    download_key = f"{video_details['id']}_{res}"
                    if st.button(f"Download {res}", key=download_key):
                        try:
                            with st.spinner(f"Processing {res} video..."):
                                # Download the video
                                filename, file_data = download_video(
                                    youtube_url, 
                                    format_info['format_id'], 
                                    video_details['id'],
                                    res
                                )
                                
                                # Store the download
                                st.session_state.downloads[download_key] = {
                                    'filename': filename,
                                    'data': file_data,
                                    'quality': res
                                }
                                
                                # Force refresh
                                st.rerun()
                        except Exception as e:
                            st.error(f"Download failed: {str(e)}")
                    
                    # If download is complete, show download link
                    if download_key in st.session_state.downloads:
                        download_info = st.session_state.downloads[download_key]
                        
                        # Create a download link
                        b64_data = base64.b64encode(download_info['data']).decode()
                        
                        # Make the filename safe
                        safe_title = re.sub(r'[^\w\-_\. ]', '_', video_details['title'])
                        ext = 'mp3' if res == "Audio Only (MP3)" else 'mp4'
                        filename = f"{safe_title} - {res}.{ext}"
                        
                        # Create download link
                        href = f'<a href="data:{"audio" if ext == "mp3" else "video"}/{ext};base64,{b64_data}" download="{filename}">Download {download_info["quality"]}</a>'
                        st.markdown(href, unsafe_allow_html=True)

# Instructions
with st.expander("How to use"):
    st.write("""
    ### Instructions
    
    1. Enter a YouTube URL and click "Get Video Info"
    2. Choose your preferred quality (144p to 4K)
    3. For some formats, you'll see a "Direct Download" link - click this to download directly
    4. For other formats, click the "Download" button and wait for processing, then click the download link
    5. The video will be saved to your device with audio included
    
    ### Quality Options
    
    - **4K (2160p)** and **2K (1440p)** videos are very high quality but may not play smoothly on all devices
    - **Full HD (1080p)** is recommended for most users - good quality and compatible with most devices
    - **HD (720p)** is a good balance of quality and file size
    - **480p** and **360p** are lower quality but smaller file size
    - **240p** and **144p** are very low quality but smallest file size
    - **Audio Only (MP3)** options are available for downloading just the sound
    
    ### Troubleshooting
    
    - If a download fails, try a different quality option
    - Some videos may be restricted and cannot be downloaded
    - If you get an error, try again or try a different video
    - For high-resolution videos (2K/4K), use VLC Media Player for best playback
    """)

# Footer
st.markdown("---")
st.caption("Made with Streamlit and yt-dlp • All downloads include audio")
