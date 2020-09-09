from flask import Flask, request, redirect, make_response, jsonify, send_file
from flask_cors import CORS, cross_origin
from datetime import datetime, date
import os

import numpy as np
from PIL import Image, ImageDraw
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import base64
import functools


app = Flask(__name__)

# TODO: db initialization and access into discrete file
POSTGRES = {
    'user': 'postgres',
    'pw': 'password',
    'db': 'steg',
    'host': 'localhost',
    'port': '5432',
}

app.config['DEBUG'] = True

# Db initialization
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class ImageModel(db.Model):
    """Model for the images table"""
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key = True)
    directory = db.Column(db.String())
    name = db.Column(db.String())

    def __init__(self, name, directory):
        self.name = name
        self.directory = directory

@app.route("/get-image/<id>", methods=["GET"])
def get_image(id):
    # print(id)
    id = int(id)

    if id == -1:
        result = ImageModel.query.first()
        all_rows = ImageModel.query.all()
        max_image_id = len(all_rows)
        header_list = "image_id,image_name,max_image_id"
    else:
        result = ImageModel.query.get(id)
        header_list = "image_id,image_name"

    file_location = os.path.join(result.directory, result.name)

    response = send_file(file_location, mimetype='image/png')
    response.headers.add("Access-Control-Expose-Headers", header_list)
    response.headers['image_id'] = result.id
    response.headers['image_name'] = result.name
    if id == -1:
        response.headers['max_image_id'] = max_image_id
    
    return build_actual_response(response)


# Preview and upload are essentially the same for the moment, need to clarify this terminology
@app.route("/preview-image", methods=["POST"])
def preview_image():
    if request.method == 'OPTIONS':
        return build_preflight_response()
    elif request.method == 'POST': 
        file = request.files['image'] 
        file_location = add_effect_to_image(file)
        return build_actual_response(send_file(file_location, mimetype='image/png'))
    return 'This should not be hit?'

def handle_directory_for_day():
    # today = str(datetime.date(datetime.datetime.now()))
    today = str(date.today())
    if os.path.exists(today) is False:
        try:
            os.makedirs(today)
        except Exception as e:
            print(f'error creating directory {today}: {e}')
            return False
    return today

def add_effect_to_image(file):
    today = handle_directory_for_day()
    if today is False:
        return 'error creating storage for this image'

    changed_image = make_image_circular(file)

    # Create the path we're saving this at. While this could be more concise, readability is a solid trump
    image_name = file.filename.split('.')[0]
    file_name = f'{image_name}.png'
    file_path = os.path.join(today, file_name)

    Image.fromarray(changed_image).save(file_path)

    record_saved_image_location(file_name, today)
    
    return file_path

# Store in db for easy usage
def record_saved_image_location(file_name, directory):
    new_image = ImageModel(name=file_name, directory=directory)
    db.session.add(new_image)
    db.session.commit()

# Methods for image manipulation also likely belong in their own home
def make_image_circular(file):
    img = Image.open(file).convert("RGB")
    npImage = np.array(img)
    h,w = img.size

    # Create same size alpha layer with circle
    alpha = Image.new('L', img.size,0)
    draw = ImageDraw.Draw(alpha)
    draw.pieslice([0,0,h,w],0,360,fill=255)

    # Convert alpha Image to numpy array
    npAlpha = np.array(alpha)

    # Add alpha layer to RGB
    npImage = np.dstack((npImage,npAlpha))
    return npImage


# middleware methods for access control; will probably want these in their own file
def build_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response


# todo: turn into a decorator
def build_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# Helper function which displays file fields to viewer
def print_file_contents(file):
    file_dict = file.__dict__
    for f in file_dict:
        print(f'{f}: {file_dict[f]}')