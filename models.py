from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from sqlalchemy.orm import relationship

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(300), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    fdc_id = db.Column(db.Integer)
    saved_products = relationship('SavedProduct', backref='owner', lazy=True, cascade='all, delete-orphan', overlaps="owner,saved_products")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        hashed_password = self.password_hash  # Get hashed password from the database
        is_correct = check_password_hash(hashed_password, password)
        return is_correct

class FoodProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    brand = db.Column(db.String(100))
    ingredients = db.Column(db.Text)
    fdc_id = db.Column(db.Integer)
    dataType = db.Column(db.String(50))

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class UserQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    user = db.relationship('User', backref='queries', lazy=True, cascade='all, delete-orphan', single_parent=True)
    fdc_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('food_product.id'))
    product = db.relationship('FoodProduct', backref='associated_query')

    def get_product_details(self):
        if self.product:
            return {
                'brand': self.product.brand,
                'description': self.product.description,
                'ingredients': self.product.ingredients,
                'fdc_id': self.product.fdc_id
            }
        else:
            return None
    
    @classmethod
    def get_saved_products(cls, user_id):
        session = db.session
        return session.query(cls).filter(cls.user_id == user_id).all()

class SavedProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('food_product.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('products', lazy=True, cascade='all, delete-orphan', overlaps="owner, saved_products"))
    product = db.relationship('FoodProduct', backref=db.backref('saved_by_users', lazy=True))

