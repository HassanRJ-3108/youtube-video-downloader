import streamlit as st
import yt_dlp
import re
import time
import json

# Page configuration
st.set_page_config(
    page_title="YouTube Direct Downloader",
    page_icon="🎬",
    layout="centered"
)

# Header
st.title("YouTube Direct Downloader")
st.write("Get direct download links for YouTube videos")

# Input for YouTube URL
youtube_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

# Function to get direct download links with both video and audio
def get_direct_download_links(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'format': 'best',  # Get best format first to get video details
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First get video info
            info = ydl.extract_info(url, download=False)
            
            # Get video details
            video_details = {
                'title': info.get('title', 'Unknown'),
                'channel': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'views': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail', ''),
            }
            
            # Now get all formats with direct links
            formats = []
            
            # Filter for formats that have both video and audio
            for f in info.get('formats', []):
                # Skip formats without url
                if not f.get('url'):
                    continue
                
                # Skip formats without extension
                if not f.get('ext'):
                    continue
                
                # Skip audio-only formats (we'll handle those separately)
                if f.get('vcodec') == 'none':
                    continue
                
                # Skip video-only formats (we want formats with both video and audio)
                if f.get('acodec') == 'none':
                    continue
                
                # Create format info
                format_info = {
                    'format_id': f.get('format_id', ''),
                    'ext': f.get('ext', ''),
                    'url': f.get('url', ''),
                    'filesize': f.get('filesize', 0),
                    'format_note': f.get('format_note', ''),
                    'height': f.get('height', 0),
                    'width': f.get('width', 0),
                    'fps': f.get('fps', 0),
                    'acodec': f.get('acodec', ''),
                    'vcodec': f.get('vcodec', ''),
                    'resolution': f'{f.get("width", 0)}x{f.get("height", 0)}',
                }
                
                formats.append(format_info)
            
            # Get audio-only formats
            audio_formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('url'):
                    audio_format = {
                        'format_id': f.get('format_id', ''),
                        'ext': f.get('ext', ''),
                        'url': f.get('url', ''),
                        'filesize': f.get('filesize', 0),
                        'format_note': f.get('format_note', ''),
                        'acodec': f.get('acodec', ''),
                    }
                    audio_formats.append(audio_format)
            
            # Sort formats by height (quality)
            formats.sort(key=lambda x: (x['height'] or 0, x['filesize'] or 0), reverse=True)
            
            # Sort audio formats by filesize (quality)
            audio_formats.sort(key=lambda x: x['filesize'] or 0, reverse=True)
            
            # Group formats by resolution
            grouped_formats = {}
            for fmt in formats:
                height = fmt.get('height', 0)
                if height >= 2160:
                    key = "4K (2160p)"
                elif height >= 1440:
                    key = "2K (1440p)"
                elif height >= 1080:
                    key = "1080p (Full HD)"
                elif height >= 720:
                    key = "720p (HD)"
                elif height >= 480:
                    key = "480p"
                elif height >= 360:
                    key = "360p"
                elif height >= 240:
                    key = "240p"
                elif height > 0:
                    key = "144p"
                else:
                    continue  # Skip formats with no height
                
                if key not in grouped_formats:
                    grouped_formats[key] = []
                grouped_formats[key].append(fmt)
            
            # Take the best format from each resolution group
            best_formats = {}
            for res, fmts in grouped_formats.items():
                if fmts:
                    # Sort by filesize (higher is better quality)
                    fmts.sort(key=lambda x: x.get('filesize', 0) or 0, reverse=True)
                    best_formats[res] = fmts[0]
            
            # Add best audio format
            if audio_formats:
                best_formats["Audio Only (MP3)"] = audio_formats[0]
            
            return video_details, best_formats
    
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

# Always show the "Get Download Links" button
if st.button("Get Download Links"):
    if youtube_url:
        with st.spinner("Fetching video information..."):
            try:
                start_time = time.time()
                video_details, formats = get_direct_download_links(youtube_url)
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

# Display video information and download links if available
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
    st.subheader("Download Links")
    st.write("👇 Click any link below to download directly to your device")
    
    # Create a table for download links
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.write("**Quality**")
    with col2:
        st.write("**Size**")
    with col3:
        st.write("**Download**")
    
    # Sort formats by resolution (highest first)
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
    
    # Display formats in order
    for res in resolution_order:
        if res in formats:
            format_info = formats[res]
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{res}**")
            
            with col2:
                size = format_size(format_info.get('filesize', 0))
                st.write(f"{size}")
            
            with col3:
                # Create a direct download link
                ext = format_info.get('ext', 'mp4')
                download_url = format_info['url']
                
                # Make the filename safe
                safe_title = re.sub(r'[^\w\-_\. ]', '_', video_details['title'])
                
                # Create download link with proper filename
                if res == "Audio Only (MP3)":
                    link_text = "Download MP3"
                    filename = f"{safe_title}.mp3"
                else:
                    link_text = f"Download {ext.upper()}"
                    filename = f"{safe_title} - {res}.{ext}"
                
                # Use HTML to create a download link with filename
                st.markdown(
                    f'<a href="{download_url}" download="{filename}" target="_blank">{link_text}</a>', 
                    unsafe_allow_html=True
                )
    
    # Add warning for high-resolution videos
    if "4K (2160p)" in formats or "2K (1440p)" in formats:
        st.warning("⚠️ **Note:** 4K and 2K videos may not play smoothly on some devices. VLC or a powerful media player is recommended.")

# Instructions
with st.expander("How to use"):
    st.write("""
    ### Instructions
    
    1. Enter a YouTube URL and click "Get Download Links"
    2. Wait for the video information to load
    3. Click on any of the "Download" links to directly download the video or audio
    4. The download will start immediately in your browser
    
    ### Quality Options
    
    - **4K (2160p)** and **2K (1440p)** videos are very high quality but may not play smoothly on all devices
    - **Full HD (1080p)** is recommended for most users - good quality and compatible with most devices
    - **HD (720p)** is a good balance of quality and file size
    - **480p** and **360p** are lower quality but smaller file size
    - **240p** and **144p** are very low quality but smallest file size
    - **Audio Only (MP3)** options are available for downloading just the sound
    
    ### Troubleshooting
    
    - If a download link doesn't work, try a different quality option
    - Some videos may be restricted and cannot be downloaded
    - If you get an error, try again or try a different video
    - For high-resolution videos (2K/4K), use VLC Media Player for best playback
    """)

# Footer
st.markdown("---")
st.caption("Made with Streamlit and yt-dlp • Click any Download link to save directly to your device")
