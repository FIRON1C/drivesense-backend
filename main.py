from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

# In-memory event storage (replace with database in production)
events_storage = []

@app.route('/api/events', methods=['GET'])
def get_events():
    """Retrieve all recorded events"""
    return jsonify(events_storage), 200

@app.route('/api/events', methods=['POST'])
def post_events():
    """Submit new event data"""
    try:
        data = request.json
        if isinstance(data, list):
            events_storage.extend(data)
        else:
            events_storage.append(data)
        return jsonify({"status": "success", "count": len(events_storage)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/quality', methods=['GET'])
def get_quality():
    """Get road quality metrics"""
    if not events_storage:
        return jsonify({"quality": 0, "segments": []}), 200
    
    potholes = len([e for e in events_storage if e.get('type') == 'POTHOLE'])
    bumps = len([e for e in events_storage if e.get('type') == 'BUMP'])
    total = len(events_storage)
    
    quality_score = max(0, 10 - (potholes * 2 + bumps * 0.5))
    
    return jsonify({
        "quality": quality_score,
        "potholes": potholes,
        "bumps": bumps,
        "total": total
    }), 200

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))  # Railway sets PORT=8080 by default
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
