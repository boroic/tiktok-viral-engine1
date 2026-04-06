"""AI Script Generation Module"""

import hashlib
import re

MAX_VARIANT_KEY_LENGTH = 512
MAX_TOPIC_HASHTAG_LENGTH = 30
MAX_TONE_HASHTAG_LENGTH = 20
MAX_AUDIENCE_HASHTAG_LENGTH = 24

class ScriptGenerator:
    """Generate viral TikTok scripts using AI"""
    
    def __init__(self):
        self.templates = []
    
    def _pick_variant(self, variants, key):
        if not variants:
            return ""
        safe_key = str(key or "")[:MAX_VARIANT_KEY_LENGTH]
        digest = hashlib.sha256(safe_key.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % len(variants)
        return variants[idx]

    def _sanitize_topic(self, topic):
        cleaned = re.sub(r"\s+", " ", str(topic or "").strip())
        return cleaned or "viral content"

    def _sanitize_text(self, text, max_len=180):
        cleaned = re.sub(r"\s+", " ", str(text or "").strip())
        return cleaned[:max_len]

    def _build_grounding_line(self, media_grounding):
        if not isinstance(media_grounding, dict):
            return ""
        snippets = []
        for key in ("ocr_text", "transcript_text", "keyframe_summary"):
            value = self._sanitize_text(media_grounding.get(key, ""), max_len=120)
            if value:
                snippets.append(value)
        return " | ".join(snippets[:2])

    def generate_script(self, trend, tone="balanced", target_audience="general", media_grounding=None):
        """Generate script based on trending topic"""
        topic = self._sanitize_topic(trend)
        tone_key = self._sanitize_text(tone, max_len=24).lower() or "balanced"
        audience = self._sanitize_text(target_audience, max_len=48) or "general audience"
        grounding_line = self._build_grounding_line(media_grounding)
        print(f"✍️ Generating script for {topic}...")

        hooks = [
            f"If you're into {topic}, try this next.",
            f"Quick breakdown: what actually works for {topic}.",
            f"Here’s a practical way to level up your {topic} content."
        ]
        if grounding_line:
            hooks = [
                f"From the media signals we found: {grounding_line}",
                f"Your media points to this angle: {grounding_line}",
                f"Based on the uploaded content: {grounding_line}"
            ]

        body_lines = [
            f"Start with one clear promise tailored for {audience}.",
            f"Keep each beat focused on one takeaway about {topic}.",
            "Close with a specific action viewers can try today."
        ]
        if tone_key in {"educational", "expert", "professional"}:
            body_lines = [
                f"Lead with the core insight {audience} needs first.",
                f"Use concise examples that make {topic} easy to apply.",
                "Wrap with one measurable next step."
            ]
        elif tone_key in {"fun", "playful", "casual"}:
            body_lines = [
                f"Open with an energetic one-liner about {topic}.",
                f"Deliver three quick, relatable beats for {audience}.",
                "End with a challenge viewers can duet or stitch."
            ]
        elif tone_key in {"bold", "confident"}:
            body_lines = [
                f"State a strong opinion on {topic} in the first seconds.",
                f"Back it up with one proof point your {audience} will trust.",
                "Invite viewers to pick a side in comments."
            ]

        cta_options = [
            "Save this so you can use it in your next post.",
            "Comment your angle and I’ll share a follow-up version.",
            "Follow for more creator-tested formats."
        ]
        if tone_key in {"educational", "expert", "professional"}:
            cta_options = [
                "Save this framework for your next content sprint.",
                "Comment your niche and I’ll map a custom version.",
                "Follow for more practical playbooks."
            ]

        music_options = [
            "Upbeat trending instrumental",
            "Low-fi beat with clear rhythm",
            "Genre match based on current trend velocity"
        ]

        variant_key = f"{topic}|{tone_key}|{audience}|{grounding_line}"
        return {
            "title": f"{topic.title()} Playbook for {audience.title()}",
            "hook": self._pick_variant(hooks, f"hook:{variant_key}"),
            "body": body_lines,
            "cta": self._pick_variant(cta_options, f"cta:{variant_key}"),
            "duration": "45-60 seconds",
            "music_recommendation": self._pick_variant(music_options, f"music:{variant_key}")
        }
    
    def generate_multi_part_series(self, topic, parts=5):
        """Generate multi-part video series"""
        scripts = []
        for i in range(parts):
            scripts.append({
                "part": i + 1,
                "title": f"{topic} - Part {i + 1}",
                "hook": f"Part {i + 1} gets CRAZIER..."
            })
        return scripts
    
    def generate_hashtags(self, topic, tone="balanced", target_audience="general", media_grounding=None):
        """Generate viral hashtags for a topic"""
        normalized_topic = self._sanitize_topic(topic).lower()
        topic_tag = "#" + re.sub(r"[^a-z0-9]+", "", normalized_topic)[:MAX_TOPIC_HASHTAG_LENGTH]
        tone_tag = "#" + re.sub(r"[^a-z0-9]+", "", str(tone or "balanced").lower())[:MAX_TONE_HASHTAG_LENGTH]
        audience_tag = "#" + re.sub(r"[^a-z0-9]+", "", str(target_audience or "general").lower())[:MAX_AUDIENCE_HASHTAG_LENGTH]

        tags = [
            topic_tag if len(topic_tag) > 1 else "#content",
            tone_tag if len(tone_tag) > 1 else "#balanced",
            audience_tag if len(audience_tag) > 1 else "#generalcreator",
            "#creatorstrategy",
            "#fyp",
            "#tiktoktips"
        ]
        deduped = []
        seen = set()
        for tag in tags:
            if tag not in seen:
                deduped.append(tag)
                seen.add(tag)
        return deduped

    def generate_captions(self, topic, tone="balanced", target_audience="general", media_grounding=None):
        """Generate caption options for a topic"""
        normalized_topic = self._sanitize_topic(topic)
        audience = self._sanitize_text(target_audience, max_len=48) or "general audience"
        grounding_line = self._build_grounding_line(media_grounding)
        base = [
            f"Built this {normalized_topic} format for {audience}.",
            f"A cleaner way to approach {normalized_topic} without fluff.",
            f"{normalized_topic} ideas you can apply on your next post."
        ]
        if grounding_line:
            base = [
                f"Using cues from the upload: {grounding_line}",
                f"Media-grounded take on {normalized_topic} for {audience}.",
                f"Turned this media context into a practical {normalized_topic} concept."
            ]
        return base

    def get_viral_hooks(self):
        """Get proven viral hook templates"""
        return [
            "You won't BELIEVE...",
            "This SHOCKED me...",
            "POV: You just discovered...",
            "Nobody talks about...",
            "Wait till the end..."
        ]
