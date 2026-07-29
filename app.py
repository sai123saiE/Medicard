"""
MedCart - Online Medical Store / Medicine Ordering System
B.Tech Final Year Project
Built with Python Flask + SQLAlchemy (SQLite)
"""

import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'medcart.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4 MB uploads

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(300))
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='customer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    medicines = db.relationship('Medicine', backref='category', lazy=True)


class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    manufacturer = db.Column(db.String(150))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    requires_prescription = db.Column(db.Boolean, default=False)
    image_filename = db.Column(db.String(200), default='default_medicine.png')
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def in_stock(self):
        return self.stock > 0


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    medicine = db.relationship('Medicine')

    def subtotal(self):
        return round(self.medicine.price * self.quantity, 2)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    shipping_address = db.Column(db.String(300))
    payment_method = db.Column(db.String(50), default='Cash on Delivery')
    status = db.Column(db.String(30), default='Placed')  # Placed, Packed, Shipped, Delivered, Cancelled
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    medicine_name = db.Column(db.String(150))  # snapshot at time of order
    price = db.Column(db.Float)                # snapshot at time of order
    quantity = db.Column(db.Integer, default=1)

    def subtotal(self):
        return round(self.price * self.quantity, 2)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route('/')
def home():
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)

    medicines_query = Medicine.query
    if query:
        medicines_query = medicines_query.filter(Medicine.name.ilike(f'%{query}%'))
    if category_id:
        medicines_query = medicines_query.filter_by(category_id=category_id)

    medicines = medicines_query.order_by(Medicine.name).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template('home.html', medicines=medicines, categories=categories,
                            query=query, selected_category=category_id)


@app.route('/medicine/<int:medicine_id>')
def medicine_detail(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    return render_template('medicine_detail.html', medicine=medicine)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return redirect(url_for('register'))

        user = User(name=name, email=email, phone=phone, address=address)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


# ---------------------------------------------------------------------------
# Cart routes
# ---------------------------------------------------------------------------
@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = round(sum(item.subtotal() for item in items), 2)
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add/<int:medicine_id>', methods=['POST'])
@login_required
def add_to_cart(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    quantity = request.form.get('quantity', 1, type=int)

    if medicine.stock < 1:
        flash('This medicine is currently out of stock.', 'danger')
        return redirect(url_for('medicine_detail', medicine_id=medicine_id))

    existing = CartItem.query.filter_by(user_id=current_user.id, medicine_id=medicine_id).first()
    if existing:
        existing.quantity += quantity
    else:
        db.session.add(CartItem(user_id=current_user.id, medicine_id=medicine_id, quantity=quantity))

    db.session.commit()
    flash(f'{medicine.name} added to cart.', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_item(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)

    quantity = request.form.get('quantity', 1, type=int)
    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity
    db.session.commit()
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))


# ---------------------------------------------------------------------------
# Checkout / Orders
# ---------------------------------------------------------------------------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('home'))

    total = round(sum(item.subtotal() for item in items), 2)

    if request.method == 'POST':
        address = request.form.get('address', current_user.address)
        payment_method = request.form.get('payment_method', 'Cash on Delivery')

        # Validate stock before placing order
        for item in items:
            if item.quantity > item.medicine.stock:
                flash(f'Not enough stock for {item.medicine.name}.', 'danger')
                return redirect(url_for('cart'))

        order = Order(user_id=current_user.id, total_amount=total,
                       shipping_address=address, payment_method=payment_method)
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        for item in items:
            db.session.add(OrderItem(
                order_id=order.id,
                medicine_id=item.medicine_id,
                medicine_name=item.medicine.name,
                price=item.medicine.price,
                quantity=item.quantity
            ))
            item.medicine.stock -= item.quantity
            db.session.delete(item)

        db.session.commit()
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=order.id))

    return render_template('checkout.html', items=items, total=total)


