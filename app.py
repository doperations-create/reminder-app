from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os, uuid

app = Flask(__name__)
app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# USER
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# REMINDER
class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    date = db.Column(db.String(20))
    message = db.Column(db.String(500))
    category = db.Column(db.String(50))
    image = db.Column(db.String(200))
    last_notified = db.Column(db.String(20))
    user_id = db.Column(db.Integer)

# ROUTES
@app.route('/')
@login_required
def home():
    reminders = Reminder.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', reminders=reminders)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=request.form['username'], password=password)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect('/')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')

@app.route('/add', methods=['POST'])
@login_required
def add():
    file = request.files['image']
    path = ""

    if file and file.filename != "":
        filename = str(uuid.uuid4()) + "_" + file.filename
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

    title = request.form['title']
    category = request.form['category']

    # Custom event override
    if category == "Custom":
        title = request.form['custom_event']

    r = Reminder(
        title=title,
        date=request.form['date'],
        message=request.form['message'],
        category=category,
        image=path,
        user_id=current_user.id
    )

    db.session.add(r)
    db.session.commit()
    return redirect('/')

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    r = Reminder.query.get(id)
    db.session.delete(r)
    db.session.commit()
    return redirect('/')

# REMINDER ENGINE
def check_reminders():
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")

    reminders = Reminder.query.all()

    for r in reminders:
        event_date = datetime.strptime(r.date, "%Y-%m-%d").date()
        diff = (event_date - today).days

        if diff in [3,2,1,0] and r.last_notified != today_str:
            if diff == 0:
                msg = f"🎉 Today: {r.title}"
            elif diff == 1:
                msg = f"⚡ Tomorrow: {r.title}"
            else:
                msg = f"📅 {diff} days left for {r.title}"

            print("🔔", msg)

            r.last_notified = today_str
            db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, 'interval', minutes=1)
scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)