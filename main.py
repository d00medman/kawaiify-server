import os
from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import cross_origin
# imports from files in this project
import middleware as mw
import image_manipulation as imman
import db
import helpers

app = Flask(__name__)

# app.config['DEBUG'] = True

@app.route("/get-all-images", methods=["GET"])
def get_all_images():
    image_list = db.get_images_for_list()
    image_list = helpers.append_file_data_to_request_objects(image_list)
    return mw.add_cors_response_headers(jsonify(image_list))

@app.route("/get-my-image-data/<user_email>", methods=["GET"])
def get_my_image_data(user_email):
    """
    Gets the list of all images for the user's email sent up
    """
    if user_email is None:
        return mw.handle_response(401)
    image_list = db.get_images_for_list(user_email)
    image_list = helpers.append_file_data_to_request_objects(image_list)
    return mw.add_cors_response_headers(jsonify(image_list))


@app.route("/get-image/<image_id>", methods=["GET"])
def get_image(image_id):
    """
    Recover a single image and its relevant data
    """
    # print(f'image id in get_image {image_id}')
    image_id = int(image_id)
    display_name, image_creator, file_name = db.get_image_by_id(image_id)
    file_location = os.path.join(imman.STORAGE_DIRECTORY, file_name)

    response = send_file(file_location, mimetype='image/png')
    response.headers.add("Access-Control-Expose-Headers", "image_name,image_creator")
    response.headers['image_creator'] = image_creator
    response.headers['image_name'] = display_name
    return mw.add_cors_response_headers(response)


# Preview and upload are essentially the same for the moment, need to clarify this terminology
@app.route("/upload-image", methods=["POST"])
@cross_origin(headers=["Content-Type", "Authorization"])
@mw.requires_auth
def upload_image():
    """
    Applies all selected effects to the uploaded image, saves said image to both the file system and
    the database, then returns relevant information to the user for assessment
    """
    email = request.form['email']
    if email is None:
        return mw.handle_response(401, False)
    file = request.files['image']
    input_filename = None if request.form['file_name'] == '' else request.form['file_name']
    print(f'input filename: {input_filename}')
    effects = request.form['effects'].split(',')
    if len(effects) < 1:
        return mw.handle_response(406, False)
    file_location, file_name = imman.add_effects_to_image(file, effects, email, input_filename)

    if os.path.exists(file_location) is True:
        display_name = file_name if input_filename is None else input_filename
        image_id = db.insert_image(file_name, email, display_name)
        if image_id is False:
            return mw.handle_response(500, False)

    response = send_file(file_location, mimetype='image/png')
    response.headers.add("Access-Control-Expose-Headers", "image_id")
    response.headers['image_id'] = image_id
    return response

@app.route("/delete-my-image-data/<image_id>", methods=["GET"])
@cross_origin(headers=["Content-Type", "Authorization"])
@mw.requires_auth
def delete_my_image(image_id):
    """
    I am using a get route because once we delete an image, we are going to need to return updated
    data
    """
    image_id = int(image_id)
    print(image_id)
    file_name = db.delete_image(image_id)
    if file_name is False:
        return mw.handle_response(500, False)
    file_location = os.path.join(imman.STORAGE_DIRECTORY, file_name)
    os.remove(file_location)
    return make_response()

@app.route("/report-image/<image_id>", methods=["GET"])
def report_image(image_id):
    """
    Reports an image, which will not delete the image, but will prevent it from appearing in list
    requests to the GUI.

    This is a stub which could be expanded to handle the uploading of obscene content
    """
    image_id = int(image_id)
    if db.report_image(image_id) is False:
        return mw.handle_response(500)
    return mw.add_cors_response_headers()

# Code from the auth0 setup guide
@app.errorhandler(mw.AuthError)
def handle_auth_error(ex):
    """
    Handles authorization errors
    """
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response