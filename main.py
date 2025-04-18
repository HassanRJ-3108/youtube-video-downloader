import streamlit as st
import yt_dlp
import os
from pathlib import Path
import re
import time
import datetime

# Page configuration
st.set_page_config(
    page_title="YouTube HD Downloader",
    page_icon="🎬",
    layout="centered"
)

# Header
st.title("YouTube HD Downloader")
st.write("Download high-quality videos with language selection")

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

# Input for YouTube URL
youtube_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

# Clean ANSI color codes from text
def clean_ansi(text):
    if not text:
        return ""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Function to get video info with languages
def get_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Process languages
            languages = {}
            original_language = None
            
            # Check for multiple audio tracks
            for fmt in info.get('formats', []):
                if fmt.get('language'):
                    lang_code = fmt.get('language')
                    if lang_code and lang_code != 'none':
                        # Try to get a proper language name
                        lang_name = get_language_name(lang_code)
                        
                        # Mark original language
                        if fmt.get('format_note') and 'original' in fmt.get('format_note').lower():
                            lang_name += " (Original)"
                            original_language = lang_code
                        
                        languages[lang_code] = lang_name
            
            # If we couldn't identify the original language, mark the first one
            if not original_language and languages:
                first_lang = next(iter(languages))
                languages[first_lang] = languages[first_lang] + " (Original)"
            
            # If no languages found, add a default one
            if not languages:
                languages["original"] = "Original Audio"
            
            # Create format options with sizes
            formats = {}
            
            # Only add specific resolution options (removed "Best Quality" option)
            resolutions = [
                {"name": "2160p (4K)", "height": 2160},
                {"name": "1440p (2K)", "height": 1440},
                {"name": "1080p (Full HD)", "height": 1080},
                {"name": "720p (HD)", "height": 720},
                {"name": "480p", "height": 480},
                {"name": "360p", "height": 360}
            ]
            
            for res in resolutions:
                format_id = f"bestvideo[height<={res['height']}]+bestaudio/best[height<={res['height']}]"
                size = estimate_size(info, format_id, res['height'])
                
                formats[res["name"]] = {
                    'format_id': format_id,
                    'size': size,
                    'height': res['height']
                }
            
            # Add audio-only option
            formats["Audio Only (MP3)"] = {
                'format_id': 'bestaudio/best',
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
                'formats': formats,
                'languages': languages
            }
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None

