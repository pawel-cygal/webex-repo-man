# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Note: In a Docker environment, Flask's built-in server is fine for development.
    # For production, a proper WSGI server like Gunicorn would be used,
    # and this block would not be executed. Gunicorn is included in requirements.txt.
    app.run(host='0.0.0.0', port=5000, debug=True)
