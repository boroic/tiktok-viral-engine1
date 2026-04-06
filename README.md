# 🚀 TikTok Viral Engine

Automated content generation and analytics platform for TikTok creators.

## 🌟 Features

### ✨ AI-Powered Content Generation
- Generate viral scripts using OpenAI GPT
- Auto-generate hashtags and captions
- Smart content recommendations
- Multi-part video series generation

### 🎵 Trend & Sound Analysis
- Real-time trending detection
- Trending sounds analysis
- Engagement predictions
- Viral score calculations

### 📊 Analytics & Performance Tracking
- Video performance analytics
- Engagement rate monitoring
- ROI calculations
- Historical data tracking

### 👥 Influencer Collaboration
- Find micro-influencers
- Match by budget and niche
- Collaboration recommendations
- Budget-based filtering

### 📤 Automated Upload
- One-click TikTok upload
- Scheduled posting
- Batch processing
- Multi-format support

### 💾 Database & Storage
- SQLAlchemy ORM
- Video metadata tracking
- Trend history
- Script library

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/boroic/tiktok-viral-engine1.git
cd tiktok-viral-engine1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys

# Run Streamlit dashboard
streamlit run app.py
```

### Flask API

```bash
python main.py
```

#### Run full pipeline by topic

```bash
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"topic":"fitness motivation"}'
```

#### Auto create faceless video (V7 MVP)

Generates a faceless 9:16 TikTok-ready package with:
- script + scene plan
- AI voiceover (if TTS API key/provider is available)
- burned subtitles
- exported MP4 download URL
- caption_final + hashtags

If external API keys are missing, the endpoint fails gracefully by returning script/caption outputs and clear guidance while marking video as not generated.

```bash
curl -X POST http://localhost:8080/auto-create-video \
  -H "Content-Type: application/json" \
  -d '{
    "topic":"morning productivity",
    "tone":"educational",
    "target_audience":"busy professionals",
    "duration":45,
    "voice_preset":"female",
    "style_preset":"checklist"
  }'
```

Download generated MP4:

```bash
curl -L "http://localhost:8080/artifacts/<artifact_id>/download" -o auto-video.mp4
```

#### Run full pipeline from uploaded media

Uploads an image/video to `/app`, analyzes media context, and generates script/captions/hashtags from the media-derived topic.

```bash
curl -X POST http://localhost:8080/run-from-media \
  -F "media=@/path/to/your/video.mp4"
```

### Web App (Flask `/app`)

The web UI now includes a dedicated **Auto Create Video (Faceless MVP)** card with:
- Inputs: topic, tone, target audience, duration (30/45/60), voice preset (male/female), style preset (educational/storytelling/checklist)
- Buttons: **Auto Create Video**, **Download MP4**, **Copy Caption**

Existing caption generation and media-based flows remain intact and backward compatible.
