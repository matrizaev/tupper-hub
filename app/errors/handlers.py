from flask import render_template, request
from app.errors import bp
from app import db


@bp.app_errorhandler(404)
def NotFoundError(error):
	return render_template('errors/404.html'), 404
	
	
@bp.app_errorhandler(500)
def InternalError(error):
	db.session.rollback()
	return render_template('errors/500.html'), 500