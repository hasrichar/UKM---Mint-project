from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, session
from pymongo import MongoClient
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, HiddenField, validators
from flask_bcrypt import Bcrypt
from bson import ObjectId
import hashlib
from humanize import naturaltime
from datetime import datetime, timedelta
from wtforms.validators import DataRequired, EqualTo, ValidationError
import os
from os.path import join, dirname
from dotenv import load_dotenv
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileRequired
from jinja2 import Environment
from flask_session import Session

# ============== Connection string dan database ==============
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Adjust the session timeout as needed
Session(app)



def file_exists(path):
    return os.path.exists(path)

app.jinja_env.filters['file_exists'] = file_exists

# ============== Model untuk User ==============
class User(UserMixin):
    def __init__(self, username, profile_pic=None, role='user'):
        self.id = username
        self.username = username
        self.profile_pic = profile_pic
        self.role = role

# ============== Formulir Login ==============
class LoginForm(FlaskForm):
    username = StringField('Username', [validators.DataRequired()], render_kw={'autocomplete': 'username'})
    password = PasswordField('Password', [validators.DataRequired()], render_kw={'autocomplete': 'current-password'})
    submit = SubmitField('Login')

# ============== Formulir Sign Up ==============
class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()], render_kw={'autocomplete': 'username'})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={'autocomplete': 'new-password'})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')], render_kw={'autocomplete': 'new-password'})
    role = StringField('Role', validators=[DataRequired()], render_kw={'autocomplete': 'off'})
    submit = SubmitField('Sign Up')

    def validate_username(self, field):
        existing_user = db.users.find_one({'username': field.data})
        if existing_user:
            raise ValidationError('Username telah digunakan')

    def validate_role(self, field):
        # Pengecekan tambahan di sini
        if field.data.lower() != 'user':
            raise ValidationError('Invalid role. Only "user" role is allowed.')
        
class PostForm(FlaskForm):
    content = TextAreaField('Post Sesuatu', [validators.DataRequired()])
    submit_post = SubmitField('Post')

# Formulir untuk menambahkan komentar
class CommentForm(FlaskForm):
    text = TextAreaField('Comment', [validators.DataRequired()])
    submit_comment = SubmitField('Comment')
    post_id = StringField('Post ID', [validators.DataRequired()])

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'username': user_id})
    if user_data:
        user_role = user_data.get('role', 'user')
        user_profile_pic = user_data.get('profile_pic')
        user = User(user_id, profile_pic=user_profile_pic, role=user_role)
        return user
    return None

# ======= index ===============

@app.route('/', methods=['GET', 'POST'])
def index():
    beritas = db.berita.find().sort([('_id', -1)]).limit(3)
    return render_template('index.html', beritas=beritas)


# ====================== LOGIN ======================
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user_data = db.users.find_one({'username': username})
        if user_data:
            # Verify the hashed password
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if hashed_password == user_data['password']:
                user_role = user_data.get('role', 'user')
                user = User(username, role=user_role) 
                login_user(user)
                flash('Login berhasil!', 'success')

                if current_user.is_authenticated:
                    if current_user.role == 'user':
                        return redirect(url_for('index'))
                    elif current_user.role == 'admin':
                        return redirect(url_for('beritacontrol'))
                    else:
                        flash('Invalid role.', 'danger')
                        return redirect(url_for('login'))

            else:
                flash('Username atau password salah.', 'danger')
        else:
            flash('Username atau password salah.', 'danger')
    return render_template('login.html', form=form)

# ======Daftar akun====
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = form.role.data.lower()

        existing_user = db.users.find_one({'username': username})
        if existing_user:
            flash('Username sudah digunakan, pilih username lain.', 'danger')
        else:
            if role == 'user':
                hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
                db.users.insert_one({'username': username, 'password': hashed_password, 'role': role})

                flash('Registrasi berhasil! Silakan login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Invalid role. Only "user" role is allowed.', 'danger')

    return render_template('signup.html', form=form)

