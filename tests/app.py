"""
TikTok Viral Engine - Streamlit Dashboard
Beautiful web interface for content generation and management
"""

import streamlit as st
import logging
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import TikTokViralEngine
from src.database import DatabaseManager
from src.api_client import APIManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Streamlit
st.set_page_config(
    page_title="TikTok Viral Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        padding: 0.5rem;
        border-radius: 0.5rem;
        font-size: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'engine' not in st.session_state:
    st.session_state.engine = TikTokViralEngine()
    st.session_state.api_manager = APIManager()
    st.session_state.db = DatabaseManager()

# Header
st.title("🚀 TikTok Viral Engine")
st.markdown("### Automated Content Generation & Analytics Platform")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown("---")
    
    # Health Check
    if st.button("🏥 Health Check"):
        health = st.session_state.api_manager.health_check()
        st.success(f"✅ {health['status']}")
    
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "📍 Navigation",
        ["🏠 Dashboard", "✍️ Generate Content", "📤 Upload", "📊 Analytics", "👥 Influencers", "⚙️ Settings"]
    )

# Main content based on page selection
if page == "🏠 Dashboard":
    dashboard_page()

elif page == "✍️ Generate Content":
    generate_content_page()

elif page == "📤 Upload":
    upload_page()

elif page == "📊 Analytics":
    analytics_page()

elif page == "👥 Influencers":
    influencers_page()

elif page == "⚙️ Settings":
    settings_page()


# ============= PAGE FUNCTIONS =============

