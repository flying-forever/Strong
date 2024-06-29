from strong import create_app, socketio

app = create_app()
port = app.config['PORT']

# app.run(host='0.0.0.0', port=port, debug=True)
socketio.run(app=app, host='0.0.0.0', port=port, debug=True)
