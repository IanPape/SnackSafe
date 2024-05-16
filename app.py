from flask import Flask, session, request, render_template, redirect, url_for, jsonify, flash
from flask_login import login_user, logout_user, login_required, LoginManager, UserMixin, current_user
from flask_migrate import Migrate
from extensions import db
from urllib.parse import quote
import requests
import logging
from werkzeug.security import generate_password_hash ,check_password_hash
from sqlalchemy.orm.exc import NoResultFound
from urllib.parse import quote, quote_plus
import os

def connect_db(app):
    with app.app_context():
        db.app = app
        db.init_app(app)
        db.create_all()


app = Flask(__name__)

print("DATABASE_URL:", os.getenv("DATABASE_URL"))
print("SECRET_KEY:", os.getenv("SECRET_KEY"))

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql:///snacksafe_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = "yobananaboy"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Importing models after creating the db object
from models import User, UserQuery, SavedProduct, FoodProduct

with app.app_context():
    db.create_all()



# Example session debugging
@app.route('/debug/session')
def debug_session():
    logging.debug('Debug session route accessed')
    # Print session variables for debugging
    app.logger.debug(f"Session Contents: {session}")
    
    # Return session contents as JSON for inspection
    return jsonify(session)


@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            # # Debug print to output hashed password from the database
            # print(f"Hashed Password from DB: {user.password_hash}")

            if user.check_password(password):
                login_user(user)
                print("User logged in successfully.")  # Debugging output
                print(f"Current user ID: {current_user.id}")  # Debugging output
                return redirect(url_for('my_snack_safe'))
            else:
                print("Password incorrect.")  # Debugging output
                flash('Invalid username or password', 'error')
        else:
            print("User not found.")  # Debugging output
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        try:
            # Create a new user instance
            new_user = User(username=username, password_hash=hashed_password)

            # Add the new user to the database
            db.session.add(new_user)
            db.session.commit()

            flash('User registered successfully!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            # Rollback changes on error
            db.session.rollback()
            flash('An error occurred. Please try again later.', 'error')
            logging.error(f"Error during registration: {e}")
        finally:
            # Close the session to release resources
            db.session.close()

    return render_template('register.html')





@app.route('/foodsearch')
def food_search():
        return render_template('foodsearch.html')


@app.route('/search', methods=['POST', 'GET'])
def search():
    # Get food_name, custom_allergen, and allergens from form data or session
    food_name = request.form.get('food_name') or session.get('food_name', '')
    custom_allergen = request.form.get('custom_allergen') or session.get('custom_allergen', '')
    allergens = request.form.getlist('allergens') or session.get('allergens', [])
    if isinstance(allergens, str):  # Convert to list if allergens is a string
        allergens = [allergens]


    # Store food_name, custom_allergen, and allergens in session for persistence
    session['food_name'] = food_name
    session['custom_allergen'] = custom_allergen
    session['allergens'] = allergens

    # Encode parameters for URL
    encoded_food_name = quote(food_name) if food_name else ''
    encoded_custom_allergen = quote(custom_allergen) if custom_allergen else ''
    encoded_allergens = '&'.join([f'allergens={quote(allergen)}' for allergen in allergens])

    # Construct the search URL with encoded parameters
    search_url = f'/search?food_name={encoded_food_name}&custom_allergen={encoded_custom_allergen}&{encoded_allergens}&page='

    # Make API call to search for the FDC ID of the food item including dataType in the query string
    search_api_url = f'https://api.nal.usda.gov/fdc/v1/foods/search?query={encoded_food_name}&dataType=Branded&api_key=PHGHdWaATRJN7epsuUUjSaLGgKRC2eG8lHSVx9Mt'
    search_response = requests.get(search_api_url)
    search_data = search_response.json()

    # Pagination logic
    if 'foods' in search_data:
        foods = search_data['foods']
        safe_foods = []
        for food in foods:
            brand_name = food.get('brandName', '') or food.get('brandOwner', 'Unknown Brand')
            food_info = {
                'brand': brand_name,
                'description': food.get('description', 'Unknown Product'),
                'ingredients': food.get('ingredients', 'Unknown Ingredients'),
                'fdcId': food.get('fdcId', 'Unknown')
            }
            if (not custom_allergen or not contains_allergen(food_info['ingredients'].lower(), custom_allergen.lower())) and not any(
                    contains_allergen(food_info['ingredients'].lower(), allergen.lower()) for allergen in allergens):
                safe_foods.append(food_info)

        # Paginate the safe_foods list
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of items per page
        start = (page - 1) * per_page
        end = start + per_page
        paginated_foods = safe_foods[start:end]

        total = len(safe_foods)
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'has_prev': page > 1,
            'has_next': end < total,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if end < total else None,
            'iter_pages': range(1, total // per_page + 2)
        }

        return render_template('searchresults.html', search_url=search_url, foods=paginated_foods, pagination=pagination)









@app.route('/add_to_snack_safe/<int:fdc_id>', methods=['POST'])
@login_required
def add_to_snack_safe(fdc_id):
    print(f"Route accessed: /add_to_snack_safe/{fdc_id}")
    print(f"Current user ID: {current_user.id}")
    print(f"Product ID: {fdc_id}")

    existing_product = FoodProduct.query.filter_by(fdc_id=fdc_id).first()
    if existing_product:
        saved_product = SavedProduct.query.filter_by(user_id=current_user.id, product_id=existing_product.id).first()
        if saved_product:
            flash('Product already added to Snack Safe!', 'warning')
        else:
            new_saved_product = SavedProduct(user_id=current_user.id, product_id=existing_product.id)
            db.session.add(new_saved_product)
            db.session.commit()
            flash('Product added to Snack Safe!', 'success')
    else:
        # Product not found in your database, make an API call to fetch it
        usda_api_url = f'https://api.nal.usda.gov/fdc/v1/food/{fdc_id}?api_key=PHGHdWaATRJN7epsuUUjSaLGgKRC2eG8lHSVx9Mt'
        response = requests.get(usda_api_url)
        if response.status_code == 200:
            product_data = response.json()
            # Extract relevant data from the API response
            name = product_data.get('description', 'Unknown Product')
            description = product_data.get('ingredients', 'No ingredients listed')
            brand = product_data.get('brandOwner', 'Unknown Brand')
            # Create a new entry in your FoodProduct table
            new_product = FoodProduct(name=name, description=description, brand=brand, fdc_id=fdc_id)
            db.session.add(new_product)
            db.session.commit()
            # Now add the newly created product to the user's snack safe
            new_saved_product = SavedProduct(user_id=current_user.id, product_id=new_product.id)
            db.session.add(new_saved_product)
            db.session.commit()
            flash('Product added to Snack Safe!', 'success')
        else:
            flash('Failed to fetch product details from USDA database!', 'error')

    return redirect(url_for('my_snack_safe'))





@app.route('/my_snack_safe')
@login_required
def my_snack_safe():
    user_id = current_user.id if current_user.is_authenticated else None
    print(f"User ID: {user_id}")  # Debugging output
    if user_id is not None:
        saved_products = get_saved_products(user_id)
        print(f"Saved Products: {saved_products}")  # Debugging output

        return render_template('userSnackSafe.html', saved_products=saved_products)
    else:
        flash('User ID is None. Please log in again.', 'error')
        return redirect(url_for('login'))



@app.route('/remove_product/<int:product_id>', methods=['POST'])
@login_required
def remove_product(product_id):
    product = SavedProduct.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if product:
        db.session.delete(product)
        db.session.commit()
        flash('Product removed from Snack Safe!', 'success')
    else:
        flash('Product not found in Snack Safe!', 'error')

    # Redirect back to the 'my_snack_safe' route after removing the product
    return redirect(url_for('my_snack_safe'))






##################################################### functions###############################################################################

def save_product_to_snack_safe(product_id):
    if current_user.is_authenticated:
        user_id = current_user.id
        saved_product = SavedProduct(user_id=user_id, product_id=product_id)
        db.session.add(saved_product)
        db.session.commit()
        flash('Product added to Snack Safe!', 'success')
        

def get_saved_products(user_id):
    try:
        # Query the SavedProduct table to get the saved product IDs for the given user_id
        saved_products = SavedProduct.query.filter_by(user_id=user_id).all()

        # Get the corresponding FoodProduct objects for each saved product
        products_with_details = []
        for saved_product in saved_products:
            try:
                product = FoodProduct.query.get(saved_product.product_id)
                if product:
                    products_with_details.append(product)
            except NoResultFound:
                # Handle case where no corresponding FoodProduct is found for a saved product
                pass

        return products_with_details
    except Exception as e:
        # Handle any other exceptions or errors
        print(f"Error fetching saved products: {e}")
        return []



def contains_allergen(ingredients, allergen):
    # Check if ingredients is a string
    if not isinstance(ingredients, str):
        return False
    
    # Split ingredients into components based on common separators
    separators = [',', ';', '|']  
    for sep in separators:
        if sep in ingredients:
            components = ingredients.split(sep)
            break
    else:
        # If no separator is found, split by whitespace
        components = ingredients.split()
    
    # Check each component for allergen
    for component in components:
        # Strip leading and trailing whitespace from component
        comp = component.strip()
        # Convert component to lowercase for case-insensitive comparison
        comp_lower = comp.lower()
        # Check if allergen is in component
        if allergen.lower() in comp_lower:
            return True
    
    return False





def get_allergens_for_food(food_id):
    # Make API call to fetch allergens for a specific food item using its FDC ID
    api_url = f'https://api.nal.usda.gov/fdc/v1/food/{food_id}?api_key=PHGHdWaATRJN7epsuUUjSaLGgKRC2eG8lHSVx9Mt'
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        allergens = data.get('allergens', [])
        return [allergen.lower() for allergen in allergens]
    else:
        return []  # Return empty list if allergen data is not available or API call fails



if __name__ == '__main__':
    app.run(debug=True)
