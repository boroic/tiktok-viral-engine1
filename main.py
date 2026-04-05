from flask import Flask, jsonify, request
import os

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({"status":"ok","service":"tiktok-viral-engine1"}), 200

@app.get("/health")
def health():
    return jsonify({"status":"ok"}), 200

@app.post("/run")
def run():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "viral_trends")
    return jsonify({
        "status": "success",
        "message": "Pipeline trigger endpoint works",
        "topic": topic
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