@app.route('/check_username', methods=['GET'])
def check_username():
    username = request.args.get('username')
    existing_user = db.users.find_one({'username': username})
    return jsonify({'available': not existing_user})


# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout berhasil!', 'success')
    return redirect(url_for('index'))


#* ======================= Account Route =======================

@app.route("/akun", methods=['GET', 'POST'])
@login_required
def akun():
    update_form = UpdateAkunForm()

    if update_form.validate_on_submit():
        if 'profile_pic' in request.files:
            profile_pic = update_form.profile_pic.data
            if profile_pic:
                # Ensure that the directory exists
                profile_pic_folder = os.path.join('static', 'image', 'profile')
                os.makedirs(profile_pic_folder, exist_ok=True)

                # Constructing the filename with username and current timestamp
                filename = f"{current_user.username}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
                filepath = os.path.join(profile_pic_folder, filename)

                # Save the profile picture
                profile_pic.save(filepath)

                # Update the current user's profile_pic attribute
                current_user.profile_pic = filename

                # Save the user object to update the profile_pic in the database
                db.users.update_one({'username': current_user.username}, {'$set': {'profile_pic': filename}})
                
                flash('Profile picture updated successfully!', 'success')
                return redirect(url_for('akun'))

    return render_template('account/akun.html', update_form=update_form)

class UpdateAkunForm(FlaskForm):
    profile_pic = FileField('Profile Picture', validators=[FileRequired()])
    submit = SubmitField('Update Profile')

#! ======================== Content =======================

@app.route("/profil")
def profil():
    return render_template('content/profil.html')

# ============== UKM ==================
@app.route("/ukm")
def ukm():
    return render_template('content/ukm.html')


@app.route("/ukm_olahraga")
def ukm_olahraga():
    return render_template('ukm/ukm-olahraga.html')

@app.route("/ukm_media")
def ukm_media():
    return render_template('ukm/ukm-media.html')

@app.route("/ukm_pendidikan")
def ukm_pendidikan():
    return render_template('ukm/ukm-pendidikan.html')

@app.route("/berita")
def berita():
    beritas = db.berita.find() 
    return render_template('content/berita.html', beritas=beritas)

# ================= diskusi =============
@app.route('/diskusi', methods=['GET', 'POST'])
@login_required
def diskusi():
    form_post = PostForm()
    form_comment = CommentForm()
    
    if form_post.validate_on_submit():
        post_content = form_post.content.data
        post_data = {'user_id': current_user.id, 'content': post_content, 'date': datetime.utcnow()}
        db.posts.insert_one(post_data)
        flash('Postingan berhasil ditambahkan!', 'success')
        return redirect(url_for('diskusi'))

    posts = list(db.posts.find().sort('date', -1))
    comments = list(db.comments.find())

    post_comments = {str(post['_id']): [] for post in posts}

    for comment in comments:
        post_id = str(comment['post_id']) if comment['post_id'] is not None else None

        if post_id in post_comments:
            post_comments[post_id].append(comment)

    if form_comment.validate_on_submit():
        post_id = form_comment.post_id.data

        if post_id in post_comments:
            comment_text = form_comment.text.data
            comment_data = {'user_id': current_user.id, 'text': comment_text, 'post_id': post_id,
                            'date': datetime.utcnow()}
            db.comments.insert_one(comment_data)
            flash('Komentar berhasil ditambahkan!', 'success')
            return redirect(url_for('diskusi'))

    selected_post_id = None
    if posts:
        selected_post_id = str(posts[0]['_id'])
    form_comment.post_id.data = selected_post_id

    return render_template('content/diskusi.html', form_post=form_post, form_comment=form_comment, posts=posts,
                        post_comments=post_comments, naturaltime=naturaltime, datetime=datetime, load_user=load_user)

