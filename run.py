from app import create_app

app = create_app()

# -------------------- Optional Local Run -------------------- #
if _name_ == "_main_":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
