from flask import Flask, render_template

app = Flask(__name__)

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/resume")
def resume():
    return render_template("resume.html")

@app.get("/papers")
def papers():
    return render_template("papers.html")

@app.get("/hobbies")
def hobbies():
    return render_template("hobbies.html")

@app.get("/health")
def health():
    return {"ok": True}
