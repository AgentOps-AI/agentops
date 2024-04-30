from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/data', methods=['POST'])
def mock_data():
    return jsonify({
        'data': 'mock data'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
