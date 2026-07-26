import os
import json
import re

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, IntegerField
from flask_uploads import configure_uploads, UploadSet, UploadNotAllowed
from flask_executor import Executor

import pdfgenerator
import mail
import ml_gen
import speedometer_gen
import heat_map_gen
import bar_graphs
import tcl

load_dotenv()

app = Flask(__name__, static_url_path="/static")
# Falls back to a dev-only value locally, but you should always set
# FLASK_SECRET_KEY in production (see .env.example).
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-only-change-me')
app.config['UPLOADED_PHOTOS_DEST'] = 'static/uploads'

# Make sure the folders the app writes to actually exist
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('static/outputs', exist_ok=True)

images = UploadSet('photos', ('jpg', 'png'))
configure_uploads(app, images)

executor = Executor(app)

# Cache the chatbot chain so we don't rebuild embeddings / reload the
# vector DB on every single chat message.
_qa_chain = None


def get_chatbot_chain():
    global _qa_chain
    if _qa_chain is None:
        if not os.path.exists(tcl.vectordb_file_path):
            tcl.create_vector_db()
        vectordb = tcl.load_vector_db()
        _qa_chain = tcl.get_qa_chain(vectordb)
    return _qa_chain


class UploadForm(FlaskForm):
    name = StringField('name')
    gender = StringField('gender')
    email = StringField('email')
    age = IntegerField("age")
    image = FileField('image')


EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b')


def validateEmail(email):
    return bool(email) and EMAIL_REGEX.fullmatch(email) is not None


def validateAge(age):
    return age is not None and age in range(1, 101)


@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    if form.validate_on_submit():
        name = form.name.data
        gender = form.gender.data
        age = form.age.data
        email = form.email.data

        if not validateEmail(email):
            flash("Wrong E-Mail Format!")
            return redirect(url_for('index'))

        if not validateAge(age):
            flash("Please enter your correct age!")
            return redirect(url_for('index'))

        try:
            filename = images.save(form.image.data)
        except UploadNotAllowed:
            flash("Filetype not supported! Upload JPEGS!")
            return redirect(url_for('index'))

        ext = os.path.splitext(filename)[1]
        target_path = f"static/uploads/input{ext}"

        # Remove any stale upload from a previous session (either extension)
        for old_ext in (".jpg", ".png"):
            old_path = f"static/uploads/input{old_ext}"
            if os.path.exists(old_path) and old_path != target_path:
                os.remove(old_path)
        if os.path.exists(target_path):
            os.remove(target_path)

        os.rename(f"static/uploads/{filename}", target_path)

        op = {
            'name': name,
            'age': age,
            'gender': gender,
            'email': email,
            'filename': f"/static/uploads/input{ext}",
        }
        with open("static/input.json", "w") as op_file:
            json.dump(op, op_file, indent=4)

        ml_gen.predict(op['filename'][1:])
        return redirect(url_for('result'))

    return render_template("Page1.html", form=form)


@app.route('/result')
def result():
    with open('static/output.json') as file_op:
        op = json.load(file_op)
    with open('static/input.json') as file_ip:
        ip = json.load(file_ip)

    # Use whichever extension was actually uploaded, instead of assuming .jpg
    image_path = (
        "static/uploads/input.png"
        if os.path.exists("static/uploads/input.png")
        else "static/uploads/input.jpg"
    )

    bar_graphs.generate(image_path)
    heat_map_gen.generate(image_path)
    speedometer_gen.generate(image_path)
    pdfgenerator.generate_pdf(
        "static/input.json",
        "static/output.json",
        image_path,
        "static/outputs/heatmap.png",
        "static/outputs/bar_graph.png",
        "static/outputs/speedometers.png",
        "static/media/logoXray.png",
    )

    executor.submit(mail.sendMail, ip['email'])
    return render_template("xray.html", content={'input': ip, 'output': op})


@app.route('/get', methods=['GET'])
def get_response():
    userTxt = request.args.get('usrMsg', '').strip()
    if not userTxt:
        return "Please enter a question."

    chain_instance = get_chatbot_chain()
    return tcl.ask_question(chain_instance, userTxt)


if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, threaded=True)
