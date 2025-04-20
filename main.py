import streamlit as st
import yt_dlp
import re
import time

# Page configuration
st.set_page_config(
    page_title="YouTube HD Downloader",
    page_icon="🎬",
    layout="centered"
)

# Header
st.title("YouTube HD Downloader")
st.write("Download videos in any quality (144p to 4K)")

# Input for YouTube URL
youtube_url = st.text_input("Enter YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

# Function to get ALL available formats with audio
def get_all_formats(url):
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
            
            # Get all formats with both video and audio
            combined_formats = []
            for f in info.get('formats', []):
                # Skip formats without url
                if not f.get('url'):
                    continue
                
                # Skip formats without extension
                if not f.get('ext'):
                    continue
                
                # Only include formats with both video and audio
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
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
                    combined_formats.append(format_info)
            
            # Get best audio-only format
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
            
            # Sort audio formats by filesize (quality)
            audio_formats.sort(key=lambda x: x.get('filesize', 0) or 0, reverse=True)
            
            # Get best audio format
            best_audio = audio_formats[0] if audio_formats else None
            
            # Organize formats by resolution
            resolution_groups = {}
            
            # Define resolution groups
            resolutions = [
                {"name": "4K (2160p)", "min_height": 2160, "max_height": 9999},
                {"name": "2K (1440p)", "min_height": 1440, "max_height": 2159},
                {"name": "1080p (Full HD)", "min_height": 1080, "max_height": 1439},
                {"name": "720p (HD)", "min_height": 720, "max_height": 1079},
                {"name": "480p", "min_height": 480, "max_height": 719},
                {"name": "360p", "min_height": 360, "max_height": 479},
                {"name": "240p", "min_height": 240, "max_height": 359},
                {"name": "144p", "min_height": 1, "max_height": 239},
            ]
            
            # Group formats by resolution
            for res in resolutions:
                resolution_groups[res["name"]] = []
                
                for fmt in combined_formats:
                    height = fmt.get('height', 0)
                    if height >= res["min_height"] and height <= res["max_height"]:
                        resolution_groups[res["name"]].append(fmt)
            
            # Sort formats within each resolution group by filesize (quality)
            for res_name, formats in resolution_groups.items():
                formats.sort(key=lambda x: x.get('filesize', 0) or 0, reverse=True)
            
            # Remove empty resolution groups
            resolution_groups = {k: v for k, v in resolution_groups.items() if v}
            
            return video_details, resolution_groups, best_audio
    
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None, None, None

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

# Get Download Links button
if st.button("Get Download Links"):
    if youtube_url:
        with st.spinner("Fetching video information..."):
            try:
                start_time = time.time()
                video_details, resolution_groups, best_audio = get_all_formats(youtube_url)
                fetch_time = time.time() - start_time
                
                if video_details and resolution_groups:
                    st.success(f"Video information fetched in {fetch_time:.2f} seconds")
                    
                    # Store in session state
                    st.session_state.video_details = video_details
                    st.session_state.resolution_groups = resolution_groups
                    st.session_state.best_audio = best_audio
                else:
                    st.error("Failed to fetch video information. Please check the URL and try again.")
            except Exception as e:
                st.error(f"Error fetching video info: {str(e)}")
    else:
        st.error("Please enter a YouTube URL first")

# Display video information and download links if available
if 'video_details' in st.session_state and 'resolution_groups' in st.session_state:
    video_details = st.session_state.video_details
    resolution_groups = st.session_state.resolution_groups
    best_audio = st.session_state.best_audio
    
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
    st.write("�� Click any link below to download directly to your device")
    
    # Resolution order (highest to lowest)
    resolution_order = [
        "4K (2160p)", 
        "2K (1440p)", 
        "1080p (Full HD)", 
        "720p (HD)", 
        "480p", 
        "360p", 
        "240p", 
        "144p"
    ]
    
    # Display formats by resolution
    for res_name in resolution_order:
        if res_name in resolution_groups and resolution_groups[res_name]:
            st.write(f"### {res_name}")
            
            # Display all formats in this resolution group
            for i, format_info in enumerate(resolution_groups[res_name]):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    fps = format_info.get('fps', 0)
                    ext = format_info.get('ext', 'mp4')
                    format_note = format_info.get('format_note', '')
                    
                    details = []
                    if fps:
                        details.append(f"{fps} FPS")
                    if format_note:
                        details.append(format_note)
                    
                    details_str = f" ({', '.join(details)})" if details else ""
                    st.write(f"**Option {i+1}**{details_str}")
                
                with col2:
                    size = format_size(format_info.get('filesize', 0))
                    st.write(f"{size}")
                
                with col3:
                    # Create a direct download link
                    download_url = format_info['url']
                    
                    # Make the filename safe
                    safe_title = re.sub(r'[^\w\-_\. ]', '_', video_details['title'])
                    filename = f"{safe_title} - {res_name}.{ext}"
                    
                    # Use HTML to create a download link with filename
                    st.markdown(
                        f'<a href="{download_url}" download="{filename}" target="_blank">Download {ext.upper()}</a>', 
                        unsafe_allow_html=True
                    )
    
    # Display audio-only option
    if best_audio:
        st.write("### Audio Only (MP3)")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            format_note = best_audio.get('format_note', 'Best quality')
            st.write(f"**Audio Only** ({format_note})")
        
        with col2:
            size = format_size(best_audio.get('filesize', 0))
            st.write(f"{size}")
        
        with col3:
            # Create a direct download link
            download_url = best_audio['url']
            
            # Make the filename safe
            safe_title = re.sub(r'[^\w\-_\. ]', '_', video_details['title'])
            filename = f"{safe_title} - Audio.{best_audio.get('ext', 'mp3')}"
            
            # Use HTML to create a download link with filename
            st.markdown(
                f'<a href="{download_url}" download="{filename}" target="_blank">Download MP3</a>', 
                unsafe_allow_html=True
            )
    
    # Add warning for high-resolution videos
    if "4K (2160p)" in resolution_groups or "2K (1440p)" in resolution_groups:
        st.warning("⚠️ **Note:** 4K and 2K videos may not play smoothly on some devices. VLC or a powerful media player is recommended.")

# Instructions
with st.expander("How to use"):
    st.write("""
    ### Instructions
    
    1. Enter a YouTube URL and click "Get Download Links"
    2. Wait for the video information to load
    3. Choose your preferred quality (144p to 4K)
    4. Click on any "Download" link to save directly to your device
    5. The download will start immediately in your browser
    
    ### Quality Options
    
    - **4K (2160p)** and **2K (1440p)** videos are very high quality but may not play smoothly on all devices
    - **Full HD (1080p)** is recommended for most users - good quality and compatible with most devices
    - **HD (720p)** is a good balance of quality and file size
    - **480p** and **360p** are lower quality but smaller file size
    - **240p** and **144p** are very low quality but smallest file size
    - **Audio Only (MP3)** options are available for downloading just the sound
    
    ### Troubleshooting
    
    - If a download link doesn't work, try a different option within the same resolution
    - Some videos may be restricted and cannot be downloaded
    - If you get an error, try again or try a different video
    - For high-resolution videos (2K/4K), use VLC Media Player for best playback
    """)

# Footer
st.markdown("---")
st.caption("Made with Streamlit and yt-dlp • Click any Download link to save directly to your device")
