from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import os

app = Flask(__name__)
app.secret_key = "yt_secret"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        link = request.form["link"]
        ss = request.form["ss"]
        to = request.form["to"]
        output = request.form["output"]
        
        if not link or not ss or not to or not output:
            flash("Please fill in all fields", "error")
            return redirect(url_for("index"))

        cmd = f"python youtube.py -L \"{link}\" -ss {ss} -to {to} -O {output}"
        try:
            subprocess.run(cmd, shell=True, check=True)
            flash(f"Download completed: {output}", "success")
        except subprocess.CalledProcessError as e:
            flash("Error while downloading video.", "error")

        return redirect(url_for("index"))

    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6000))
    app.run(debug=True, host='0.0.0.0', port=port)
