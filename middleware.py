from functools import wraps
from flask import make_response
from flask_api import status


# middleware methods for access control; will probably want these in their own file
# TODO: can probably be deleted now that preflight no longer relevant
# def build_preflight_response():
#     response = make_response()
#     response.headers.add("Access-Control-Allow-Origin", "*")
#     response.headers.add('Access-Control-Allow-Headers', "*")
#     response.headers.add('Access-Control-Allow-Methods', "*")
#     return response


# TODO: turn into a decorator. also rename
def add_cors_response_headers(response=None):
    if response is None:
        response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

def handle_response(code):
    response = make_response()
    if code == 401:
        response.status = status.HTTP_401_UNAUTHORIZED
    elif code == 406:
        response.status = status.HTTP_406_NOT_ACCEPTABLE
    elif code == 500:
        response.status = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif code == 502:
        response.status = status.HTTP_502_BAD_GATEWAY
    response.status_code = code
    return add_cors_response_headers(response)