@app.route('/delete_comment/<comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = db.comments.find_one({'_id': ObjectId(comment_id)})

    if comment:
        if current_user.role == 'admin' or current_user.id == comment['user_id']:
            db.comments.delete_one({'_id': ObjectId(comment_id)})
            flash('Komentar berhasil dihapus!', 'success')
    else:
        abort(403)  # Unauthorized

    return redirect(url_for('diskusi'))


@app.route('/delete_post/<post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = db.posts.find_one({'_id': ObjectId(post_id)})

    if post:
        if current_user.role == 'admin' or current_user.id == post['user_id']:
            db.posts.delete_one({'_id': ObjectId(post_id)})
            flash('Postingan berhasil dihapus!', 'success')
        else:
            abort(403)  # Unauthorized
    else:
        abort(404)  # Post not found

    return redirect(url_for('diskusi'))



# =================== Berita =========================
@app.route('/beritacontrol')
def beritacontrol():
    beritas = db.berita.find()
    return render_template('admin/beritacontrol.html', beritas=beritas)

@app.route('/add_berita', methods=['POST'])
def add_berita():
    title_receive = request.form.get('title')
    kategori_receive = request.form.get('kategori')
    deskripsi_receive = request.form.get('deskripsi')

    today = datetime.now()
    mytime = today.strftime("%Y-%m-%d-%H-%M-%S")

    file = request.files['gambar']
    extension = file.filename.split('.')[-1]
    filename = f'static/image/berita/{mytime}.{extension}'
    file.save(filename)

    date = today.strftime('%Y-%m-%d')

    doc = {
        'title': title_receive,
        'kategori': kategori_receive,
        'gambar': filename,
        'deskripsi': deskripsi_receive,
        'date': date,
    }
    db.berita.insert_one(doc)
    return redirect(url_for('beritacontrol'))

@app.route('/delete_berita/<id>')
def delete_berita(id):
    berita = db.berita.find_one({'_id': ObjectId(id)})

    if berita:
        
        if 'gambar' in berita and os.path.exists(berita['gambar']):
            os.remove(berita['gambar'])

        # Menghapus berita dari database
        db.berita.delete_one({'_id': ObjectId(id)})
        flash('Berita berhasil dihapus!', 'success')
    else:
        flash('Berita tidak ditemukan.', 'danger')

    return redirect(url_for('beritacontrol'))

@app.route('/edit_berita/<id>')
def edit_berita(id):
    berita = db.berita.find_one({'_id': ObjectId(id)})
    return render_template('admin/edit_berita.html', berita=berita)

@app.route('/update_berita/<id>', methods=['POST'])
def update_berita(id):
    berita = db.berita.find_one({'_id': ObjectId(id)})

    title_receive = request.form.get('title')
    kategori_receive = request.form.get('kategori')
    deskripsi_receive = request.form.get('deskripsi')

    if 'gambar' in request.files:
        file = request.files['gambar']
        if file.filename != '':
            # Remove old image
            old_filename = berita['gambar']
            os.remove(old_filename)

            # Save new image
            extension = file.filename.split('.')[-1]
            mytime = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            filename = f'static/image/berita/{mytime}.{extension}'
            file.save(filename)
            berita['gambar'] = filename

    # Update news information
    berita['title'] = title_receive
    berita['kategori'] = kategori_receive
    berita['deskripsi'] = deskripsi_receive

    # Save changes to the database
    db.berita.update_one({'_id': ObjectId(id)}, {'$set': berita})

    return redirect(url_for('beritacontrol'))

@app.route('/detail_berita/<id>')
def detail_berita(id):
    berita = db.berita.find_one({'_id': ObjectId(id)})
    print(berita)
    return render_template('content/detailberita.html', berita=berita)

# ==================== Layanan ========================

@app.route("/layanan")
def layanan():
    return render_template('content/layanan.html')

# @app.route("/detailberita")
# def detailberita():
#     return render_template('content/detailberita.html')


# chat app :


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)