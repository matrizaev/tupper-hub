from flask import current_app
from flask_httpauth import HTTPBasicAuth
from app.api.errors import ErrorResponse
from flask import g
from app.models import User

basic_auth = HTTPBasicAuth()

@basic_auth.verify_password
def verify_password(username, password):
	user = User.query.filter_by(username=username).first()
	if user is None:
			return False
	return user.CheckPassword(password)

@basic_auth.error_handler
def basic_auth_error():
	return ErrorResponse(401)