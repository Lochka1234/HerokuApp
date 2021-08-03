import flask as fl
import flask_security as fls
import flask_sqlalchemy as sql
import wtforms as wtf
from flask_login import current_user
from flask_security import login_required, roles_required
from wtforms.fields.html5 import TelField
from cloudipsp import Api, Checkout
import cloudipsp as ps
from cloudipsp.helpers import check_data

app = fl.Flask(__name__)
app.config.from_object("config.Config")

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


class Item(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.Text(), nullable=False)
    price = db.Column(db.Integer(), nullable=False)

    def __repr__(self):
        return f'Запись:{self.name}'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.Text(), nullable=False)
    price = db.Column(db.Integer(), nullable=False)
    order_active = db.Column(db.Boolean(), default=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post %r>' % (self.name)


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

    orders = db.relationship('Order',
                             backref='user', lazy='dynamic')


class ExtendedRegisterForm(fls.RegisterForm):
    first_name = wtf.StringField('first_name', [wtf.validators.DataRequired()])
    phone_number = wtf.fields.html5.TelField('phone_number',
                                             [wtf.validators.DataRequired(), wtf.validators.Length(min=10, max=13)])


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


@app.route('/terms')
def terms():
    return fl.render_template("terms.html")


@app.route('/profile/admin')
@login_required
@roles_required('admin')
def admin():
    return fl.render_template("userprofile/admin.html")


@app.route('/delete_user_admin/<id>')
@login_required
@roles_required('admin')
def delete_user_admin(id):
    user_datastore.get_user(current_user.get_id())
    user = user_datastore.get_user(id)
    user_datastore.delete_user(user)
    db.session.commit()
    return fl.redirect(fl.url_for('admin_page', name='users'))


@app.route('/delete/<id>')
@login_required
@roles_required('admin')
def delete(id):
    Item.query.filter_by(id=id).delete()
    db.session.commit()
    return fl.redirect(fl.url_for('admin_page', name='items'))


@app.route('/profile/admin/<name>', methods=['post', 'get'])
@login_required
@roles_required('admin')
def admin_page(name):
    if name == 'users':
        users = User.query.order_by(User.id).all()
        return fl.render_template('userprofile/admin/users_admin.html', data=users)

    if name == 'items':
        item = Item.query.order_by(Item.id).all()
        return fl.render_template('userprofile/admin/item_admin.html', data=item)

    if name == '?':
        pass

    else:
        return fl.redirect('/')


@app.route('/profile/admin/items/add', methods=['post'])
@login_required
@roles_required('admin')
def add_item():
    if fl.request.method == 'POST':
        name = fl.request.form.get('name')
        price = fl.request.form.get('price')
        intro = fl.request.form.get('intro')
        item = Item(name=name, price=price, intro=intro)
        db.session.add(item)
        db.session.commit()
        return fl.redirect(fl.url_for('admin_page', name='items'))


@app.route('/profile/admin/items/edit_item/<id>', methods=['post'])
@login_required
@roles_required('admin')
def edit_item(id):
    if fl.request.method == 'POST':
        item = Item.query.get(id)
        item.name = fl.request.form.get('name')
        item.price = fl.request.form.get('price')
        item.intro = fl.request.form.get('intro')
        db.session.commit()
        return fl.redirect(fl.url_for('admin_page', name='items'))


@app.route('/price')
def price():
    item = Item.query.order_by(Item.id).all()
    return fl.render_template("price.html", data=item)


@app.route('/about')
def about():
    return fl.render_template("about.html")


@app.route('/profile')
@app.route('/profile/')
@login_required
def profile():
    return fl.render_template("profile.html")


@app.route('/profile/your_info', methods=['post', 'get'])
@login_required
def user_info():
    return fl.render_template('userprofile/userinfo.html')


@app.route('/emailModal', methods=['post', 'get'])
@login_required
def email_edit():
    if fl.request.method == 'POST':
        user = user_datastore.get_user(current_user.get_id())
        user.email = fl.request.form.get('email')
        db.session.commit()
    return fl.redirect(fl.url_for('user_info'))


@app.route('/nameModal', methods=['post', 'get'])
@login_required
def name_edit():
    if fl.request.method == 'POST':
        user = user_datastore.get_user(current_user.get_id())
        user.first_name = fl.request.form.get('name')
        db.session.commit()
    return fl.redirect(fl.url_for('user_info'))


@app.route('/phone_numberModal', methods=['post', 'get'])
@login_required
def phone_edit():
    if fl.request.method == 'POST':
        user = user_datastore.get_user(current_user.get_id())
        user.phone_number = fl.request.form.get('phone_number')
        db.session.commit()
    return fl.redirect(fl.url_for('user_info'))


@app.route('/profile/your_history')
@login_required
def user_history():
    return fl.render_template('userprofile/userhistory.html')


@app.route('/delete_user/<id>')
def delete_user(id):
    if id == current_user.get_id():
        user = user_datastore.get_user(current_user.get_id())
        user_datastore.delete_user(user)
        db.session.commit()
        return fl.redirect(fl.url_for('index'))
    else:
        return fl.render_template('userprofile/userinfo.html', error="Ищи себя в прошмандовках Санкт-Петербурга")


@app.route('/price/buy/<int:id>')
@login_required
def buy_item(id):
    item = Item.query.get(id)
    api = Api(merchant_id=1397120,
              secret_key='test')
    checkout = Checkout(api=api)
    data = {
        "currency": "RUB",
        "amount": str(item.price) + '00'
    }
    order = ps.Order(api=api)
    url = checkout.url(data).get('checkout_url')
    return fl.redirect(url)



