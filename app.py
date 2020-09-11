import os

from flask import Flask, request, send_file
# TODO: delete me once cors is confirmed stable
# from flask_cors import CORS, cross_origin
from datetime import datetime, date


from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import functools


# imports from files in this project
import middleware
import image_manipulation


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


@app.route("/get-image/<image_id>", methods=["GET"])
def get_image(image_id):
    print(image_id)
    image_id = int(image_id)

    if image_id == -1:
        print('hola mundo')
        result = ImageModel.query.first()
        print(result)

        all_rows = ImageModel.query.all()
        max_image_id = len(all_rows)
        header_list = "image_id,image_name,max_image_id"
    else:
        result = ImageModel.query.get(image_id)
        header_list = "image_id,image_name"
    try:
        file_location = os.path.join(result.file_path, result.file_name)
    except TypeError:
        print('type error in building file path')
        return middleware.handle_response(500)
    
    response = send_file(file_location, mimetype='image/png')
    response.headers.add("Access-Control-Expose-Headers", header_list)
    response.headers['image_id'] = result.id
    response.headers['image_name'] = result.file_name
    if image_id == -1:
        response.headers['max_image_id'] = max_image_id
    return middleware.add_cors_response_headers(response)


# Preview and upload are essentially the same for the moment, need to clarify this terminology
@app.route("/preview-image", methods=["POST"])
def preview_image():
    email = request.form['email']
    if email is None:
        return middleware.handle_response(401)
    file = request.files['image']
    effects = request.form['effects'].split(',')
    if len(effects) < 1:
        return middleware.handle_response(406)
    file_location = image_manipulation.add_effects_to_image(file, effects)
    # file_location = add_effect_to_image(file, email)
    return middleware.add_cors_response_headers(send_file(file_location, mimetype='image/png'))

# TODO: add auth0 authentication. Pretty minor, but would be better than the pseudo-authentication I'm currently doing
@app.route("/get-my-image-data/<username>", methods=["GET"])
def get_my_image_data(username):
    if username is None:
        return middleware.handle_response(401)
    start_image, user_image_ids = get_user_initialization_data(username)
    if start_image is False:
         return middleware.add_cors_response_headers()
    file_location = os.path.join(start_image.file_path, start_image.file_name)
    response = send_file(file_location, mimetype='image/png')
    response.headers.add("Access-Control-Expose-Headers", "user_image_id_list,image_name,image_id")
    # going to transmit the user IDs to the client as a comma separated list
    response.headers['user_image_id_list'] = user_image_ids
    response.headers['image_name'] = start_image.file_name
    response.headers['image_id'] = start_image.id
    return middleware.add_cors_response_headers(response)

"""
DB methods. I'd prefer to have these in a separate file, but the pattern I've selected has made this tricky to do without inducing a circular dependency
"""
class ImageModel(db.Model):
    """Model for the images table"""
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key = True)
    file_path = db.Column(db.String())
    file_name = db.Column(db.String())
    creator_email = db.Column(db.String(), index=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, file_name, file_path, creator_email):
        self.file_name = file_name
        self.file_path = file_path
        self.creator_email = creator_email

def get_user_initialization_data(username):
    user_images = [i for i in ImageModel.query.filter(ImageModel.creator_email == username)]
    if len(user_images) < 1:
        # in this case, the user has not added filters to any images. Return false for controller to handle
        return False, False
    user_image_ids = [str(image.id) for image in user_images]
    return user_images[0], ",".join(user_image_ids)

# Store in db for easy usage
def record_saved_image_location(file_name, file_path, creator_email):
    new_image = ImageModel(file_name=file_name, file_path=file_path, creator_email=creator_email)
    db.session.add(new_image)
    db.session.commit()


# Helper function which displays file fields to viewer
# TODO: delete me, really just here for my debugging purposes
def print_file_contents(file):
    file_dict = file.__dict__
    for f in file_dict:
        print(f'{f}: {file_dict[f]}')