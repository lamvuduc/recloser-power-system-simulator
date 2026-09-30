import os
from flask import Flask, render_template, request, jsonify
from simulation import simulate

app = Flask(__name__)

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/simulate")
def api_simulate():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(simulate(data))
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
