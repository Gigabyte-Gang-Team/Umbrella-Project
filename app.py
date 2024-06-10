import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, render_template, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]


app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def home():
    product = list(db.products.find({}))
    return render_template('admin_dashboard.html', product=product)

@app.route('/products', methods=["GET"])
def products():
    product = list(db.products.find({}).sort("created_at", -1))
    return render_template('admin_products.html', product=product)

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
    
    return render_template('admin_addProduct.html')


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
    
    return render_template('admin_editProduct.html', product=product)

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
