import io
from google.cloud import storage

import image_manipulation as imman

def get_blob(file_name):
    """
    Gets the blob for the file passed in gcloud
    """
    gcs = storage.Client()
    bucket = gcs.get_bucket(imman.CLOUD_STORAGE_BUCKET)
    return bucket.blob(file_name)

def save_image_to_gcloud_bucket(pil_image, file_name):
    """
    Converts a PIL image into a buffer, then uses this buffer to save the image to gcloud
    """
    buf = io.BytesIO()
    pil_image.save(buf, format='PNG')
    byte_im = buf.getvalue()

    blob = get_blob(file_name)
    blob.upload_from_string(byte_im, content_type='image/png')
    return blob.public_url

def delete_image_from_gcloud_bucket(file_name):
    """
    Exactly what it says
    """
    blob = get_blob(file_name)
    blob.delete()