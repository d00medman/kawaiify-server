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
import cv2


# imports from files in this project
import middleware


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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class ImageModel(db.Model):
    """Model for the images table"""
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key = True)
    file_path = db.Column(db.String())
    file_name = db.Column(db.String())
    # users_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    creator_email = db.Column(db.String(), index=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, file_name, file_path, creator_email):
        self.file_name = file_name
        self.file_path = file_path
        self.creator_email = creator_email

@app.errorhandler(middleware.AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

@app.route("/get-image/<id>", methods=["GET"])
def get_image(id):
    print(id)
    id = int(id)

    if id == -1:
        print('hola mundo')
        result = ImageModel.query.first()
        print(result)

        all_rows = ImageModel.query.all()
        max_image_id = len(all_rows)
        header_list = "image_id,image_name,max_image_id"
    else:
        result = ImageModel.query.get(id)
        header_list = "image_id,image_name" 
    try:
        file_location = os.path.join(result.file_path, result.file_name)
    except TypeError:
        print('type error in building file path')
        return middleware.build_actual_response(jsonify('no data'))
    
    response = send_file(file_location, mimetype='image/png')
    response.headers.add("Access-Control-Expose-Headers", header_list)
    response.headers['image_id'] = result.id
    response.headers['image_name'] = result.file_name
    if id == -1:
        response.headers['max_image_id'] = max_image_id
    return middleware.build_actual_response(response)


# Preview and upload are essentially the same for the moment, need to clarify this terminology
@app.route("/preview-image", methods=["POST"])
def preview_image():
    if request.method == 'OPTIONS':
        return middleware.build_preflight_response()
    elif request.method == 'POST': 
        email = request.form['email']
        # print(email)
        if email is None:
            response = make_response()
            response.status_code = 401
            return middleware.build_actual_response(response)

        file = request.files['image']
        file_location = handle_facial_recognition_dnn(file, email)
        # file_location = add_effect_to_image(file, email)
        return middleware.build_actual_response(send_file(file_location, mimetype='image/png'))
    return 'This should not be hit?'

# TODO: add auth0 authentication. Pretty minor, but would be better than the pseudo-authentication I'm currently doing
@app.route("/get-my-image-data/<username>", methods=["GET"])
def get_my_image_data(username):
    # print('hallo weld')
    if username is None:
        return 'this endpoint needs an email'
    # for some reason, the baseQuery object recovered by the filter does not mesh with standard iterable operations
    user_images = [i for i in ImageModel.query.filter(ImageModel.creator_email == username)]
    if len(user_images) < 1:
        # in this case, the user has not added filters to any images
        return middleware.build_actual_response({[]})
    start_image = user_images[0]
    # TODO: Essentially identical to get_image, should thus be encapsulated
    file_location = os.path.join(start_image.file_path, start_image.file_name)
    user_image_ids = [str(image.id) for image in user_images]
    print(user_image_ids)
    response = send_file(file_location, mimetype='image/png')
    response.headers.add("Access-Control-Expose-Headers", "user_image_id_list,image_name,image_id")
    # going to transmit the user IDs to the client as a comma separated list
    response.headers['user_image_id_list'] = ",".join(user_image_ids)
    response.headers['image_name'] = start_image.file_name
    response.headers['image_id'] = start_image.id
    return middleware.build_actual_response(response)

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

def add_effect_to_image(file, email):
    today = handle_directory_for_day()
    if today is False:
        return 'error creating storage for this image'

    changed_image = make_image_circular(file)

    # Create the path we're saving this at. While this could be more concise, readability is a solid trump
    image_name = file.filename.split('.')[0]
    file_name = f'{image_name}_circular.png'
    file_path = os.path.join(today, file_name)

    if os.path.exists(file_path) is False:
        record_saved_image_location(file_name, today, email)

    Image.fromarray(changed_image).save(file_path)
    return file_path

# Store in db for easy usage
def record_saved_image_location(file_name, file_path, creator_email):
    new_image = ImageModel(file_name=file_name, file_path=file_path, creator_email=creator_email)
    db.session.add(new_image)
    db.session.commit()

# Methods for image manipulation also likely belong in their own home
def make_image_circular(file):
    img = Image.open(file).convert("RGB")
    np_image = np.array(img)
    h, w = img.size

    # Create same size alpha layer with circle
    alpha = Image.new('L', img.size,0)
    draw = ImageDraw.Draw(alpha)
    draw.pieslice([0,0,h,w],0,360,fill=255)

    # Convert alpha Image to numpy array
    np_alpha = np.array(alpha)

    # Add alpha layer to RGB
    np_image = np.dstack((np_image, np_alpha))
    return np_image

# TODO: coalesce these two similar functions into one single function
def handle_facial_recognition_dnn(file, email):
    today = handle_directory_for_day()
    if today is False:
        return 'error creating storage for this image'

    # Create the path we're saving this at. While this could be more concise, readability is a solid trump
    image_name = file.filename.split('.')[0]
    file_name = f'{image_name}.png'
    # file_path = os.path.join(today, file_name)

    image_name = file.filename.split('.')[0]
    file_name = f'{image_name}_face_rec.png'
    file_path = os.path.join(today, file_name)

    img = Image.open(file).convert("RGB")
    np_image = np.array(img)

    # Image.fromarray(np_image).save(file_path)
    modelFile = "res10_300x300_ssd_iter_140000.caffemodel"
    configFile = "deploy.prototxt.txt"
    net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
    img = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0,
    (300, 300), (104.0, 117.0, 123.0))
    net.setInput(blob)
    faces = net.forward()
    #to draw faces on image
    print(faces.shape[2])
    # A boolean flag to direct us if there are no faces present in the image
    no_faces = True
    image = Image.fromarray(np_image)
    for i in range(faces.shape[2]):
            confidence = faces[0, 0, i, 2]
            # print(confidence)
            if confidence > 0.25:
                no_faces = False
                box = faces[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x1, y1) = box.astype("int")
                face = image.convert("RGBA").crop((x, y, x1, y1))
                # face.show()
                sparkly_face = perform_alpha_composite(face, "effects/sparkles.png")
                image.paste(sparkly_face, (x, y))
                # cv2.rectangle(img, (x, y), (x1, y1), (0, 0, 255), 2)
    
    if no_faces:
        return add_sparkles_to_whole_image(img, file_path)

    image.convert("RGBA").save(file_path)
    return file_path

