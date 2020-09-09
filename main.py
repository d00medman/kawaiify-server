from flask import Flask, request, redirect, make_response, jsonify, send_file
import logging
from flask_cors import CORS, cross_origin

import numpy as np
from PIL import Image, ImageDraw

app = Flask(__name__)
# CORS(app, support_credentials=True)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('HELLO WORLD')

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route("/preview-image", methods=["POST"])
# @cross_origin(supports_credentials=True)
def preview_image():
    if request.method == 'OPTIONS':
        print('hallo weld')
        return build_preflight_response()
    elif request.method == 'POST': 
        print('hola mundo')

        file = request.files['image'] 
        make_image_circular(file)
        return build_actual_response(send_file('out.png', mimetype='image/png'))
    return 'This should not be hit?'

# Methods for image manipulation also likely belong in their own home
def make_image_circular(file):
    print(file)
    img = Image.open(file).convert("RGB")
    npImage = np.array(img)
    h,w = img.size

    # Create same size alpha layer with circle
    alpha = Image.new('L', img.size,0)
    draw = ImageDraw.Draw(alpha)
    draw.pieslice([0,0,h,w],0,360,fill=255)

    # Convert alpha Image to numpy array
    npAlpha=np.array(alpha)

    # Add alpha layer to RGB
    npImage=np.dstack((npImage,npAlpha))

    # Save with alpha
    Image.fromarray(npImage).save('out.png')

# middleware methods for access control; will probably want these in their own file
def build_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

def build_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response