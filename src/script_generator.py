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

    def generate_full_content_pack(
        self,
        topic,
        tone="balanced",
        target_audience="general",
        media_grounding=None,
        script=None,
        hashtags=None,
        captions=None
    ):
        """Generate a complete ready-to-produce TikTok content pack."""
        normalized_topic = self._sanitize_topic(topic)
        audience = self._sanitize_text(target_audience, max_len=48) or "general audience"
        tone_key = self._sanitize_text(tone, max_len=24).lower() or "balanced"
        grounding_line = self._build_grounding_line(media_grounding)
        variant_key = f"{normalized_topic}|{tone_key}|{audience}|{grounding_line}"

        hook_options = [
            f"Stop scrolling: this is the fastest way to improve your {normalized_topic} results.",
            f"Most creators miss this {normalized_topic} move—here's the fix in 30 seconds.",
            f"If your {normalized_topic} content is stuck, use this simple 3-step reset."
        ]
        if grounding_line:
            hook_options = [
                f"Your uploaded media revealed this key angle: {grounding_line}",
                f"Built directly from your media signals: {grounding_line}",
                f"Based on the content you uploaded, this is the strongest hook: {grounding_line}"
            ]

        selected_hook = self._pick_variant(hook_options, f"pack_hook:{variant_key}")
        effective_script = script if isinstance(script, dict) else self.generate_script(
            normalized_topic,
            tone=tone,
            target_audience=target_audience,
            media_grounding=media_grounding
        )

        shot_list = [
            {
                "scene": 1,
                "duration_seconds": "0-3",
                "shot": "Tight close-up, direct eye contact, quick movement into frame",
                "purpose": "Pattern interrupt + hook delivery"
            },
            {
                "scene": 2,
                "duration_seconds": "3-12",
                "shot": "Medium shot with gesture to key prop or screen",
                "purpose": f"Introduce core {normalized_topic} problem for {audience}"
            },
            {
                "scene": 3,
                "duration_seconds": "12-25",
                "shot": "Over-the-shoulder demo or before/after visual",
                "purpose": "Show practical solution steps"
            },
            {
                "scene": 4,
                "duration_seconds": "25-35",
                "shot": "B-roll montage with quick cuts synced to beat",
                "purpose": "Reinforce key takeaways and outcomes"
            },
            {
                "scene": 5,
                "duration_seconds": "35-45",
                "shot": "Return to talking head, confident CTA delivery",
                "purpose": "Drive comments, saves, and follows"
            }
        ]

        on_screen_text = [
            {"scene": 1, "text": selected_hook},
            {"scene": 2, "text": f"Why most {normalized_topic} posts underperform"},
            {"scene": 3, "text": "Step 1 → Step 2 → Step 3"},
            {"scene": 4, "text": "Do this today for faster results"},
            {"scene": 5, "text": "Save this + follow for next part"}
        ]

        body_lines = effective_script.get("body", [])
        if isinstance(body_lines, list):
            body_text = " ".join([self._sanitize_text(line, max_len=220) for line in body_lines if line]).strip()
        else:
            body_text = self._sanitize_text(body_lines, max_len=500)
        cta_line = self._sanitize_text(effective_script.get("cta", ""), max_len=180)
        voiceover_lines = [selected_hook, body_text, cta_line]
        voiceover_script = "\n\n".join([line for line in voiceover_lines if line]).strip()

        editing_notes = [
            "Keep cuts every 1.0-1.8s in first 10 seconds to protect retention.",
            "Use punch-in zoom on key claim and each step transition.",
            "Add subtitles with high contrast and safe margins for mobile UI overlays.",
            "Sync beat drops to scene transitions and CTA line.",
            "Color-grade for warm skin tones and slightly boosted contrast."
        ]

        base_hashtags = hashtags if isinstance(hashtags, list) and hashtags else self.generate_hashtags(
            normalized_topic,
            tone=tone,
            target_audience=target_audience,
            media_grounding=media_grounding
        )
        cta_variants = [
            "Comment your niche and I’ll give you a custom version.",
            "Save this and use it before your next upload.",
            "Follow for more creator-tested short-form frameworks."
        ]
        if tone_key in {"fun", "playful", "casual"}:
            cta_variants = [
                "Drop a 🔥 if you want part 2.",
                "Duet this with your version and tag me.",
                "Save this cheat code for your next post."
            ]

        caption_final = ""
        if isinstance(captions, list) and captions:
            caption_final = self._sanitize_text(captions[0], max_len=260)
        if not caption_final:
            caption_final = f"{selected_hook} {cta_variants[0]}"
        tags_line = " ".join([self._sanitize_text(tag, max_len=36) for tag in base_hashtags if tag]).strip()
        if tags_line:
            caption_final = (caption_final + "\n\n" + tags_line).strip()

        thumbnail_text = self._pick_variant([
            f"{normalized_topic.title()} in 45s",
            f"Fix Your {normalized_topic.title()} Hook",
            "Use This Viral Format"
        ], f"thumb:{variant_key}")

        return {
            "video_concept": f"Fast, actionable {normalized_topic} breakdown tailored for {audience}.",
            "hook_options": hook_options[:3],
            "shot_list": shot_list,
            "on_screen_text": on_screen_text,
            "voiceover_script": voiceover_script,
            "editing_notes": editing_notes,
            "caption_final": caption_final,
            "hashtags": base_hashtags,
            "thumbnail_text": thumbnail_text,
            "cta_variants": cta_variants[:3]
        }

    def get_viral_hooks(self):
        """Get proven viral hook templates"""
        return [
            "You won't BELIEVE...",
            "This SHOCKED me...",
            "POV: You just discovered...",
            "Nobody talks about...",
            "Wait till the end..."
        ]
