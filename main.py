import streamlit as st
import yt_dlp
import re
import time

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

# Function to get direct download links
def get_download_links(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'youtube_include_dash_manifest': False,  # Exclude DASH formats
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get video details
            video_details = {
                'title': info.get('title', 'Unknown'),
                'channel': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'views': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail', ''),
            }
            
            # Get available formats
            formats = []
            
            # Filter and organize formats
            video_formats = []
            audio_formats = []
            
            for f in info.get('formats', []):
                # Skip formats without url
                if not f.get('url'):
                    continue
                
                # Skip formats with "none" in format_note
                if f.get('format_note') and 'none' in f.get('format_note').lower():
                    continue
                
                # Skip DASH formats (they require separate audio download)
                if f.get('container') == 'webm_dash':
                    continue
                
                # Skip formats without extension
                if not f.get('ext'):
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
                }
                
                # Separate audio and video formats
                if format_info['vcodec'] == 'none':
                    audio_formats.append(format_info)
                elif format_info['acodec'] != 'none' and format_info['vcodec'] != 'none':
                    video_formats.append(format_info)
            
            # Sort video formats by height (quality)
            video_formats.sort(key=lambda x: (x['height'] or 0, x['filesize'] or 0), reverse=True)
            
            # Sort audio formats by filesize (quality)
            audio_formats.sort(key=lambda x: x['filesize'] or 0, reverse=True)
            
            # Create organized format list
            organized_formats = {
                'video': video_formats,
                'audio': audio_formats[:3]  # Limit to top 3 audio formats
            }
            
            return video_details, organized_formats
    
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

# Get quality label
def get_quality_label(format_info):
    height = format_info.get('height', 0)
    
    if not height:
        return "Unknown"
    
    if height >= 2160:
        return "4K"
    elif height >= 1440:
        return "2K"
    elif height >= 1080:
        return "Full HD"
    elif height >= 720:
        return "HD"
    elif height >= 480:
        return "SD"
    elif height >= 360:
        return "360p"
    elif height >= 240:
        return "240p"
    else:
        return "144p"

# Always show the "Get Download Links" button
if st.button("Get Download Links"):
    if youtube_url:
        with st.spinner("Fetching video information..."):
            try:
                start_time = time.time()
                video_details, formats = get_download_links(youtube_url)
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
    
    # Video formats
    if formats['video']:
        st.write("### Video Formats (with audio)")
        
        for i, format_info in enumerate(formats['video']):
            quality = get_quality_label(format_info)
            size = format_size(format_info.get('filesize', 0))
            ext = format_info.get('ext', 'mp4')
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{quality}** ({format_info.get('width', 0)}x{format_info.get('height', 0)})")
            
            with col2:
                st.write(f"Size: {size}")
            
            with col3:
                # Create a direct download link
                st.markdown(f"[Download .{ext}]({format_info['url']})", unsafe_allow_html=True)
    
    # Audio formats
    if formats['audio']:
        st.write("### Audio Only")
        
        for i, format_info in enumerate(formats['audio']):
            size = format_size(format_info.get('filesize', 0))
            ext = format_info.get('ext', 'mp3')
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Audio** ({format_info.get('format_note', 'Unknown quality')})")
            
            with col2:
                st.write(f"Size: {size}")
            
            with col3:
                # Create a direct download link
                st.markdown(f"[Download .{ext}]({format_info['url']})", unsafe_allow_html=True)

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
    - **SD (480p)** and **360p** are lower quality but smaller file size
    - **240p** and **144p** are very low quality but smallest file size
    - **Audio Only** options are available for downloading just the sound
    
    ### Troubleshooting
    
    - If a download link doesn't work, try a different quality option
    - Some videos may be restricted and cannot be downloaded
    - If you get an error, try again or try a different video
    - For high-resolution videos (2K/4K), use VLC Media Player for best playback
    """)

# Footer
st.markdown("---")
st.caption("Made with Streamlit and yt-dlp • Click any Download link to save directly to your device")
