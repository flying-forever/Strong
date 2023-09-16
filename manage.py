from strong import create_app
app = create_app()
app.run(host='0.0.0.0', port=3002, debug=True)
