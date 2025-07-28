# web/socketio_app.py
import os
from web import create_app
from flask_socketio import SocketIO

app = create_app()
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app, message_queue=os.getenv("REDIS_URL"))

if __name__ == "__main__":
    # enable debug=True here
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=True    # ← add this
    )