@app.route('/order/confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template('order_confirmation.html', order=order)


@app.route('/orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.placed_at.desc()).all()
    return render_template('my_orders.html', orders=orders)


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    total_medicines = Medicine.query.count()
    total_orders = Order.query.count()
    total_users = User.query.filter_by(is_admin=False).count()
    low_stock = Medicine.query.filter(Medicine.stock <= 10).all()
    recent_orders = Order.query.order_by(Order.placed_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', total_medicines=total_medicines,
                            total_orders=total_orders, total_users=total_users,
                            low_stock=low_stock, recent_orders=recent_orders)


@app.route('/admin/medicines')
@login_required
@admin_required
def admin_medicines():
    medicines = Medicine.query.order_by(Medicine.name).all()
    return render_template('admin/medicines.html', medicines=medicines)


@app.route('/admin/medicines/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_medicine():
    categories = Category.query.order_by(Category.name).all()

    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form.get('description', '').strip()
        manufacturer = request.form.get('manufacturer', '').strip()
        price = request.form.get('price', type=float)
        stock = request.form.get('stock', type=int)
        category_id = request.form.get('category_id', type=int)
        requires_prescription = 'requires_prescription' in request.form

        image_filename = 'default_medicine.png'
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            image_filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        medicine = Medicine(name=name, description=description, manufacturer=manufacturer,
                             price=price, stock=stock, category_id=category_id,
                             requires_prescription=requires_prescription,
                             image_filename=image_filename)
        db.session.add(medicine)
        db.session.commit()
        flash('Medicine added successfully.', 'success')
        return redirect(url_for('admin_medicines'))

    return render_template('admin/medicine_form.html', categories=categories, medicine=None)


@app.route('/admin/medicines/edit/<int:medicine_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    categories = Category.query.order_by(Category.name).all()

    if request.method == 'POST':
        medicine.name = request.form['name'].strip()
        medicine.description = request.form.get('description', '').strip()
        medicine.manufacturer = request.form.get('manufacturer', '').strip()
        medicine.price = request.form.get('price', type=float)
        medicine.stock = request.form.get('stock', type=int)
        medicine.category_id = request.form.get('category_id', type=int)
        medicine.requires_prescription = 'requires_prescription' in request.form

        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            image_filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            medicine.image_filename = image_filename

        db.session.commit()
        flash('Medicine updated successfully.', 'success')
        return redirect(url_for('admin_medicines'))

    return render_template('admin/medicine_form.html', categories=categories, medicine=medicine)


@app.route('/admin/medicines/delete/<int:medicine_id>')
@login_required
@admin_required
def admin_delete_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    db.session.delete(medicine)
    db.session.commit()
    flash('Medicine deleted.', 'info')
    return redirect(url_for('admin_medicines'))


@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_categories():
    if request.method == 'POST':
        name = request.form['name'].strip()
        if name and not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
            db.session.commit()
            flash('Category added.', 'success')
        return redirect(url_for('admin_categories'))

    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=categories)


@app.route('/admin/categories/delete/<int:category_id>')
@login_required
@admin_required
def admin_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted.', 'info')
    return redirect(url_for('admin_categories'))


@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.placed_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
@admin_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get('status', order.status)
    db.session.commit()
    flash(f'Order #{order.id} status updated to {order.status}.', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Access forbidden.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page not found.'), 404


# ---------------------------------------------------------------------------
# Database seeding helper
# ---------------------------------------------------------------------------
def seed_data():
    """Creates tables and inserts demo data if the database is empty."""
    db.create_all()

    if Category.query.count() == 0:
        cat_names = ['Pain Relief', 'Vitamins & Supplements', 'Cold & Flu',
                     'Diabetes Care', 'Skin Care', 'First Aid']
        categories = [Category(name=n) for n in cat_names]
        db.session.add_all(categories)
        db.session.commit()

    if Medicine.query.count() == 0:
        cats = {c.name: c.id for c in Category.query.all()}
        demo_medicines = [
            ('Paracetamol 500mg', 'Pain and fever relief tablets, strip of 10.',
             'MediCore Pharma', 45.0, 120, False, cats['Pain Relief']),
            ('Ibuprofen 400mg', 'Anti-inflammatory pain relief tablets.',
             'HealWell Labs', 60.0, 80, False, cats['Pain Relief']),
            ('Vitamin C 500mg', 'Immunity booster chewable tablets, 30 count.',
             'NutriLife', 150.0, 60, False, cats['Vitamins & Supplements']),
            ('Multivitamin Capsules', 'Daily multivitamin and mineral supplement.',
             'NutriLife', 220.0, 45, False, cats['Vitamins & Supplements']),
            ('Cough Syrup 100ml', 'Relieves dry and wet cough.',
             'MediCore Pharma', 85.0, 40, False, cats['Cold & Flu']),
            ('Antihistamine Tablets', 'Relief from allergy and cold symptoms.',
             'HealWell Labs', 55.0, 70, False, cats['Cold & Flu']),
            ('Glucometer Strips (25 pack)', 'Blood glucose test strips.',
             'DiaCare', 480.0, 25, False, cats['Diabetes Care']),
            ('Insulin Pen Needles', 'Pack of 30 fine needles for insulin pens.',
             'DiaCare', 350.0, 15, True, cats['Diabetes Care']),
            ('Antiseptic Cream 30g', 'For minor cuts, wounds, and burns.',
             'SkinPure', 95.0, 55, False, cats['Skin Care']),
            ('Moisturizing Lotion 200ml', 'For dry and sensitive skin.',
             'SkinPure', 175.0, 50, False, cats['Skin Care']),
            ('First Aid Kit (Basic)', 'Bandages, antiseptic wipes, gauze, and more.',
             'SafeGuard', 399.0, 20, False, cats['First Aid']),
            ('Digital Thermometer', 'Fast and accurate digital thermometer.',
             'SafeGuard', 249.0, 30, False, cats['First Aid']),
        ]
        for name, desc, mfr, price, stock, presc, cat_id in demo_medicines:
            db.session.add(Medicine(name=name, description=desc, manufacturer=mfr,
                                     price=price, stock=stock,
                                     requires_prescription=presc, category_id=cat_id))
        db.session.commit()

    if User.query.filter_by(email='admin@medcart.com').first() is None:
        admin = User(name='Admin', email='admin@medcart.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(debug=True)
