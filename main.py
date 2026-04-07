import os
import uuid
from flask import Flask, render_template, redirect, url_for, request, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Xavfsizlik kaliti (sessiyalar va flash xabarlar uchun shart)
app.config['SECRET_KEY'] = 'cloud-box-2026-super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Maksimal 16MB fayl yuklash

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Kirilmagan bo'lsa login sahifasiga otadi

# --- MODELLAR ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    files = db.relationship('FileModel', backref='owner', lazy=True)

class FileModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False) # Serverdagi unikal nomi
    original_name = db.Column(db.String(100), nullable=False) # Foydalanuvchi ko'radigan nomi
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- YO'NALISHLAR (ROUTES) ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Ism bandligini tekshirish
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Bu foydalanuvchi nomi band! Boshqasini tanlang.', 'danger')
            return redirect(url_for('register'))
        
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Muvaffaqiyatli ro‘yxatdan o‘tdingiz! Kirishingiz mumkin.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Login yoki parol xato!', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Faqat joriy foydalanuvchining fayllarini olib chiqish
    user_files = FileModel.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', files=user_files)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files.get('file')
    if file and file.filename != '':
        orig_name = secure_filename(file.filename)
        # Fayl nomini unikal qilish (UUID qo'shish)
        unique_name = f"{uuid.uuid4().hex}_{orig_name}"
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
        
        new_file = FileModel(
            filename=unique_name, 
            original_name=orig_name, 
            user_id=current_user.id
        )
        db.session.add(new_file)
        db.session.commit()
        flash('Fayl muvaffaqiyatli yuklandi!', 'success')
    else:
        flash('Fayl tanlanmadi!', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/download/<filename>')
@login_required
def download(filename):
    # Xavfsizlik: foydalanuvchi faqat o'ziga tegishli faylni yuklab olishi mumkin
    file_record = FileModel.query.filter_by(filename=filename, user_id=current_user.id).first()
    if file_record:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    flash('Ruxsat berilmagan!', 'danger')
    return redirect(url_for('dashboard')), 403

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- DASTURNI ISHGA TUSHIRISH ---

if __name__ == '__main__':
    # Uploads papkasini tekshirish
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
        
    with app.app_context():
        db.create_all() # MB va jadvallarni yaratish
        
    app.run(debug=True)