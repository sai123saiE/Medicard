# MedCart — Online Medical Store (B.Tech Project)

A full-stack web application for ordering medicines online, built with
**Python (Flask)**, **SQLAlchemy**, and **SQLite**.

## Features

**Customer side**
- Register / login (secure password hashing via Werkzeug)
- Browse medicines by category, search by name
- Product detail pages with stock and prescription-required indicators
- Shopping cart: add, update quantity, remove items
- Checkout with shipping address and payment method selection
- Order confirmation and order history

**Admin side** (login: `admin@medcart.com` / `admin123`)
- Dashboard with stats (total medicines, orders, customers, low-stock alerts)
- Add / edit / delete medicines, with image upload
- Manage categories
- View and update order status (Placed → Packed → Shipped → Delivered / Cancelled)
- View registered customers

## Tech Stack

| Layer      | Technology                     |
|------------|---------------------------------|
| Backend    | Python, Flask                   |
| Database   | SQLite via Flask-SQLAlchemy     |
| Auth       | Flask-Login + password hashing  |
| Frontend   | Jinja2 templates, HTML/CSS      |

## Project Structure

```
medcart/
├── app.py                  # All routes, models, and app logic
├── requirements.txt
├── medcart.db               # created automatically on first run
├── static/
│   ├── css/style.css
│   └── uploads/             # medicine images uploaded via admin panel
└── templates/
    ├── base.html
    ├── home.html, login.html, register.html, ...
    └── admin/                # admin panel templates
```

## How to Run

1. **Install Python 3.9+** if not already installed.

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```
   On first run, the database is created automatically and seeded with
   sample categories, 12 demo medicines, and an admin account.

5. **Open in browser:** http://127.0.0.1:5000

## Default Accounts

| Role     | Email                | Password  |
|----------|----------------------|-----------|
| Admin    | admin@medcart.com    | admin123  |
| Customer | *(register your own)* | —       |

## Database Schema (for your project report)

- **User** — id, name, email, phone, address, password_hash, is_admin
- **Category** — id, name
- **Medicine** — id, name, description, manufacturer, price, stock,
  requires_prescription, image_filename, category_id
- **CartItem** — id, user_id, medicine_id, quantity
- **Order** — id, user_id, total_amount, shipping_address, payment_method, status, placed_at
- **OrderItem** — id, order_id, medicine_id, medicine_name, price, quantity
  *(name/price are snapshotted so past orders don't change if a medicine's price changes later)*

## Ideas for Extending This Project (for extra viva marks)

- Prescription upload for Rx-required medicines (file upload + admin approval step)
- Email notifications on order placement / status change (Flask-Mail)
- Payment gateway integration (Razorpay/Stripe test mode)
- Wishlist / favorites
- Product reviews and ratings
- REST API version using Flask-RESTful for a mobile app frontend
- Deployment to Render/Railway/PythonAnywhere with PostgreSQL instead of SQLite

## Notes

- This uses Flask's built-in development server (`debug=True`), which is
  fine for a college project/demo but should never be used in production.
- The `SECRET_KEY` in `app.py` should be replaced with a random value if
  you ever deploy this beyond a local demo.