def handle_facial_recognition_haar(file, email):
    today = handle_directory_for_day()
    if today is False:
        return 'error creating storage for this image'

    # Create the path we're saving this at. While this could be more concise, readability is a solid trump
    image_name = file.filename.split('.')[0]
    file_name = f'{image_name}.png'
    # file_path = os.path.join(today, file_name)

    image_name = file.filename.split('.')[0]
    file_name = f'{image_name}_face_rec.png'
    file_path = os.path.join(today, file_name)

    img = Image.open(file).convert("RGB")
    np_image = np.array(img)

    # Image.fromarray(np_image).save(file_path)

    casc_path = 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(casc_path)
    # image = cv2.imread(file_path)
    image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    # TODO: find some way to retain the color
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect faces in the image
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    print(type(faces))
    # TODO: error handling; roll me back if the image save fails
    if os.path.exists(file_path) is False:
        record_saved_image_location(file_name, today, email)
    # If there are no faces, add sparkles to everything
    if len(faces) < 1:
        return add_sparkles_to_whole_image(image, file_path)
    else:
        # Draw a rectangle around the faces
        print(f'detected {len(faces)} faces')
        # The image on which we do detection has its colors pretty dramatically changed. We don't want this, so use the original
        image = Image.fromarray(np_image)
        for (x, y, w, h) in faces:
            face = image.convert("RGBA").crop((x, y, x+w, y+h))
            sparkly_face = perform_alpha_composite(face, "effects/sparkles.png")
            image.paste(sparkly_face, (x, y))
            
            # image.show()
        image.convert("RGBA").save(file_path)
            # image

            # cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
    # Image.fromarray(image).save(file_path)
    # image.save(file_path, "PNG")
    return file_path

def perform_alpha_composite(layer1, file):
    layer2 = Image.open(file).resize(layer1.size)
    # print(f'layer 1: {layer1.size} layer 2: {layer2.size}')
    final2 = Image.new("RGBA", layer1.size)
    final2 = Image.alpha_composite(final2, layer1)
    final2 = Image.alpha_composite(final2, layer2)
    return final2

def add_sparkles_to_whole_image(image, file_path):
    # print('no faces found, add sparkles')
    layer1 = Image.fromarray(image).convert("RGBA")
    final2 = perform_alpha_composite(layer1, "effects/sparkles.png") 
    print(type(final2))
    final2.save(file_path)
    return file_path


# Helper function which displays file fields to viewer
def print_file_contents(file):
    file_dict = file.__dict__
    for f in file_dict:
        print(f'{f}: {file_dict[f]}')