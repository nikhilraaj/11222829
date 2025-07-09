from flask import Flask, request, jsonify, redirect, abort
from datetime import datetime, timedelta
import re
import string
import random

app = Flask(__name__)

# In-memory data storage
url_store = {}  # key: shortcode, value: dict with 'url', 'expiry', 'clicks'

@app.before_request
def log_request():
    with open('request_logs.txt', 'a') as log_file:
        log_file.write(f"{datetime.utcnow().isoformat()} - {request.method} {request.url} - Body: {request.get_data(as_text=True)}\n")

def generate_shortcode(length=6):
    charset = string.ascii_letters + string.digits
    while True:
        shortcode = ''.join(random.choices(charset, k=length))
        if shortcode not in url_store:
            return shortcode

url_regex = re.compile(
    r'^(https?:\/\/)'  # http:// or https://
    r'(([\w\-]+\.)+[\w]{2,})'  # domain
    r'([\w\-\.\/~%]*)*$',  # optional path
    re.IGNORECASE
)

def is_valid_url(url):
    return re.match(url_regex, url) is not None

@app.route('/shorturls', methods=['POST'])
def create_short_url():
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({"error": "Missing 'url' field."}), 400

    original_url = data['url']
    if not is_valid_url(original_url):
        return jsonify({"error": "Invalid URL format."}), 400

    validity = int(data.get('validity', 30))
    shortcode = data.get('shortcode')

    if shortcode:
        if not re.match(r'^[a-zA-Z0-9]{1,20}$', shortcode):
            return jsonify({"error": "Shortcode must be alphanumeric and up to 20 characters."}), 400
        if shortcode in url_store:
            return jsonify({"error": "Shortcode already exists."}), 409
    else:
        shortcode = generate_shortcode()

    expiry_time = datetime.utcnow() + timedelta(minutes=validity)
    url_store[shortcode] = {
        'url': original_url,
        'expiry': expiry_time,
        'clicks': 0
    }

    return jsonify({
        "shortLink": f"http://localhost:5000/{shortcode}",
        "expiry": expiry_time.isoformat() + 'Z'
    }), 201

@app.route('/<shortcode>', methods=['GET'])
def redirect_url(shortcode):
    record = url_store.get(shortcode)
    if not record:
        return jsonify({"error": "Shortcode not found."}), 404

    if datetime.utcnow() > record['expiry']:
        return jsonify({"error": "Short link has expired."}), 410

    record['clicks'] += 1
    return redirect(record['url'], code=302)

@app.route('/shorturls/<shortcode>', methods=['GET'])
def get_stats(shortcode):
    record = url_store.get(shortcode)
    if not record:
        return jsonify({"error": "Shortcode not found."}), 404

    return jsonify({
        "originalURL": record['url'],
        "expiry": record['expiry'].isoformat() + 'Z',
        "clicks": record['clicks']
    }), 200

if __name__ == '__main__':
    app.run(debug=True)