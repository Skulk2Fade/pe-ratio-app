from stockapp import create_app
import os

app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0").lower() in ["1", "true", "yes"]
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
