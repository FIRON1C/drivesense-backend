from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///drivesense.db')

# Fix 'postgres' vs 'postgresql' issue automatically just in case
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)

# Database Model for Road Events
class RoadEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    magnitude = db.Column(db.Float)
    time = db.Column(db.String(100))

# Create tables if they don't exist, with schema check and drop/recreation if columns are missing
with app.app_context():
    try:
        db.create_all()
        # Verify schema is up-to-date
        RoadEvent.query.filter_by(magnitude=1.0).first()
    except Exception as e:
        print("Schema mismatch or missing column in drivesense database, recreating tables...", e)
        try:
            db.drop_all()
            db.create_all()
        except Exception as drop_err:
            print("Failed to drop and recreate database:", drop_err)

@app.route('/')
def home():
    return {
        "status": "online",
        "database": "Connected to Neon",
        "info": "DriveSense Backend v2"
    }

# In-memory event storage (fallback / legacy support)
events_storage = []

@app.route('/api/upload', methods=['POST'])
def upload_data():
    """Batch upload endpoint for mobile app buffer-and-sync"""
    try:
        data = request.get_json() or {}
        events = data.get('events', [])
        
        for e in events:
            new_event = RoadEvent(
                event_type=e.get('type') or e.get('event_type'),
                lat=float(e['lat']),
                lng=float(e['lng']),
                magnitude=float(e.get('mag') or e.get('magnitude', 0)),
                time=e.get('time')
            )
            db.session.add(new_event)
            # Add to legacy events_storage for local compatibility
            events_storage.append({
                'type': new_event.event_type,
                'lat': new_event.lat,
                'lng': new_event.lng,
                'magnitude': new_event.magnitude,
                'time': new_event.time
            })
            
        db.session.commit()
        return jsonify({"status": "success", "synced": len(events)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/events', methods=['GET'])
def get_events():
    """Retrieve all recorded events from database"""
    try:
        events = RoadEvent.query.all()
        events_list = [{
            'id': e.id,
            'type': e.event_type,
            'lat': e.lat,
            'lng': e.lng,
            'magnitude': e.magnitude or 0.0,
            'time': e.time or datetime.now().isoformat()
        } for e in events]
        return jsonify(events_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/events', methods=['POST'])
def post_events():
    """Submit new event data to database"""
    try:
        data = request.json or {}
        if isinstance(data, list):
            events = data
        else:
            events = [data]
            
        for e in events:
            new_event = RoadEvent(
                event_type=e.get('type') or e.get('event_type'),
                lat=float(e['lat']),
                lng=float(e['lng']),
                magnitude=float(e.get('magnitude') or e.get('mag', 0)),
                time=e.get('time')
            )
            db.session.add(new_event)
            events_storage.append(e)
            
        db.session.commit()
        return jsonify({"status": "success", "count": len(events_storage)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/quality', methods=['GET'])
def get_quality():
    """Get road quality metrics from database events"""
    try:
        events = RoadEvent.query.all()
        if not events:
            return jsonify({"quality": 10.0, "potholes": 0, "bumps": 0, "total": 0}), 200
        
        potholes = len([e for e in events if e.event_type == 'POTHOLE'])
        bumps = len([e for e in events if e.event_type == 'BUMP'])
        total = len(events)
        
        quality_score = max(0.0, 10.0 - (potholes * 2.0 + bumps * 0.5))
        
        return jsonify({
            "quality": round(quality_score, 1),
            "potholes": potholes,
            "bumps": bumps,
            "total": total
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))  # Railway sets PORT=8080 by default
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
