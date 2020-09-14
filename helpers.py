import base64
import os

import image_manipulation as imman

def append_file_data_to_request_objects(image_list):
    """
    Appends file binary data to the object which will be sent to the client to display to users
    """
    for image in image_list:
        file_location = os.path.join(imman.STORAGE_DIRECTORY, image['fileName'])
        with open(file_location, "rb") as image_file:
            image['fileData'] = base64.b64encode(image_file.read()).decode()
    return image_list
