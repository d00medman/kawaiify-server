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

import middleware


app = Flask(__name__)

# oauth = OAuth(app)

# # TODO: login in its own file
# auth0 = oauth.register(
#     'auth0',
#     client_id='qt7n6UnMAwIUvN0bFaxkCAPiNFbqXNPQ',
#     client_secret='YOUR_CLIENT_SECRET',
#     api_base_url='https://dev-ogr-2kjg.us.auth0.com',
#     access_token_url='https://dev-ogr-2kjg.us.auth0.com/oauth/token',
#     authorize_url='https://dev-ogr-2kjg.us.auth0.com/authorize',
#     client_kwargs={
#         'scope': 'openid profile email',
#     },
# )

# Here we're using the /callback route.
# @app.route('/callback')
# def callback_handling():
#     # Handles response from token endpoint
#     auth0.authorize_access_token()
#     resp = auth0.get('userinfo')
#     userinfo = resp.json()

#     # Store the user information in flask session.
#     session['jwt_payload'] = userinfo
#     session['profile'] = {
#         'user_id': userinfo['sub'],
#         'name': userinfo['name'],
#         'picture': userinfo['picture']
#     }
#     return redirect('/dashboard')

# @app.route('/login')
# def login():
#     return auth0.authorize_redirect(redirect_uri='YOUR_CALLBACK_URL')

# @app.route('/logout')
# def logout():
#     # Clear session stored data
#     session.clear()
#     # Redirect user to logout endpoint
#     params = {'returnTo': url_for('home', _external=True), 'client_id': 'qt7n6UnMAwIUvN0bFaxkCAPiNFbqXNPQ'}
#     return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

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

# class UsersModel(db.Model):
#     """Model for the users table"""
#     __tablename__ = 'users'
#     id = db.Column(db.Integer, primary_key = True)
#     name = db.Column(db.String())
#     pass_phrase = db.Column(db.String())
#     created_date = db.Column(db.DateTime, default=datetime.utcnow)

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
        print(f'email in preview image {email}')
        if email is None:
            response = make_response()
            response.status_code = 401
            return middleware.build_actual_response(response)

        file = request.files['image'] 
        file_location = add_effect_to_image(file, email)
        return middleware.build_actual_response(send_file(file_location, mimetype='image/png'))
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

def add_effect_to_image(file, email):
    today = handle_directory_for_day()
    if today is False:
        return 'error creating storage for this image'

    changed_image = make_image_circular(file)

    # Create the path we're saving this at. While this could be more concise, readability is a solid trump
    image_name = file.filename.split('.')[0]
    file_name = f'{image_name}.png'
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


# Helper function which displays file fields to viewer
def print_file_contents(file):
    file_dict = file.__dict__
    for f in file_dict:
        print(f'{f}: {file_dict[f]}')