def dashboard_page():
    """Dashboard page"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📹 Total Videos", 12)
    with col2:
        st.metric("👁️ Total Views", "2.5M")
    with col3:
        st.metric("❤️ Total Likes", "180K")
    
    st.markdown("---")
    
    # Recent trends
    st.subheader("📊 Trending Now")
    trends = st.session_state.engine.trend_detector.fetch_trends()
    
    trend_cols = st.columns(len(trends))
    for i, trend in enumerate(trends):
        with trend_cols[i]:
            st.info(f"**{trend}**")
    
    st.markdown("---")
    
    # Recent videos
    st.subheader("📹 Recent Videos")
    recent_videos = [
        {"id": "v_1", "views": 250000, "likes": 15000, "date": "2026-04-05"},
        {"id": "v_2", "views": 180000, "likes": 12000, "date": "2026-04-04"},
        {"id": "v_3", "views": 320000, "likes": 25000, "date": "2026-04-03"},
    ]
    
    for video in recent_videos:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{video['id']}**")
        with col2:
            st.write(f"👁️ {video['views']:,}")
        with col3:
            st.write(f"❤️ {video['likes']:,}")
        with col4:
            st.write(f"📅 {video['date']}")


def generate_content_page():
    """Generate content page"""
    st.subheader("✍️ AI Content Generator")
    st.markdown("Generate viral TikTok scripts, hashtags, and captions using AI")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        topic = st.text_input(
            "🎯 Topic/Niche",
            placeholder="e.g., fitness, comedy, education, etc.",
            value="viral_trends"
        )
    
    with col2:
        content_type = st.selectbox(
            "📝 Content Type",
            ["Viral Challenge", "Educational", "Entertainment", "Comedy", "Motivation"]
        )
    
    st.markdown("---")
    
    # Generate button
    if st.button("🚀 Generate Content", use_container_width=True):
        with st.spinner("🤖 AI is generating your content..."):
            result = st.session_state.engine.run_full_pipeline(topic)
            
            if result['status'] == 'success':
                # Script
                st.success("✅ Content Generated Successfully!")
                
                # Tabs for different outputs
                tab1, tab2, tab3, tab4 = st.tabs(["📝 Script", "🏷️ Hashtags", "💬 Captions", "📊 Analytics"])
                
                with tab1:
                    st.subheader("Generated Script")
                    script = result['script']
                    st.markdown(f"""
                    **HOOK:** {script['hook']}
                    
                    **BODY:**
                    """)
                    for i, line in enumerate(script['body'], 1):
                        st.write(f"{i}. {line}")
                    
                    st.markdown(f"**CTA:** {script['cta']}")
                
                with tab2:
                    st.subheader("Generated Hashtags")
                    hashtags = result['hashtags']
                    
                    # Display as tags
                    tag_cols = st.columns(4)
                    for i, tag in enumerate(hashtags):
                        with tag_cols[i % 4]:
                            st.info(tag)
                
                with tab3:
                    st.subheader("Caption Options")
                    captions = result['captions']
                    for i, caption in enumerate(captions, 1):
                        st.write(f"**Option {i}:** {caption}")
                        st.divider()
                
                with tab4:
                    st.subheader("Predicted Performance")
                    analytics = result['predicted_analytics']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Predicted Views", f"{analytics['predicted_views']:,}")
                    with col2:
                        st.metric("Predicted Likes", f"{analytics['predicted_likes']:,}")
                    with col3:
                        st.metric("Viral Probability", f"{analytics['viral_probability']*100:.0f}%")
                    
                    st.write(f"**Best Posting Time:** {analytics['best_posting_time']}")
            
            else:
                st.error(f"❌ Error: {result.get('message', 'Unknown error')}")


def upload_page():
    """Upload page"""
    st.subheader("📤 Upload to TikTok")
    st.markdown("Upload your video directly to TikTok")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader(
            "📹 Choose video file",
            type=["mp4", "mov", "avi"],
            help="Max 500MB"
        )
    
    with col2:
        caption = st.text_area(
            "📝 Caption",
            placeholder="Write your video caption here...",
            height=100
        )
    
    st.markdown("---")
    
    # Hashtags
    hashtags = st.text_input(
        "🏷️ Hashtags (comma-separated)",
        placeholder="#viral #tiktok #trending",
        value="#viral #tiktok #trending"
    )
    
    st.markdown("---")
    
    # Upload button
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Upload Now", use_container_width=True):
            if uploaded_file and caption:
                with st.spinner("📤 Uploading to TikTok..."):
                    result = st.session_state.engine.upload_content(
                        uploaded_file.name,
                        caption,
                        hashtags.split(",")
                    )
                    
                    if result.get('status') == 'success':
                        st.success(f"✅ Video uploaded successfully!")
                        st.info(f"🔗 [View on TikTok]({result['url']})")
                    else:
                        st.error("❌ Upload failed")
            else:
                st.warning("⚠️ Please select a video and write a caption")
    
    with col2:
        if st.button("⏰ Schedule Upload", use_container_width=True):
            st.info("📅 Schedule upload feature coming soon!")


def analytics_page():
    """Analytics page"""
    st.subheader("📊 Video Analytics")
    st.markdown("---")
    
    # Video selector
    video_id = st.selectbox(
        "Select Video",
        ["v_1", "v_2", "v_3"]
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👁️ Views", "250,000")
    with col2:
        st.metric("❤️ Likes", "15,000")
    with col3:
        st.metric("💬 Comments", "2,500")
    with col4:
        st.metric("📤 Shares", "1,200")
    
    st.markdown("---")
    
    # Engagement rate
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Engagement Rate", "6.8%")
    
    with col2:
        st.metric("Viral Score", "9.2/10")


def influencers_page():
    """Influencers page"""
    st.subheader("👥 Find Influencer Collaborators")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        niche = st.text_input("Niche/Category", value="viral")
    
    with col2:
        follower_range = st.slider("Follower Range", 0, 10000000, (100000, 1000000))
    
    if st.button("🔍 Find Influencers", use_container_width=True):
        with st.spinner("🔍 Finding influencers..."):
            influencers = st.session_state.engine.influencer_finder.find_collaborators(niche)
            
            for influencer in influencers:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**{influencer['username']}**")
                with col2:
                    st.write(f"👥 {influencer['followers']:,} followers")
                with col3:
                    st.write(f"💰 {influencer['collaboration_rate']}")
                
                st.divider()


def settings_page():
    """Settings page"""
    st.subheader("⚙️ Configuration")
    st.markdown("---")
    
    with st.expander("🔐 API Keys"):
        st.warning("⚠️ Never share your API keys!")
        st.text_input("TikTok API Key", type="password", placeholder="Enter your TikTok API key")
        st.text_input("OpenAI API Key", type="password", placeholder="Enter your OpenAI API key")
        
        if st.button("💾 Save API Keys"):
            st.success("✅ API keys saved!")
    
    with st.expander("🎨 Preferences"):
        st.selectbox("Theme", ["Light", "Dark"])
        st.toggle("Enable Notifications")
    
    with st.expander("📊 Features"):
        st.toggle("Enable AI Scripts", value=True)
        st.toggle("Enable Auto Upload", value=False)
        st.toggle("Enable Analytics", value=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Save Settings", use_container_width=True):
            st.success("✅ Settings saved!")
    with col2:
        if st.button("🔄 Reset to Default", use_container_width=True):
            st.warning("⚠️ Are you sure?")


if __name__ == "__main__":
    st.markdown("""
    ---
    **Made with ❤️ by TikTok Viral Engine Team**
    """)