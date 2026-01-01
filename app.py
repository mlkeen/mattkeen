from flask import Flask, render_template, send_from_directory

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

@app.get("/robots.txt")
def robots_txt():
    return send_from_directory(app.static_folder, "robots.txt", mimetype="text/plain")

@app.get("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(app.static_folder, "sitemap.xml", mimetype="application/xml")

@app.get("/health")
def health():
    return {"ok": True}
