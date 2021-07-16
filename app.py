import flask as fl
import flask_sqlalchemy as sql
import flask_security as fls
from flask_security import login_required
from flask_login import current_user
import wtforms as wtf
from wtforms.fields.html5 import TelField

app = fl.Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['DEBUG'] = True
app.config['FLASK_DEBUG'] = 1
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}


app.config['SECURITY_PASSWORD_SALT'] = '176474375850775801120531136185633838018'
app.config['SECRET_KEY'] = 'l4gmnDn-ifb9yaytCZgIGhDnWF6_d2tahmYgTDm1GEI'
app.config['SECURITY_URL_PREFIX'] = '/'


app.config['SECURITY_LOGIN_URL'] = '/login/'
app.config['SECURITY_LOGOUT_URL'] = '/logout/'
app.config['SECURITY_REGISTER_URL'] = '/register/'
app.config['SECURITY_POST_LOGIN_VIEW'] = '/'
app.config['SECURITY_POST_LOGOUT_VIEW'] = '/'
app.config['SECURITY_POST_REGISTER_VIEW'] = '/'


app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECURITY_MSG_INVALID_PASSWORD'] = 'Неверный пароль', 'error'
app.config['SECURITY_MSG_USER_DOES_NOT_EXIST'] = 'Такого пользователя не существует', 'error'


db = sql.SQLAlchemy(app)


roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, fls.RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)


class User(db.Model, fls.UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(45), default=None)
    phone_number = db.Column(db.String(15), default=None)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), default=True)
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role',
                            secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)


class ExtendedRegisterForm(fls.RegisterForm):
    first_name = wtf.StringField('first_name', [wtf.validators.DataRequired()])
    phone_number = wtf.fields.html5.TelField('phone_number',  [wtf.validators.DataRequired(), wtf.validators.Length(min=10, max=13)])


user_datastore = fls.SQLAlchemyUserDatastore(db, User, Role)
security = fls.Security(app, user_datastore, register_form=ExtendedRegisterForm)


@app.before_first_request
def create_user():
    db.create_all()

    user_datastore.find_or_create_role(name='admin', description='Administrator')
    user_datastore.find_or_create_role(name='end-user', description='End user')

    if not user_datastore.get_user('someone@example.com'):
        user_datastore.create_user(email='someone@example.com', password=fls.utils.hash_password('password'))
    if not user_datastore.get_user('admin@example.com'):
        user_datastore.create_user(email='admin@example.com', password=fls.utils.hash_password('passwordAdmin'))

    db.session.commit()

    user_datastore.add_role_to_user('someone@example.com', 'end-user')
    user_datastore.add_role_to_user('admin@example.com', 'admin')

    db.session.commit()


@app.route('/')
def index():
    return fl.render_template("index.html")


@app.route('/profile')
@app.route('/profile/')
@login_required
def profile():
    return fl.render_template("profile.html")


@app.route('/profile/your_info', methods=['post', 'get'])
@login_required
def userinfo():
    if fl.request.method == 'POST':
        current_user.first_name = fl.request.form.get('name')
    return fl.render_template('userprofile/userinfo.html')


@app.route('/emailModal', methods=['post', 'get'])
@login_required
def email_edit():
    if fl.request.method == 'POST':
        current_user.first_name = fl.request.form.get('email')
    return fl.render_template('userprofile/userinfo.html')


@app.route('/phone_numberModal', methods=['post', 'get'])
@login_required
def phone_edit():
    if fl.request.method == 'POST':
        current_user.phone_number = fl.request.form.get('phone_number')
    return fl.render_template('userprofile/userinfo.html')


@app.route('/profile/your_history')
@login_required
def userhistory():
    return fl.render_template('userprofile/userhistory.html')


@app.route('/delete_user/<id>')
def delete_user(id):
    if id == current_user.get_id():
        user_datastore.get_user(current_user.get_id())
        user = user_datastore.get_user(id)
        user_datastore.delete_user(user)
        db.session.commit()
        return fl.redirect(fl.url_for('index'))
    else:
        return fl.render_template('userprofile/userinfo.html', error="Ищи себя в прошмандовках Санкт-Петербурга")
