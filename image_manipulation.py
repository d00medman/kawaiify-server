import io
import os
import numpy as np
from PIL import Image, ImageDraw
import cv2

import helpers

STORAGE_DIRECTORY = 'user-images'
CLOUD_STORAGE_BUCKET = 'steg-interview-project-imstore'



# The nexus method which will apply all desired effects to the image
def add_effects_to_image(file, effects, username, input_filename=None):
    """
    A few improvements would include
    - make the effect list indexed, to allow the user to determine the order in which they're applied?
    - Allow users to upload custom effects
    """
    file_name, pil_image, np_image = add_effect_setup_and_data(file, effects, username, input_filename)

    if 'haar_sparkle' or 'haar_googly' in effects:
        sparkly = 'haar_sparkle' in effects
        googly = 'haar_googly' in effects
        pil_image, np_image = handle_facial_recognition_haar(np_image, sparkly, googly)
    if 'dnn_sparkle' or 'dnn_googly' in effects:
        sparkly = 'dnn_sparkle' in effects
        googly = 'dnn_googly' in effects
        pil_image, np_image = handle_facial_recognition_dnn(np_image, sparkly, googly)
    if 'circle' in effects:
        pil_image, np_image = make_image_circular(pil_image.convert("RGB"))

    cloud_url = helpers.save_image_to_gcloud_bucket(pil_image, file_name)
    # pil_image.save(file_path)
    return cloud_url, file_name

def add_effect_setup_and_data(file, effects, username, image_name=None):
    """
    Performs the initial setup of directories for storing images and returns the different 
    representations needed to add the effects
    """
    if image_name is None:
        image_name = file.filename.split('.')[0]
    else:
        image_name = image_name.replace(' ', '-')
    effect_list = '-'.join(effects)
    file_name = f'{image_name}_{effect_list}_{username}.png'
    # file_path = os.path.join(STORAGE_DIRECTORY, file_name)

    # PIL: Python Imaging Library, the library which actually changes the file passed in
    pil_image = Image.open(file).convert("RGB")
    # NP: numpy, a representation which acts as a go-between for PIL and OpenCV
    np_image = np.array(pil_image)
    return file_name, pil_image, np_image

def handle_facial_recognition_dnn(np_image, sparkly_face=False, anime_eyes=False):
    """
    Uses openCV's Dynamic Neural Net (DNN) with an established set of weights to locate faces,
    Then apply the selected effects to those faces.
  
    If no faces are located, it will behave appropriately
    """
    model_file = "res10_300x300_ssd_iter_140000.caffemodel"
    config_file = "deploy.prototxt.txt"
    net = cv2.dnn.readNetFromCaffe(config_file, model_file)
    img = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    height, width = img.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(img, (300, 300)),
        1.0,
        (300, 300),
        (104.0, 117.0, 123.0)
    )
    net.setInput(blob)
    faces = net.forward() 
    # A boolean flag to direct us if there are no faces present in the image
    no_faces_in_image = True
    image = Image.fromarray(np_image)
    for i in range(faces.shape[2]):
        confidence = faces[0, 0, i, 2]
        if confidence > 0.25:
            no_faces_in_image = False
            
            if sparkly_face:
                box = faces[0, 0, i, 3:7] * np.array([width, height, width, height])
                (x, y, x1, y1) = box.astype("int")
                face = image.convert("RGBA").crop((x, y, x1, y1))
                sparkly_face = perform_alpha_composite(face, "effects/sparkles.png")
                image.paste(sparkly_face, (x, y))
            if anime_eyes:
                box = faces[0, 0, i, 3:7] * np.array([width, height, width, height])
                (x, y, x1, y1) = box.astype("int")
                # eyes are about 3/4 of the way up the face, so we target the top 1/4 of the face
                face = image.convert("RGBA").crop((x, y, x1, y1 * 0.75))
                googly_face = perform_alpha_composite(face, "effects/anime_eyes_2.png")
                image.paste(googly_face, (x, y))
    
    if no_faces_in_image:
        return add_sparkles_to_whole_image(np_image)

    pil_image = image.convert("RGBA")
    return pil_image, np.array(pil_image)


def handle_facial_recognition_haar(np_image, sparkly_face=False, anime_eyes=False):
    """
    I implemented haar first, then found from my research that haar is outdated and I'd be better suited using DNN, That said, I'm pretty loathe to take out
    more or less good code, so I'm calling the methods which use haar 'less accurate' on the front and calling it a day
    """
    casc_path = 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(casc_path)
    img = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Detect faces in the image
    # one potential improvement here would be to iterate on scale factors. Could have the knock on of doubling (to n) up on faces though, An interesting problem, but probably not worth dealing with at the moment
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    if len(faces) < 1:
        return add_sparkles_to_whole_image(np_image)
    
    # The image on which we do detection has its palatte pretty dramatically changed. We don't want this, so use the original
    image = Image.fromarray(np_image)
    for (x, y, width, height) in faces:
        if sparkly_face:
            face = image.convert("RGBA").crop((x, y, x+width, y+height))
            sparkly_face = perform_alpha_composite(face, "effects/sparkles.png")
            image.paste(sparkly_face, (x, y))
        if anime_eyes:
            face = image.convert("RGBA").crop((x, y, x+width, y+(height*0.5)))
            googly_face = perform_alpha_composite(face, "effects/anime_eyes_2.png")
            image.paste(googly_face, (x, y))

    pil_image = image.convert("RGBA")
    return pil_image, np.array(pil_image)

def perform_alpha_composite(layer1, file):
    """
    The alpha composite method transposes the passed file on top of the passed layer
    """
    layer2 = Image.open(file).resize(layer1.size)
    final2 = Image.new("RGBA", layer1.size)
    final2 = Image.alpha_composite(final2, layer1)
    final2 = Image.alpha_composite(final2, layer2)
    return final2

def add_sparkles_to_whole_image(np_image):
    """
    Applies the sparkle effect to an entire image
    """
    layer1 = Image.fromarray(np_image).convert("RGBA")
    pil_image = perform_alpha_composite(layer1, "effects/sparkles.png")
    return pil_image, np.array(pil_image)

def make_image_circular(pil_image):
    """
    Crops an image to be circular
    """
    np_image = np.array(pil_image)
    height, width = pil_image.size

    # Create same size alpha layer with circle
    alpha = Image.new('L', pil_image.size, 0)
    draw = ImageDraw.Draw(alpha)
    draw.pieslice([0, 0, height, width], 0, 360, fill=255)

    # Convert alpha Image to numpy array
    np_alpha = np.array(alpha)

    # Add alpha layer to RGB
    np_image = np.dstack((np_image, np_alpha))
    pil_image = Image.fromarray(np_image)
    return pil_image, np_image
