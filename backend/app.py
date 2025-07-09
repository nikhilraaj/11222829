from flask import Flask, request, jsonify, redirect
from datetime import datetime, timedelta, timezone
import string
import random
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# In-memory database
url_store = {}  # shortcode: {url, expiry, clicks, creation_time, click_details}

# Middleware-based logging (custom, not using logging module)
@app.before_request
def log_request():
    with open('request_logs.txt', 'a') as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {request.method} {request.path} - {request.get_data(as_text=True)}\n")

# Utility functions
def generate_shortcode(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        if code not in url_store:
            return code

def is_valid_url(url):
    regex = re.compile(
        r'^(https?:\/\/)'  # http:// or https://
        r'(([\w\-]+\.)+[\w]{2,})'  # domain
        r'([\w\-\.\/~%]*)*$',
        re.IGNORECASE
    )
    return re.match(regex, url) is not None

# API: Create Short URL
@app.route('/shorturls', methods=['POST'])
def create_short_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Missing required 'url' field."}), 400

    url = data['url']
    validity = data.get('validity', 30)
    shortcode = data.get('shortcode')

    if not is_valid_url(url):
        return jsonify({"error": "Invalid URL format."}), 400

    try:
        validity = int(validity)
    except:
        return jsonify({"error": "Validity must be an integer."}), 400

    if shortcode:
        if not re.fullmatch(r'^[a-zA-Z0-9]{1,20}$', shortcode):
            return jsonify({"error": "Shortcode must be alphanumeric and up to 20 characters."}), 400
        if shortcode in url_store:
            return jsonify({"error": "Shortcode already exists."}), 409
    else:
        shortcode = generate_shortcode()

    expiry = datetime.now(timezone.utc) + timedelta(minutes=validity)
    url_store[shortcode] = {
        'url': url,
        'expiry': expiry,
        'creation_time': datetime.now(timezone.utc),
        'clicks': 0,
        'click_details': []
    }

    return jsonify({
        "shortLink": f"http://localhost:5000/{shortcode}",
        "expiry": expiry.isoformat() + 'Z'
    }), 201

# API: Redirect
@app.route('/<shortcode>', methods=['GET'])
def redirect_short_url(shortcode):
    entry = url_store.get(shortcode)
    if not entry:
        return jsonify({"error": "Shortcode not found."}), 404

    if datetime.utcnow() > entry['expiry']:
        return jsonify({"error": "Short link has expired."}), 410

    # Track click
    entry['clicks'] += 1
    entry['click_details'].append({
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'source': request.headers.get('Referer', 'unknown'),
        'location': request.remote_addr  # coarse-grained
    })

    return redirect(entry['url'], code=302)

# API: Get Statistics for a Short URL
@app.route('/shorturls/<shortcode>', methods=['GET'])
def get_short_url_stats(shortcode):
    entry = url_store.get(shortcode)
    if not entry:
        return jsonify({"error": "Shortcode not found."}), 404

    return jsonify({
        "shortLink": f"http://localhost:5000/{shortcode}",
        "originalURL": entry['url'],
        "creationTime": entry['creation_time'].isoformat() + 'Z',
        "expiry": entry['expiry'].isoformat() + 'Z',
        "clicks": entry['clicks'],
        "clickDetails": entry['click_details']
    }), 200

# API: Get All Short URLs (For URL Statistics Page)
@app.route('/shorturls', methods=['GET'])
def get_all_short_urls():
    result = []
    for code, entry in url_store.items():
        result.append({
            "shortLink": f"http://localhost:5000/{code}",
            "originalURL": entry['url'],
            "creationTime": entry['creation_time'].isoformat() + 'Z',
            "expiry": entry['expiry'].isoformat() + 'Z',
            "clicks": entry['clicks']
        })
    return jsonify(result), 200

if __name__ == '__main__':
    app.run(debug=True)
