import os
from datetime import date

import numpy as np
from PIL import Image, ImageDraw
import cv2

import middleware

# The nexus method which will apply all desired effects to the image
def add_effects_to_image(file, effects):
    file_path, pil_image, np_image = add_effect_setup_and_data(file, effects)
    # TODO: maybe make the list indexed, to allow the user to determine the order in which they're applied?
    if 'haar_sparkle' in effects:
        pil_image, np_image = handle_facial_recognition_haar(np_image)
    if 'dnn_sparkle' in effects:
        pil_image, np_image = handle_facial_recognition_dnn(np_image)
    if 'circle' in effects:
        pil_image, np_image = make_image_circular(pil_image.convert("RGB"))

    pil_image.save(file_path)
    # Image.fromarray(changed_image).save(file_path)
    return file_path

def handle_directory_for_day():
    today = str(date.today())
    if os.path.exists(today) is False:
        try:
            os.makedirs(today)
        except Exception as exception:
            print(f'error creating directory {today}: {exception}')
            return False
    return today

# Performs the initial setup of directories for storing images and returns the different representations needed to add the effects
def add_effect_setup_and_data(file, effects):
    today = handle_directory_for_day()
    if today is False:
        return middleware.handle_response(500)

    # Create the path we're saving this at. While this could be more concise, readability is a solid trump
    image_name = file.filename.split('.')[0]
    effect_list = '-'.join(effects)
    file_name = f'{image_name}_{effect_list}.png'
    file_path = os.path.join(today, file_name)

    # PIL: Python Imaging Library, the library which actually changes the file passed in
    pil_image = Image.open(file).convert("RGB")
    # NP: numpy, a representation which acts as a go-between for PIL and OpenCV
    np_image = np.array(pil_image)
    return file_path, pil_image, np_image

def handle_facial_recognition_dnn(np_image):
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
    #to draw faces on image
    print(faces.shape[2])
    # A boolean flag to direct us if there are no faces present in the image
    no_faces_in_image = True
    image = Image.fromarray(np_image)
    for i in range(faces.shape[2]):
            confidence = faces[0, 0, i, 2]
            if confidence > 0.25:
                no_faces_in_image = False
                box = faces[0, 0, i, 3:7] * np.array([width, height, width, height])
                (x, y, x1, y1) = box.astype("int")
                face = image.convert("RGBA").crop((x, y, x1, y1))
                sparkly_face = perform_alpha_composite(face, "effects/sparkles.png")
                image.paste(sparkly_face, (x, y))
    
    if no_faces_in_image:
        return add_sparkles_to_whole_image(np_image)

    pil_image = image.convert("RGBA")
    return pil_image, np.array(pil_image)

def handle_facial_recognition_haar(np_image):
    casc_path = 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(casc_path)
    image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Detect faces in the image
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    if len(faces) < 1:
        return add_sparkles_to_whole_image(image)
    else:
        # The image on which we do detection has its palatte pretty dramatically changed. We don't want this, so use the original
        image = Image.fromarray(np_image)
        for (x, y, w, h) in faces:
            face = image.convert("RGBA").crop((x, y, x+w, y+h))
            sparkly_face = perform_alpha_composite(face, "effects/sparkles.png")
            image.paste(sparkly_face, (x, y))

    pil_image = image.convert("RGBA")
    return pil_image, np.array(pil_image)

def perform_alpha_composite(layer1, file):
    layer2 = Image.open(file).resize(layer1.size)
    final2 = Image.new("RGBA", layer1.size)
    final2 = Image.alpha_composite(final2, layer1)
    final2 = Image.alpha_composite(final2, layer2)
    return final2

def add_sparkles_to_whole_image(np_image):
    layer1 = Image.fromarray(np_image).convert("RGBA")
    pil_image = perform_alpha_composite(layer1, "effects/sparkles.png")
    return pil_image, np.array(pil_image)

def make_image_circular(pil_image):
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