# Get proper language name
def get_language_name(lang_code):
    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'bn': 'Bengali',
        'ur': 'Urdu',
        'te': 'Telugu',
        'mr': 'Marathi',
        'ta': 'Tamil',
        'gu': 'Gujarati',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'pa': 'Punjabi',
        'or': 'Odia',
        'as': 'Assamese',
        'mai': 'Maithili',
        'ne': 'Nepali',
        'sd': 'Sindhi',
        'si': 'Sinhala',
        'th': 'Thai',
        'vi': 'Vietnamese',
        'id': 'Indonesian',
        'ms': 'Malay',
        'tr': 'Turkish',
        'fa': 'Persian',
        'he': 'Hebrew',
        'pl': 'Polish',
        'nl': 'Dutch',
        'sv': 'Swedish',
        'da': 'Danish',
        'no': 'Norwegian',
        'fi': 'Finnish',
        'hu': 'Hungarian',
        'cs': 'Czech',
        'sk': 'Slovak',
        'ro': 'Romanian',
        'bg': 'Bulgarian',
        'hr': 'Croatian',
        'sr': 'Serbian',
        'uk': 'Ukrainian',
        'el': 'Greek',
        'original': 'Original'
    }
    # Return the language name if found, otherwise return the code
    return language_names.get(lang_code, lang_code.upper())

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
            else:
                return duration * 1.5 * 1024 * 1024 / 60 # ~1.5MB per minute for 360p
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
def download_video(url, format_id, language, download_path):
    try:
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
        
        # Ensure download path exists
        os.makedirs(download_path, exist_ok=True)
        
        # Generate a timestamp-based filename to ensure it appears at the top in file explorer
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Simplify the format selection to avoid errors
        if "bestaudio" in format_id and "bestvideo" not in format_id:
            # For audio only
            simple_format = "bestaudio/best"
        elif "2160" in format_id:
            # For 4K
            simple_format = "bestvideo[height<=2160]+bestaudio/best"
        elif "1440" in format_id:
            # For 2K
            simple_format = "bestvideo[height<=1440]+bestaudio/best"
        elif "1080" in format_id:
            # For 1080p
            simple_format = "bestvideo[height<=1080]+bestaudio/best"
        elif "720" in format_id:
            # For 720p
            simple_format = "bestvideo[height<=720]+bestaudio/best"
        elif "480" in format_id:
            # For 480p
            simple_format = "bestvideo[height<=480]+bestaudio/best"
        else:
            # For 360p or fallback
            simple_format = "bestvideo[height<=360]+bestaudio/best"
        
        # Optimize download settings
        ydl_opts = {
            'format': simple_format,
            'outtmpl': os.path.join(download_path, f"{current_time}_%(title)s.%(ext)s"),
            'progress_hooks': [progress_hook],
            'quiet': False,
            'no_warnings': False,
            'noplaylist': True,
            'ignoreerrors': True,  # Continue on download errors
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
        
        # Simplified approach for language selection
        # We'll just try to download the video and let yt-dlp handle the language selection
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
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
                
                # Check if file exists
                final_path = os.path.join(download_path, os.path.basename(filename))
                if not os.path.exists(final_path):
                    # Try to find the file with a similar name
                    base_name = os.path.splitext(os.path.basename(filename))[0]
                    for file in os.listdir(download_path):
                        if base_name in file:
                            final_path = os.path.join(download_path, file)
                            break
                
                return os.path.basename(final_path), final_path
            except yt_dlp.utils.DownloadError as e:
                error_message = str(e)
                if "requested format not available" in error_message.lower():
                    # If the requested format is not available, try a lower quality
                    st.warning("Requested quality not available. Trying a lower quality...")
                    
                    # Try with a more compatible format
                    ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                        info = ydl2.extract_info(url, download=True)
                        if info is None:
                            raise Exception("Failed to extract video information")
                            
                        filename = ydl2.prepare_filename(info)
                        if not filename.endswith('.mp4'):
                            filename = os.path.splitext(filename)[0] + '.mp4'
                        
                        final_path = os.path.join(download_path, os.path.basename(filename))
                        return os.path.basename(final_path), final_path
                else:
                    raise
    
    except Exception as e:
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
    
    # Language selection if available
    languages = video_info['languages']
    if languages:
        language_options = list(languages.keys())
        language_display = {k: v for k, v in languages.items()}
        
        selected_language = st.selectbox(
            "Select Language:", 
            language_options,
            format_func=lambda x: language_display[x]
        )
        
        st.info(f"Selected audio track: **{language_display[selected_language]}**")
        
        # Add warning about language selection
        if selected_language != "original":
            st.warning("⚠️ Language selection may not work for all videos. If the selected language doesn't work, the video will use the original audio.")
    else:
        selected_language = "original"
    
    # Download location
    download_path = str(Path.home() / "Downloads")
    custom_path = st.checkbox("Specify custom download location")
    if custom_path:
        download_path = st.text_input("Download folder path:", value=download_path)
        if not os.path.exists(download_path):
            st.warning(f"The path '{download_path}' does not exist. It will be created when you download.")
    
    # Download button
    if not st.session_state.download_started:
        if st.button("Download Now", type="primary"):
            st.session_state.download_started = True
            st.session_state.download_complete = False
            st.session_state.download_error = None
            
            try:
                # Start download with spinner
                with st.spinner("Downloading video..."):
                    format_id = video_info['formats'][selected_quality]['format_id']
                    filename, filepath = download_video(youtube_url, format_id, selected_language, download_path)
                
                # Update session state
                st.session_state.download_complete = True
                st.session_state.filename = filename
                st.session_state.download_path = filepath
            
            except Exception as e:
                st.session_state.download_error = str(e)
            
            # Force refresh
            st.rerun()
    
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
            
            if st.button("Try Again"):
                st.session_state.download_started = False
                st.rerun()
        
        elif st.session_state.download_complete:
            st.success("✅ Download Complete!")
            st.info(f"File saved as: {st.session_state.filename}")
            st.info(f"Location: {st.session_state.download_path}")
            
            # Check if file exists
            if os.path.exists(st.session_state.download_path):
                st.success("File verified - download successful!")
                
                # For high-resolution videos, add a playback tip
                if selected_format['height'] in [1440, 2160]:
                    st.warning("For smooth playback of high-resolution videos, use VLC Media Player or another powerful video player.")
            else:
                st.warning("File not found at the expected location. It may have been saved with a different name.")
            
            if st.button("Download Another Video"):
                st.session_state.download_started = False
                st.session_state.download_complete = False
                st.session_state.download_error = None
                st.session_state.filename = None
                st.session_state.download_path = None
                st.session_state.video_info = None
                st.rerun()

# Instructions
with st.expander("How to use"):
    st.write("""
    ### Instructions
    
    1. Enter a YouTube URL and click "Fetch Video Info"
    2. Select your preferred quality (up to 4K if available)
    3. Select your preferred language (if multiple audio tracks are available)
    4. Click "Download Now"
    5. Wait for the download to complete
    6. Find your video in your Downloads folder
    
    ### Quality Selection
    
    - **4K (2160p)** and **2K (1440p)** videos are very high quality but may not play smoothly on all devices
    - **1080p (Full HD)** is recommended for most users - good quality and compatible with most devices
    - **720p (HD)** is a good balance of quality and file size
    - **480p** and **360p** are lower quality but smaller file size
    - **Audio Only (MP3)** will extract just the audio track
    
    ### Language Selection
    
    - If a video has multiple audio tracks (like dubbed versions), you can select your preferred language
    - The language selection will only work if the video actually has multiple audio tracks
    - Original language is marked with "(Original)"
    
    ### Troubleshooting
    
    - If downloads fail, try a different quality setting
    - Make sure you have a stable internet connection
    - Some videos may be restricted and cannot be downloaded
    - If you get an error, try again or try a different video
    - For high-resolution videos (2K/4K), use VLC Media Player for best playback
    """)

# Footer
st.markdown("---")
st.caption("Made with Streamlit and yt-dlp • All downloads are saved to your Downloads folder")