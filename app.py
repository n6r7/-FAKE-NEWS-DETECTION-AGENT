from flask import Flask, request, jsonify, render_template
import threading
from fake_news_agent import train_and_evaluate, analyze_news

app = Flask(__name__, template_folder='templates', static_folder='static')

MODEL = {"agent": None}

def load_model():
    print("⏳ Loading BERT Model...")
    try:
        agent = train_and_evaluate()
        MODEL["agent"] = agent
        print("✅ Model Ready and Loaded!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")

threading.Thread(target=load_model, daemon=True).start()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/check", methods=["POST"])
def check_news():
    if MODEL["agent"] is None:
        return jsonify({"status": "loading", "message": "Model is still loading..."}), 202

    data = request.json
    text = data.get("text", "")
    source = data.get("source", "")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        result = analyze_news(MODEL["agent"], text, source)
        return jsonify(result)
    except Exception as e:
        print(f"Analysis Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)