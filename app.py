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
import uuid

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

app.secret_key = SECRET_KEY

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

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.json
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    note = data.get('note', '')

    # Validasi data
    if not user_id or not product_id:
        return jsonify({'message': 'User ID dan Product ID diperlukan!'}), 400

    try:
        user_id = ObjectId(user_id)  # Pastikan user_id adalah ObjectId
        product_id = ObjectId(product_id)  # Pastikan product_id adalah ObjectId

        cart_item = {
            'product_id': str(product_id),
            'quantity': quantity,
            'note': note,
            'added_at': datetime.now()  # Menggunakan datetime.now() untuk waktu saat ini
        }

        # Cari apakah user_id sudah ada di database carts
        existing_cart = db.carts.find_one({'user_id': user_id})
        if existing_cart:
            # Update keranjang yang sudah ada
            db.carts.update_one(
                {'user_id': user_id},
                {'$push': {'items': cart_item}}
            )
        else:
            # Buat keranjang baru
            db.carts.insert_one({
                'user_id': user_id,
                'items': [cart_item]
            })

        return jsonify({'message': 'Produk berhasil ditambahkan ke keranjang!'}), 200
    except Exception as e:
        return jsonify({'message': 'Terjadi kesalahan: ' + str(e)}), 500
    
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

# Cart Start
@app.route('/cart')
def cart():
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

    # Cek apakah user sudah login
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_id_obj = ObjectId(user_id)  # Konversi user_id dari string ke ObjectId
    cart = db.carts.find_one({"user_id": user_id_obj})

    if not cart or 'items' not in cart:
        return render_template('cart.html', items=[], total=0)

    items = []
    total_price = 0

    for item in cart['items']:
        product = db.products.find_one({"_id": ObjectId(item['product_id'])})
        if product:
            product_price = product['harga_produk']
            total_price += product_price * item['quantity']
            items.append({
                'product_id': str(product['_id']),
                'nama_produk': product['nama_produk'],
                'gambar_produk': product['gambar_produk'][0],
                'quantity': item['quantity'],
                'price': product_price,
                'total_price': product_price * item['quantity'],
                'note': item['note']
            })

    return render_template('cart.html', items=items, total=total_price, is_logged_in=is_logged_in, user_info=user_info)

@app.route('/cart/delete/<product_id>', methods=['POST'])
def delete_item(product_id):
    if request.method == 'POST':
        # Ambil user_id dari session dan konversi ke ObjectId
        user_id = session['user_id']
        user_id_obj = ObjectId(user_id)  # Konversi user_id dari string ke ObjectId
        
        # Cari keranjang belanja berdasarkan user_id
        cart = db.carts.find_one({"user_id": user_id_obj})
        
        # Temukan index item dalam keranjang belanja
        index_to_remove = None
        for index, item in enumerate(cart['items']):
            if item['product_id'] == product_id:
                index_to_remove = index
                break
        
        if index_to_remove is not None:
            # Hapus item dari objek "items"
            db.carts.update_one(
                {"user_id": user_id_obj},
                {"$pull": {"items": {"product_id": product_id}}}
            )
            return jsonify({'success': True}), 200
        else:
            # Jika item tidak ditemukan
            return jsonify({'success': False, 'error': 'Item not found'}), 404
# Cart End

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


@app.route('/history')
def riwayat():
    token_receive = request.cookies.get(TOKEN_KEY)
    
    if not ('user_id' in session or token_receive):
        return redirect(url_for('login'))  

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({'email': payload.get('id')})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        user_info = None
    return render_template('history.html', is_logged_in=True, user_info=user_info)

## admin side
## admin side
@app.route('/login/admin', methods=['GET'])
def login_admin():
    msg = request.args.get('msg')
    return render_template('admin/adm-login.html', msg=msg)

@app.route('/logout/admin')
def logout_admin():
    resp = make_response(redirect(url_for('login_admin')))
    resp.delete_cookie(TOKEN_KEY)
    return resp
 
