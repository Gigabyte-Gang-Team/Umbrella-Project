from flask import Flask, redirect, url_for, render_template, request, jsonify, make_response, session
from pymongo import MongoClient
import requests
from datetime import datetime, timedelta
import hashlib
import re
from bson import ObjectId
from bson.objectid import ObjectId, InvalidId
import jwt.exceptions
import jwt 
from functools import wraps
from werkzeug.utils import secure_filename

import os
from os.path import join, dirname
from dotenv import load_dotenv

import certifi

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
db = client[DB_NAME]

SECRET_KEY = os.environ.get("SECRET_KEY")
TOKEN_KEY = os.environ.get("TOKEN_KEY")

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def home():
#   navbar profile
    token_receive = request.cookies.get(TOKEN_KEY)
    user_info = None

    if token_receive:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.users.find_one({'email': payload.get('id')})
        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            pass

    is_logged_in = 'user_id' in session or user_info is not None
#   navbar profile end
    
    best_products = db.products.find().sort('total_pembelian', -1).limit(3)
    products = list(db.products.find({}))
    unique_categories = {}
    for product in products:
        category = product['kategori_produk']
        if category not in unique_categories:
            unique_categories[category] = product

    # Mengubah hasil menjadi daftar
    kategori_produk = list(unique_categories.values())
    
    return render_template('home.html', best_products=best_products, kategori_produk=kategori_produk, is_logged_in=is_logged_in, user_info=user_info)

@app.route('/search', methods=['GET'])
def search():
    #   navbar profile
    token_receive = request.cookies.get(TOKEN_KEY)
    user_info = None

    if token_receive:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.users.find_one({'email': payload.get('id')})
        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            pass

    is_logged_in = 'user_id' in session or user_info is not None
    #   navbar profile end
    query = request.args.get('query', '')
    regex = re.compile(f".*{query}.*", re.IGNORECASE)
    search_results_cursor = db.products.find({"nama_produk": regex})
    search_results = list(search_results_cursor)
    return render_template('search_results.html', products=search_results, query=query, is_logged_in=is_logged_in, user_info=user_info)

# Nonaktifkan caching di setiap request
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    return response

@app.route('/login', methods=['GET'])
def login():
    msg = request.args.get('msg')
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('home')))
    resp.delete_cookie(TOKEN_KEY)
    return resp

