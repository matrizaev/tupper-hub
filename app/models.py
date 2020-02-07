from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from flask import url_for
from app.ecwid import EcwidAPI
from datetime import datetime

@login.user_loader
def load_user(id):
	return User.query.get(int(id))
	
class User(UserMixin, db.Model):
	id  = db.Column(db.Integer, primary_key = True)
	email	= db.Column(db.String(120), index = True, unique = True, nullable=False)
	password = db.Column(db.String(128), nullable=False)
	stores = db.relationship('Store', backref = 'user')
	partners_key = db.Column(db.String(128), nullable=False)
	client_id = db.Column(db.String(128), nullable=False)
	client_secret = db.Column(db.String(128), nullable=False)
	hub_id = db.Column(db.Integer, unique = True, nullable=False)
	token = db.Column(db.String(128), nullable=False)
	orders_date = db.Column(db.DateTime,nullable=False, default=datetime.utcnow)
	
	def __repr__ (self):
		return '<User {}>'.format(self.email)
	
	def SetPassword(self, password):
		self.password = generate_password_hash(password)
		
	def CheckPassword(self, password):
		return check_password_hash(self.password, password)
		
	def GetAvatar(self, size):
		digest = md5(self.email.lower().encode('utf-8')).hexdigest()
		return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)
	
	def GetEcwidAPI(self):
		return EcwidAPI(self.partners_key, self.client_id, self.client_secret)


class Store(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	token = db.Column(db.String(128), nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	orders_count = db.Column(db.Integer, nullable=False, default = 0, server_default='0')
	