@app.route("/sign_in/admin", methods=["POST"])
def sign_in_admin():
    email_receive = request.form["email_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.admin.find_one(
        {
            "email": email_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": email_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )

@app.route('/register/admin', methods=['GET'])
def register_admin():
    msg = request.args.get('msg')
    return render_template('admin/adm-register.html', msg=msg)

@app.route("/sign_up/save/admin", methods=["POST"])
def sign_up_admin():
    username_receive = request.form['username_give']
    email_receive = request.form['email_give']

    password_receive = request.form['password_give']
    
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    
    doc = {
        "username": username_receive,                               # id
        "email": email_receive,                                     # email

        "password": password_hash,                                  # password
        "profile_name": username_receive,                           # user's name is set to their id by default
        "profile_pic": "",                                          # profile image file name
        "profile_pic_real": "profile_pics/profile_placeholder.png", # a default profile image
        "profile_info": ""                                          # a profile description
    }
    
    db.admin.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/sign_up/check_usn/admin', methods=['POST'])
def check_usn_admin():
    username_receive = request.form['username_give']
    exists = bool(db.admin.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/sign_up/check_email/admin', methods=['POST'])
def check_email_admin():
    email_receive = request.form['email_give']
    exists = bool(db.admin.find_one({"email": email_receive}))
    return jsonify({'result': 'success', 'exists': exists})

# ADMIN Dashboard
@app.route('/dashboardAdmin', methods=["GET", "POST"])
def homeAdmin():
    token_receive = request.cookies.get(TOKEN_KEY)
    
    if not ('user_id' in session or token_receive):
        return redirect(url_for('login_admin'))  # Redirect to the login page if not logged in

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.admin.find_one({'email': payload.get('id')})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        user_info = None
        
    product = list(db.products.find({}))
    return render_template('admin/admin_dashboard.html', product=product, is_logged_in=True, user_info=user_info)

@app.route('/productsAdmin', methods=["GET"])
def productsAdmin():
    product = list(db.products.find({}).sort("created_at", -1))
    return render_template('admin/admin_products.html', product=product)

@app.route('/addProduct', methods=["GET", "POST"])
def addBook():
    if request.method == 'POST':
        # Mengambil data dari form
        nama = request.form.get('nama_produk')
        harga = int(request.form.get('harga_produk'))
        deskripsi = request.form.get('deskripsi_produk')
        merk = request.form.get('merk_produk')
        stok = int(request.form.get('stok_produk'))
        kategori = request.form.get('kategori_produk')
        pembelian = int(request.form.get('total_pembelian', 0))

        # Memproses file gambar yang diunggah
        files = request.files.getlist('gambar_produk')  # Mengambil semua file yang diunggah
        gambar_files = []
        if files:
            for gambar in files:
                if gambar and gambar.filename:
                    # Periksa ekstensi file
                    ext = gambar.filename.rsplit('.', 1)[-1].lower()
                    if ext in ['png', 'jpg', 'jpeg']:
                        nama_file_asli = gambar.filename
                        unique_filename = str(uuid.uuid4()) + "_" + secure_filename(nama_file_asli)
                        file_path = f'./static/imgProduct/{unique_filename}'
                        try:
                            gambar.save(file_path)
                            gambar_files.append(unique_filename)
                        except Exception as e:
                            print(f"Error saving file: {e}")
                            # Tindakan alternatif jika gagal menyimpan file
                    else:
                        print(f"Invalid file extension: {ext}")
                        # Tindakan alternatif jika ekstensi tidak valid
        
        # Mengambil waktu saat ini dalam UTC
        created_at = datetime.now()

        # Membuat dokumen untuk disimpan di database
        doc = {
            'nama_produk': nama,
            'harga_produk': harga,
            'gambar_produk': gambar_files,
            'deskripsi_produk': deskripsi,
            'stok_produk': stok,
            'merk_produk': merk,
            'kategori_produk': kategori,
            'total_pembelian':pembelian,
            'created_at': created_at
        }
        
        # Menyimpan dokumen ke database
        db.products.insert_one(doc)
        return redirect(url_for("products"))
    
    return render_template('admin/admin_addProduct.html')


@app.route('/editProduct/<string:_id>', methods=["GET", "POST"])
def editProduct(_id):
    if request.method == 'POST':
        # Mendapatkan data dari form
        nama = request.form.get('nama_produk')
        harga = int(request.form.get('harga_produk'))
        deskripsi = request.form.get('deskripsi_produk')
        merk = request.form.get('merk_produk')
        stok = int(request.form.get('stok_produk'))
        kategori = request.form.get('kategori_produk')
        
        # Mendapatkan gambar-gambar baru yang diunggah
        gambar_baru = request.files.getlist('gambar_produk')
        
        # Mendapatkan indeks gambar yang akan dihapus
        delete_index = request.form.get('delete_index')
        
        if delete_index:
            delete_index = int(delete_index) - 1  # Ubah nomor gambar menjadi index array (mulai dari 0)
            product = db.products.find_one({'_id': ObjectId(_id)})
            if product and 0 <= delete_index < len(product['gambar_produk']):
                gambar_dihapus = product['gambar_produk'][delete_index]
                # Menghapus gambar dari direktori
                try:
                    os.remove(f'./static/imgProduct/{gambar_dihapus}')
                except OSError:
                    pass
                
                # Menghapus gambar dari array di database menggunakan `$unset` dan `$pull`
                update_query = {
                    '$unset': {f'gambar_produk.{delete_index}': 1}
                }
                db.products.update_one({'_id': ObjectId(_id)}, update_query)
                db.products.update_one({'_id': ObjectId(_id)}, {'$pull': {'gambar_produk': None}})  # Hapus None

        # Menyimpan gambar-gambar baru ke database
        for file_gambar in gambar_baru:
            if file_gambar:
                nama_file_asli = file_gambar.filename
                # Buat nama file unik dengan UUID
                unique_filename = str(uuid.uuid4()) + "_" + secure_filename(nama_file_asli)
                file_path = f'./static/imgProduct/{unique_filename}'
                file_gambar.save(file_path)
                
                # Menambahkan gambar baru ke array gambar_produk
                db.products.update_one({'_id': ObjectId(_id)}, {'$push': {'gambar_produk': unique_filename}})
        
        # Mengupdate data produk dalam database
        doc = {
            'nama_produk': nama,
            'harga_produk': harga,
            'deskripsi_produk': deskripsi,
            'merk_produk': merk,
            'stok_produk': stok,
            'kategori_produk': kategori
        }
        db.products.update_one({'_id': ObjectId(_id)}, {'$set': doc})
        
        return redirect(url_for('products'))
    
    # Mendapatkan produk yang akan diedit
    product = db.products.find_one({'_id': ObjectId(_id)})
    
    return render_template('admin/admin_editProduct.html', product=product)

@app.route('/deleteImage/<string:_id>', methods=["POST"])
def deleteImage(_id):
    data = request.get_json()
    delete_index = int(data.get('delete_index')) - 1  # Konversi ke indeks array

    product = db.products.find_one({'_id': ObjectId(_id)})
    if not product:
        return jsonify({'success': False, 'message': 'Produk tidak ditemukan.'}), 404

    if delete_index < 0 or delete_index >= len(product['gambar_produk']):
        return jsonify({'success': False, 'message': 'Nomor gambar tidak valid.'}), 400

    gambar_dihapus = product['gambar_produk'][delete_index]

    # Hapus gambar dari direktori
    try:
        os.remove(f'./static/imgProduct/{gambar_dihapus}')
    except OSError:
        pass
    
    # Hapus gambar dari database
    db.products.update_one({'_id': ObjectId(_id)}, {'$pull': {'gambar_produk': gambar_dihapus}})

    return jsonify({'success': True, 'message': 'Gambar berhasil dihapus.'})


@app.route('/deleteProduct/<string:_id>', methods=["GET", "POST"])
def deleteProduct(_id):
    db.products.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('products'))

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