@app.route("/sign_in", methods=["POST"])
def sign_in():
    email_receive = request.form["email_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one({
        "email": email_receive,
        "password": pw_hash,
    })
    if result:
        payload = {
            "id": email_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        resp = make_response(jsonify({"result": "success", "token": token}))
        resp.set_cookie(TOKEN_KEY, token, httponly=True, samesite='Lax')
        return resp
    else:
        return jsonify({"result": "fail", "msg": "We could not find a user with that id/password combination"})

# Halaman yang dilindungi
@app.route('/protected')
def protected():
    token = request.cookies.get(TOKEN_KEY)
    if not token:
        return redirect(url_for('login', msg="You need to log in first"))

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # Jika token valid, render halaman yang dilindungi
        return render_template('protected.html')
    except jwt.ExpiredSignatureError:
        return redirect(url_for('login', msg="Session expired. Please log in again."))
    except jwt.InvalidTokenError:
        return redirect(url_for('login', msg="Invalid token. Please log in again."))

@app.route('/register', methods=['GET'])
def register():
    msg = request.args.get('msg')
    return render_template('register.html', msg=msg)

@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form['username_give']
    email_receive = request.form['email_give']
    contact_receive = request.form['contact_give']
    address_receive = request.form['address_give']
    password_receive = request.form['password_give']
    
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    
    doc = {
        "username": username_receive,                               
        "email": email_receive,                                     
        "contact": contact_receive,                                 
        "address": address_receive,                                 
        "password": password_hash,                                  
        "profile_name": username_receive,                           
        "profile_pic": "",                                          
        "profile_pic_real": "profile_pics/profile_placeholder.png", 
        "profile_info": ""                                          
    }
    
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/sign_up/check_usn', methods=['POST'])
def check_usn():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/sign_up/check_email', methods=['POST'])
def check_email():
    email_receive = request.form['email_give']
    exists = bool(db.users.find_one({"email": email_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/about')
#fungsi tidak wajib login
def about():
    token_receive = request.cookies.get(TOKEN_KEY)
    user_info = None

    if token_receive:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.users.find_one({'email': payload.get('id')})
        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            pass

    is_logged_in = 'user_id' in session or user_info is not None

    return render_template('about.html', is_logged_in=is_logged_in, user_info=user_info)


# Products, Detail & All Start
@app.route('/products')
def products():
    #   navbar profile
    token_receive = request.cookies.get(TOKEN_KEY)
    user_info = None

    if token_receive:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.users.find_one({'email': payload.get('id')})
        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            pass

    is_logged_in = 'user_id' in session or user_info is not None
    #   navbar profile end
    product = list(db.products.find({}).sort("created_at", -1))

    best_selling_products = db.products.find().sort("total_pembelian", -1)

    return render_template('products.html', product=product, best_selling_products=best_selling_products, is_logged_in=is_logged_in, user_info=user_info)

@app.route('/all-products')
def all_products():
    #   navbar profile
    token_receive = request.cookies.get(TOKEN_KEY)
    user_info = None

    if token_receive:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.users.find_one({'email': payload.get('id')})
        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            pass

    is_logged_in = 'user_id' in session or user_info is not None
    #   navbar profile end
    sort_option = request.args.get('sort')
    filter_category = request.args.get('filter')

    query = {}

    # Ambil semua produk yang sesuai dengan kategori
    if filter_category:
        products = list(db.products.find({"kategori_produk": filter_category}))
        query['kategori_produk'] = filter_category    
    else:
        products = list(db.products.find({}))

    sort_criteria = [('created_at', -1)]  # Default sorting is by recent products
    if sort_option == 'best_selling':
        sort_criteria = [('total_pembelian', -1)]

    # Ambil produk dari database dengan filter dan urutkan sesuai kriteria
    products = list(db.products.find(query).sort(sort_criteria))

    return render_template('all-products.html', products=products, is_logged_in=is_logged_in, user_info=user_info)

@app.route('/detail-product/<product_id>')
def detail_product(product_id):
    #   navbar profile
    token_receive = request.cookies.get(TOKEN_KEY)
    user_info = None

    if token_receive:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.users.find_one({'email': payload.get('id')})
        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            pass

    is_logged_in = 'user_id' in session or user_info is not None
    #   navbar profile end
    
    product = db.products.find_one({"_id": ObjectId(product_id)})
    if product:
        product['_id'] = str(product['_id'])  # Mengubah ObjectId menjadi string untuk Jinja template
    else:
        return "Product not found", 404
    
    if product and "ulasan_produk" in product:
        ulasan_produk = product["ulasan_produk"]
        ulasan_count = len(ulasan_produk)
        total_rating = 0

        for ulasan in ulasan_produk:
            try:
                # Pastikan ulasan[2] adalah angka
                rating = int(ulasan[2])
                total_rating += rating
            except ValueError:
                print(f"Invalid rating value: {ulasan[2]}")

        average_rating = total_rating / ulasan_count if ulasan_count > 0 else 0
    else:
        ulasan_produk = []
        ulasan_count = 0
        average_rating = 0

    # Tambahkan average_rating ke data product
    product["average_rating"] = average_rating
    product["ulasan_count"] = ulasan_count

    # Untuk Sorting recent review dipaling atas
    product["ulasan_produk"] = product["ulasan_produk"][::-1]

    # Tambahkan query untuk mengurutkan berdasarkan total pembelian
    best_selling_products = db.products.find().sort("total_pembelian", -1)

    return render_template('detail-product.html', product=product, best_selling_products=best_selling_products, is_logged_in=is_logged_in, user_info=user_info)
    
# Products, Detail & All End

@app.route('/purchase')
#fungsi wajib login
def purchase():
    token_receive = request.cookies.get(TOKEN_KEY)
    
    if not ('user_id' in session or token_receive):
        return redirect(url_for('login'))  

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({'email': payload.get('id')})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        user_info = None

    return render_template('purchase.html', is_logged_in=True, user_info=user_info) 

@app.route('/cart')
def cart():
    token_receive = request.cookies.get(TOKEN_KEY)
    
    if not ('user_id' in session or token_receive):
        return redirect(url_for('login'))  

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({'email': payload.get('id')})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        user_info = None

    return render_template('cart.html', is_logged_in=True, user_info=user_info) 

@app.route('/update_profile', methods=['GET', 'POST'])
def update():
    token_receive = request.cookies.get(TOKEN_KEY)
    
    if not ('user_id' in session or token_receive):
        return redirect(url_for('login'))  

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({'email': payload.get('id')})
        email = payload.get('id')
        
        if request.method == 'POST':
            username_receive = request.form.get('username_give')
            email_receive = request.form.get('email_give')
            contact_receive = request.form.get('contact_give')
            address_receive = request.form.get('address_give')

            new_doc = {
                "username": username_receive,                               
                "email": email_receive,                                     
                "contact": contact_receive,                                 
                "address": address_receive,                                  
                "profile_name": username_receive,                                                                  
            }

            if 'file_give' in request.files:
                file = request.files.get('file_give')
                filename = secure_filename(file.filename)
                extension = filename.split('.')[-1]
                if extension not in ['jpg', 'jpeg', 'png', 'gif']:
                    return jsonify({'result': 'error', 'msg': 'Invalid file type'})
                file_path = f'profile_pics/{username_receive}.{extension}'
                file.save('./static/' + file_path)
                new_doc['profile_pic_real'] = file_path

            db.users.update_one(
                {'email': email},
                {'$set': new_doc}
            )
            return redirect(url_for('home')) 

        return render_template('update_profile.html', is_logged_in=True, user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        user_info = None
        
    return redirect(url_for('login'))


## admin side
@app.route('/adm-login')
def loginAdmin():
    return render_template('adm-login.html')

@app.route('/adm-register')
def registerAdmin():
    return render_template('adm-register.html')

@app.route('/riwayat')
def riwayat():
    return render_template('riwayat.html')


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
