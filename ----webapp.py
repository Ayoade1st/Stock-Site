from flask import Flask, session, g
from flask import render_template, json, redirect, url_for, request, flash
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security import UserMixin, RoleMixin, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.indexable import index_property
from sqlalchemy import Float
from flask_mail import Mail
from tenacity import retry, stop_after_attempt, wait_fixed
from decimal import Decimal, getcontext  # Import only needed names
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import uuid
import secrets
import requests
import datetime
Base = declarative_base()
"""
# Setup flask_mail. This is used to email users
# Can send a welcome email on registration or forgotten password link
"""
mail = Mail()
MAIL_SERVER = 'smtp.mail.yahoo.com'
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = 'fissyayoade@yahoo.com'
MAIL_PASSWORD = 'eepxfdchttruodvt'
app = Flask(__name__)  # Setup flask app
app.config.from_object(__name__)  # Setup app config
mail.init_app(app)  # Initialise flask_mail with this app

"""
# My Config settings for flask security and sqlachemy. 
# Debug is left set to false. Set to true for live reload and debugging
"""
app.config['DEBUG'] = False  # Disable this when ready for production
app.config['SECRET_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
app.config['SECURITY_REGISTERABLE'] = True  # This enables the register option for flask_security
app.config['SECURITY_RECOVERABLE'] = True  # This enables the forgot password option for flask_security
app.config['SECURITY_POST_LOGIN_VIEW'] = 'dashboard'
app.config['SECURITY_POST_REGISTER_VIEW'] = 'dashboard'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECURITY_PASSWORD_SALT'] = secrets.token_hex(16)  # Add this line
app.config['MAIL_DEFAULT_SENDER'] = MAIL_USERNAME  # Set the default sender email address

db = SQLAlchemy(app)  # Create database connection object with SQLAlchemy


"""
# Models for Database.
"""
roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

users_currencies = db.Table('users_currencies',
                            db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                            db.Column('amount', db.Integer()),
                            db.Column('ticker', db.String(255)),
                            db.Column('last', db.Float()),
                            db.Column('bid', db.Float()),
                            db.Column('ask', db.Float())
                            )
# This class is used to model the table which will hold Users
# Contains a backreference to the Role class for User/Admin role possiblities


class Role(db.Model, RoleMixin):
    #__tablename__ = "role"
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

# This class is used to model the table which will hold Users
# Contains a backreference to the Role class for User/Admin role possiblities


class User(db.Model, UserMixin):
    #__tablename__ = 'user'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True)
    password      = db.Column(db.String(255))
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    active        = db.Column(db.Boolean())
    confirmed_at  = db.Column(db.DateTime())

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))



    



class Currency(db.Model, UserMixin):
    #__tablename__ = "Currency"
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(255), unique=True)
    last = db.Column(db.String(255))
    ask = db.Column(db.String(255))
    bid = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime())


# This class is used to model the table which will hold each users currency
# Contains id as a foreign key from User


class UserCurrency(db.Model, UserMixin):
    #__tablename__ = "users_cur"
    trans_id = db.Column(db.Integer, primary_key=True, index=True)
    id = db.Column(db.Integer)

    amount = db.Column(db.Numeric())
    ticker = db.Column(db.String(255))
    priceInBTC = db.Column(db.Numeric())
    priceInUSD = db.Column(db.Numeric())
    priceInEUR = db.Column(db.Numeric())
    priceInCHY = db.Column(db.Numeric())
    last = db.Column(db.String(255))
    ask = db.Column(db.String(255))
    bid = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime())
    index = index_property('id', 'index')


class UserStocks(db.Model, UserMixin):
    #__tablename__ = "users_stocks"
    trans_id = db.Column(db.Integer, primary_key=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Correct the foreign key to reference 'user.id'
    amount = db.Column(db.Numeric(), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)
    market = db.Column(db.String(10), nullable=False)
    price_in_usd = db.Column(db.Numeric(), nullable=False)
    price_in_eur = db.Column(db.Numeric(), nullable=False)
    price_in_cny = db.Column(db.Numeric(), nullable=False)
    last = db.Column(db.Numeric(), nullable=False)
    timestamp = db.Column(db.DateTime(), nullable=False, default=datetime.datetime.utcnow)

    def __init__(self, user_id, amount, ticker, market, price_in_usd, price_in_eur, price_in_cny, last):
        self.user_id = user_id
        self.amount = amount
        self.ticker = ticker
        self.market = market
        self.price_in_usd = price_in_usd
        self.price_in_eur = price_in_eur
        self.price_in_cny = price_in_cny
        self.last = last
        self.timestamp = datetime.datetime.utcnow()

# engine = create_engine('sqlite:///data.db')
# Base.metadata.create_all(engine)  # Create the table with the new column

# Session = sessionmaker(bind=engine)
# session = Session()


class Stock(db.Model, UserMixin):
    #__tablename__ = "Stocks"
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(255), unique=True)
    last = db.Column(db.String(255))  # Store Decimal as string
    market = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime())

    @property
    def last_decimal(self):
        return Decimal(self.last)

    @last_decimal.setter
    def last_decimal(self, value):
        self.last = str(value)




# Setup user_datastore and sqlalchemy for flask_security to use
user_datastore = SQLAlchemyUserDatastore(db, User, Currency)
security = Security(app, user_datastore)



@app.before_first_request
def create_user():
    # Create all tables if they don't exist
    db.create_all()

    # Check if the user already exists
    if User.query.filter_by(email='ryan@gordon.com').first() is None:
        print("No Users found, creating test user")
        user_datastore.create_user(
            email='ryan@gordon.com',
            password='password',
            confirmed_at=datetime.datetime.now(),
            fs_uniquifier=str(uuid.uuid4())  # Generate a unique identifier
        )
        
        # Pull JSON market data from CoinGecko
        r = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={'vs_currency': 'usd'})
        if r.status_code == 200:
            try:
                data = r.json()
            except json.JSONDecodeError:
                data = {}
                print("Failed to decode JSON from CoinGecko")
        else:
            data = {}
            print(f"Failed to fetch data from CoinGecko, status code: {r.status_code}")

        # Process the data
        for coin in data:
            # Add your data processing logic here
            print(f"Coin: {coin['name']}, Price: {coin['current_price']}")

        db.session.commit()
    else:
        print("Found Users in DB")



"""
Views/ Routes for the webapp. homepage, login and register have their own pages.  
All other pages inherit from the index.html page which holds the UI for the webapp (menu and nav)
This is done using Jinja2 Syntaxing Engine. Designed by the Flask team, pocoo

"""
# The default route. Provides a landing page with info about the app and options to login/register


@app.route('/')
def landing_page():
    db.create_all()
    return render_template("homepage.html")
# This route provides a basic UI view of the app with no content. Will be removed in production


@app.route('/index')
@login_required
def index():
    return render_template("index.html")
# All this does is log out the user if any and 


@app.route('/logout')
def logout():
    logout_user(self)

# This route is the main starter view of the app and contains info from the other sections


@app.route('/dashboard')
@login_required
def dash():
    return render_template("dashboard.html")
# This route provides an about me page for me the creator.


@app.route('/about')
@login_required
def about():
    return render_template("about.html")
# This route provides contact links. Not much going on here.


@app.route('/contact')
@login_required
def contact():
    return render_template("contact.html")

# This route provides shows all the currencies for the user if any.


@app.route('/currencies')
@login_required
def currencies():
    Currencies = UserCurrency.query.filter_by(id=current_user.id).all()
    print(Currencies)
    return render_template("currencies.html", Currencies=Currencies)

# This route is the main starter view of the app and contains info from the other sections




@app.before_first_request
def create_user():
    db.create_all()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_stock_data(symbol, api_key):
    base_url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'TIME_SERIES_INTRADAY',
        'symbol': symbol,
        'interval': '1min',
        'apikey': api_key
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()  # Raise an HTTPError for bad responses
    return response.json()


@app.route('/stocks')
@login_required
def stocks():
    if Stock.query.first() is None:
        print("No stock data found in DB")
        
        api_key = 'GN4INDL6W8UHIHSS'
        symbols = ['AAPL', 'GOOG', 'MSFT', 'AMZN', 'TWTR', 'EA', 'FB', 'NVDA', 'CSCO']
        
        for symbol in symbols:
            try:
                data = fetch_stock_data(symbol, api_key)
                time_series = data.get('Time Series (1min)', {})
                if time_series:
                    latest_time = sorted(time_series.keys())[0]
                    latest_data = time_series[latest_time]
                    last_price = float(latest_data['4. close'])
                    u = Stock(ticker=symbol, last=last_price, market='NASDAQ', timestamp=datetime.datetime.now())
                    db.session.add(u)
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch data for {symbol}: {e}")

        db.session.commit()
        
    else:
        print("Found stock data in DB")
        # do something
    # query db for stocks
    Stocks = UserStocks.query.filter_by(user_id=current_user.id).all()

    # pass into html using render_template
    return render_template("stocks.html", Stocks=Stocks)


@app.route('/addNewStock', methods=['POST'])
def addNewStock():
    amount = Decimal(request.form['Amount'])  # Amount taken from posted form
    ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    queriedStock = Stock.query.filter_by(ticker=ticker).first()  # query the db for currency

    if queriedStock is None:
        flash('Unrecognized Ticker. Please select one of the supported tickers')
        print('Unrecognized Ticker. Please select one of the supported tickers')
        return redirect(url_for('stocks'))

    exchange_rates = fetch_exchange_rates()
    if exchange_rates is None:
        flash('Failed to fetch exchange rates. Please try again later.')
        return redirect(url_for('stocks'))

    queriedCur = UserStocks.query.filter_by(ticker=ticker, user_id=current_user.id).first()

    if queriedCur is not None:
        queriedCur.amount += amount
        queriedCur.timestamp = datetime.datetime.now()
        print("Currency amount updated in DB")
    else:
        me = UserStocks(
            user_id=current_user.id,
            amount=float(amount),
            ticker=queriedStock.ticker,
            market=queriedStock.market,
            price_in_usd=(queriedStock.last_decimal * amount),
            price_in_eur=(queriedStock.last_decimal * amount * Decimal(exchange_rates['EUR'])),
            price_in_cny=(queriedStock.last_decimal * amount * Decimal(exchange_rates['CNY'])),
            last=queriedStock.last
        )
        db.session.add(me)
        print("Currency added to DB")

    db.session.commit()
    return redirect(url_for('stocks'))

def fetch_exchange_rates():
    exchange_api_key = '03290e4fb9bf3a6765fa5968'
    try:
        response = requests.get(f'https://v6.exchangerate-api.com/v6/{exchange_api_key}/latest/USD')
        response.raise_for_status()
        data = response.json()
        return data['conversion_rates']
    except requests.RequestException as e:
        print(f"Failed to fetch exchange rates: {e}")
        return None





# This route is used when a user adds a new currency. Info is submitted to server via POST.
# Removed Get method. Design Principle from John Healy. Use only what you need.

@app.route('/addNewCurrency', methods=['POST'])
def addNewCurrency():
    amount = request.form['Amount']  # Amount taken from posted form
    ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    currency = Currency.query.filter_by(ticker='BTC_'+ticker).first()  # query the db for currency
    usd2btc = Currency.query.filter_by(ticker='USDT_BTC').first()
    
    # Use ExchangeRate-API to get the latest exchange rates
    response = requests.get('https://v6.exchangerate-api.com/v6/03290e4fb9bf3a6765fa5968/latest/USD')
    usd2fiat = response.json()
    
    queriedCur = UserCurrency.query.filter_by(ticker='BTC_'+ticker, id=current_user.id).first()
    if currency is not None:
        if queriedCur is not None:
            queriedCur.amount += Decimal(amount)
            queriedCur.timestamp = datetime.datetime.now()
            queriedCur.priceInBTC = (float(currency.last) * float(queriedCur.amount))
            queriedCur.priceInUSD = (queriedCur.priceInBTC * float(usd2btc.last))
            queriedCur.priceInEUR = queriedCur.priceInUSD * usd2fiat['conversion_rates']['EUR']
            queriedCur.priceInCHY = queriedCur.priceInUSD * usd2fiat['conversion_rates']['CNY']
            print("Currency amount updated in DB")
        else:
            me = UserCurrency(
                amount=float(amount), 
                id=current_user.id, 
                ticker=currency.ticker, 
                last=currency.last, 
                bid=currency.bid, 
                ask=currency.last, 
                timestamp=datetime.datetime.now(), 
                priceInBTC=(float(currency.last) * float(amount)), 
                priceInUSD=(float(usd2btc.last) * (float(currency.last) * float(amount))), 
                priceInEUR=((float(usd2btc.last) * (float(currency.last) * float(amount)) * float(usd2fiat['conversion_rates']['EUR']))), 
                priceInCHY=((float(usd2btc.last) * (float(currency.last) * float(amount)) * float(usd2fiat['conversion_rates']['CNY'])))
            )

            db.session.add(me)
            print("Currency added to DB")
        db.session.commit()
    else:
        flash('Unrecognised Ticker. Please select one of the supported tickers')
    return redirect(url_for('currencies'))




@app.route('/currencies/delete/<ticker>')
def deleteentry(ticker):
    queriedCur = UserCurrency.query.filter_by(ticker=ticker, id=current_user.id).first()
    if queriedCur is not None:
        UserCurrency.query.filter_by(ticker=ticker, user_id=current_user.id).delete()
        print("Deleted Currency")
    else:
        print("Could not delete. Redirecting")

    db.session.commit()
    return redirect(url_for('currencies'))

# This route is triggered via the stocks route
# Db is queried for provided stock and if user has stock it removes from db and commits change
# If nothing there it prints this to console and redirects


@app.route('/stocks/delete/<ticker>')
def deletestock(ticker):
    queriedCur = UserStocks.query.filter_by(ticker=ticker, id=current_user.id).first()
    if queriedCur is not None:
        UserStocks.query.filter_by(ticker=ticker, user_id=current_user.id).delete()
        print("Deleted Currency")
    else:
        print("Could not delete. Redirecting")

    db.session.commit()
    return redirect(url_for('stocks'))
""""
# Charts view allows for visual represententation of the users assets
# I leveraged the skills I learned in my Graphics Programming module
# and utilised chart js. This is the only part of my project that uses JS apart from the menu toggle
"""

@app.route("/charts")
def chart():
    labels = []
    valuesAmount = []
    valuesInEur = []
    valuesInUSD = []
    valuesInCNY = []

    Currencies = UserCurrency.query.filter_by(id=current_user.id).all()
    for row in Currencies:
        labels.append(row.ticker)
        valuesAmount.append(row.amount)
        valuesInEur.append(row.priceInEUR)
        valuesInUSD.append(row.priceInUSD)
        valuesInCNY.append(row.priceInCHY)

    print(len(valuesAmount))
    colors = ["#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA", "#ABCDEF", "#DDDDDD", "#ABCABC"]
    return render_template('charts.html', set=list(zip(valuesAmount, valuesInEur, valuesInUSD, valuesInCNY, labels, colors)))

# Example function to update currency prices using ExchangeRate-API
def update_currency_prices():
    response = requests.get('https://v6.exchangerate-api.com/v6/03290e4fb9bf3a6765fa5968/latest/USD')
    exchange_rates = response.json()

    # Update your database with the new exchange rates
    # Example: update UserCurrency prices based on the new rates
    currencies = UserCurrency.query.all()
    for currency in currencies:
        currency.priceInEUR = currency.priceInUSD * exchange_rates['conversion_rates']['EUR']
        currency.priceInCNY = currency.priceInUSD * exchange_rates['conversion_rates']['CNY']
        db.session.commit()

# Call this function periodically to keep your exchange rates up to date
update_currency_prices()





@app.route('/api/sdc')
@login_required
def BTC_SDC():
    # Pull JSON market data from CoinGecko
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,sdcoin&vs_currencies=usd')
    data = r.json()
    
    # Extract data for BTC and SDC
    btc_usd = data['bitcoin']['usd']
    sdc_usd = data['sdcoin']['usd']
    
    # Calculate average price
    pricesList = [btc_usd, sdc_usd]
    avgPrice = sum(pricesList) / float(len(pricesList))
    
    # Fill JSON with the data
    providedJson = {
        "btc_usd": btc_usd,
        "sdc_usd": sdc_usd,
        "priceObject": pricesList,
        "avgPrice": avgPrice
    }

    return json.dumps(providedJson)

@app.route('/api/eth')
def BTC_ETH():
    # Pull JSON market data from CoinGecko
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd')
    data = r.json()
    
    # Extract data for BTC and ETH
    btc_usd = data['bitcoin']['usd']
    eth_usd = data['ethereum']['usd']
    
    # Calculate average price
    pricesList = [btc_usd, eth_usd]
    avgPrice = sum(pricesList) / float(len(pricesList))
    
    # Fill JSON with the data
    providedJson = {
        "btc_usd": btc_usd,
        "eth_usd": eth_usd,
        "priceObject": pricesList,
        "avgPrice": avgPrice
    }

    return json.dumps(providedJson)

@app.route('/api/xmr')
def BTC_XMR():
    # Pull JSON market data from CoinGecko
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,monero&vs_currencies=usd')
    data = r.json()
    
    # Extract data for BTC and XMR
    btc_usd = data['bitcoin']['usd']
    xmr_usd = data['monero']['usd']
    
    # Calculate average price
    pricesList = [btc_usd, xmr_usd]
    avgPrice = sum(pricesList) / float(len(pricesList))
    
    # Fill JSON with the data
    providedJson = {
        "btc_usd": btc_usd,
        "xmr_usd": xmr_usd,
        "priceObject": pricesList,
        "avgPrice": avgPrice
    }

    return json.dumps(providedJson)



"""
# Bind to PORT if defined, otherwise default to 5000.
# I have this here as Heroku or Digital Ocean will needs the ability to specify a port
# I run the app on 0.0.0.0 so that I can use and consume the app on mobile devices. 
# When in GMIT if I do this anyone on the eduroam system can access the webapp using <computers ip>:5000
# Remove this and it will default to localhost. I keep it this way as I designed for mobile users also.
"""
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)



# from flask import Flask, session, g
# from flask import render_template, json, redirect, url_for, request, flash
# from flask_security import Security, SQLAlchemyUserDatastore
# from flask_security import UserMixin, RoleMixin, login_required, current_user
# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.ext.indexable import index_property
# from sqlalchemy import Float
# from flask_mail import Mail
# from tenacity import retry, stop_after_attempt, wait_fixed
# from decimal import Decimal, getcontext  # Import only needed names
# from sqlalchemy import create_engine, Column, Integer, String
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# import os
# import uuid
# import secrets
# import requests
# import datetime
# Base = declarative_base()
# """
# # Setup flask_mail. This is used to email users
# # Can send a welcome email on registration or forgotten password link
# """
# mail = Mail()
# MAIL_SERVER = 'smtp.mail.yahoo.com'
# MAIL_PORT = 465
# MAIL_USE_TLS = False
# MAIL_USE_SSL = True
# MAIL_USERNAME = 'fissyayoade@yahoo.com'
# MAIL_PASSWORD = 'eepxfdchttruodvt'
# app = Flask(__name__)  # Setup flask app
# app.config.from_object(__name__)  # Setup app config
# mail.init_app(app)  # Initialise flask_mail with this app

# """
# # My Config settings for flask security and sqlachemy. 
# # Debug is left set to false. Set to true for live reload and debugging
# """
# app.config['DEBUG'] = False  # Disable this when ready for production
# app.config['SECRET_KEY'] = 'super-secret'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
# app.config['SECURITY_REGISTERABLE'] = True  # This enables the register option for flask_security
# app.config['SECURITY_RECOVERABLE'] = True  # This enables the forgot password option for flask_security
# app.config['SECURITY_POST_LOGIN_VIEW'] = 'dashboard'
# app.config['SECURITY_POST_REGISTER_VIEW'] = 'dashboard'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# app.config['SECURITY_PASSWORD_SALT'] = secrets.token_hex(16)  # Add this line
# app.config['MAIL_DEFAULT_SENDER'] = MAIL_USERNAME  # Set the default sender email address

# db = SQLAlchemy(app)  # Create database connection object with SQLAlchemy


# """
# # Models for Database.
# """
# roles_users = db.Table('roles_users',
                       # db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       # db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

# users_currencies = db.Table('users_currencies',
                            # db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                            # db.Column('amount', db.Integer()),
                            # db.Column('ticker', db.String(255)),
                            # db.Column('last', db.Float()),
                            # db.Column('bid', db.Float()),
                            # db.Column('ask', db.Float())
                            # )
# # This class is used to model the table which will hold Users
# # Contains a backreference to the Role class for User/Admin role possiblities


# class Role(db.Model, RoleMixin):
    # __tablename__ = "role"
    # id = db.Column(db.Integer(), primary_key=True)
    # name = db.Column(db.String(80), unique=True)
    # description = db.Column(db.String(255))

# # This class is used to model the table which will hold Users
# # Contains a backreference to the Role class for User/Admin role possiblities


# class User(db.Model, UserMixin):
    # __tablename__ = 'user'

    # id            = db.Column(db.Integer, primary_key=True)
    # email         = db.Column(db.String(255), unique=True)
    # password      = db.Column(db.String(255))
    # fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    # active        = db.Column(db.Boolean())
    # confirmed_at  = db.Column(db.DateTime())

    # roles = db.relationship('Role', secondary=roles_users,
                            # backref=db.backref('users', lazy='dynamic'))



    



# class Currency(db.Model, UserMixin):
    # __tablename__ = "Currency"
    # id = db.Column(db.Integer, primary_key=True)
    # ticker = db.Column(db.String(255), unique=True)
    # last = db.Column(db.String(255))
    # ask = db.Column(db.String(255))
    # bid = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())


# # This class is used to model the table which will hold each users currency
# # Contains id as a foreign key from User


# class UserCurrency(db.Model, UserMixin):
    # #__tablename__ = "users_cur"
    # trans_id = db.Column(db.Integer, primary_key=True, index=True)
    # id = db.Column(db.Integer)

    # amount = db.Column(db.Numeric())  # Keep this as Numeric
    # ticker = db.Column(db.String(255))
    # priceInBTC = db.Column(db.String(255))  # Store as string
    # priceInUSD = db.Column(db.String(255))  # Store as string
    # priceInEUR = db.Column(db.String(255))  # Store as string
    # priceInCHY = db.Column(db.String(255))  # Store as string
    # last = db.Column(db.String(255))
    # ask = db.Column(db.String(255))
    # bid = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())
    # index = index_property('id', 'index')


# # class UserCurrency(db.Model, UserMixin):
    # # __tablename__ = "users_cur"
    # # trans_id = db.Column(db.Integer, primary_key=True, index=True)
    # # id = db.Column(db.Integer)

    # # amount = db.Column(db.Numeric())
    # # ticker = db.Column(db.String(255))
    # # priceInBTC = db.Column(db.Numeric())
    # # priceInUSD = db.Column(db.Numeric())
    # # priceInEUR = db.Column(db.Numeric())
    # # priceInCHY = db.Column(db.Numeric())
    # # last = db.Column(db.String(255))
    # # ask = db.Column(db.String(255))
    # # bid = db.Column(db.String(255))
    # # timestamp = db.Column(db.DateTime())
    # # index = index_property('id', 'index')


# class UserStocks(db.Model, UserMixin):
    # #__tablename__ = "users_stocks"
    # trans_id = db.Column(db.Integer, primary_key=True, index=True)
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Correct the foreign key to reference 'user.id'
    # amount = db.Column(db.Numeric(), nullable=False)
    # ticker = db.Column(db.String(10), nullable=False)
    # market = db.Column(db.String(10), nullable=False)
    # price_in_usd = db.Column(db.Numeric(), nullable=False)
    # price_in_eur = db.Column(db.Numeric(), nullable=False)
    # price_in_cny = db.Column(db.Numeric(), nullable=False)
    # last = db.Column(db.Numeric(), nullable=False)
    # timestamp = db.Column(db.DateTime(), nullable=False, default=datetime.datetime.utcnow)

    # def __init__(self, user_id, amount, ticker, market, price_in_usd, price_in_eur, price_in_cny, last):
        # self.user_id = user_id
        # self.amount = amount
        # self.ticker = ticker
        # self.market = market
        # self.price_in_usd = price_in_usd
        # self.price_in_eur = price_in_eur
        # self.price_in_cny = price_in_cny
        # self.last = last
        # self.timestamp = datetime.datetime.utcnow()

# # engine = create_engine('sqlite:///data.db')
# # Base.metadata.create_all(engine)  # Create the table with the new column

# # Session = sessionmaker(bind=engine)
# # session = Session()


# class Stock(db.Model, UserMixin):
    # __tablename__ = "Stocks"
    # id = db.Column(db.Integer, primary_key=True)
    # ticker = db.Column(db.String(255), unique=True)
    # last = db.Column(db.String(255))  # Store Decimal as string
    # market = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())

    # @property
    # def last_decimal(self):
        # return Decimal(self.last)

    # @last_decimal.setter
    # def last_decimal(self, value):
        # self.last = str(value)




# # Setup user_datastore and sqlalchemy for flask_security to use
# user_datastore = SQLAlchemyUserDatastore(db, User, Currency)
# security = Security(app, user_datastore)



# @app.before_first_request
# def create_user():
    # # Create all tables if they don't exist
    # db.create_all()

    # # Check if the user already exists
    # if User.query.filter_by(email='ryan@gordon.com').first() is None:
        # print("No Users found, creating test user")
        # user_datastore.create_user(
            # email='ryan@gordon.com',
            # password='password',
            # confirmed_at=datetime.datetime.now(),
            # fs_uniquifier=str(uuid.uuid4())  # Generate a unique identifier
        # )
        
        # # Pull JSON market data from CoinGecko
        # r = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={'vs_currency': 'usd'})
        # if r.status_code == 200:
            # try:
                # data = r.json()
            # except json.JSONDecodeError:
                # data = {}
                # print("Failed to decode JSON from CoinGecko")
        # else:
            # data = {}
            # print(f"Failed to fetch data from CoinGecko, status code: {r.status_code}")

        # # Process the data
        # for coin in data:
            # # Add your data processing logic here
            # print(f"Coin: {coin['name']}, Price: {coin['current_price']}")

        # db.session.commit()
    # else:
        # print("Found Users in DB")



# """
# Views/ Routes for the webapp. homepage, login and register have their own pages.  
# All other pages inherit from the index.html page which holds the UI for the webapp (menu and nav)
# This is done using Jinja2 Syntaxing Engine. Designed by the Flask team, pocoo

# """
# # The default route. Provides a landing page with info about the app and options to login/register


# @app.route('/')
# def landing_page():
    # db.create_all()
    # return render_template("homepage.html")
# # This route provides a basic UI view of the app with no content. Will be removed in production


# @app.route('/index')
# @login_required
# def index():
    # return render_template("index.html")
# # All this does is log out the user if any and 


# @app.route('/logout')
# def logout():
    # logout_user(self)

# # This route is the main starter view of the app and contains info from the other sections


# @app.route('/dashboard')
# @login_required
# def dash():
    # return render_template("dashboard.html")
# # This route provides an about me page for me the creator.


# @app.route('/about')
# @login_required
# def about():
    # return render_template("about.html")
# # This route provides contact links. Not much going on here.


# @app.route('/contact')
# @login_required
# def contact():
    # return render_template("contact.html")

# # This route provides shows all the currencies for the user if any.


# @app.route('/currencies')
# @login_required
# def currencies():
    # Currencies = UserCurrency.query.filter_by(id=current_user.id).all()
    # print(Currencies)
    # return render_template("currencies.html", Currencies=Currencies)

# # This route is the main starter view of the app and contains info from the other sections




# @app.before_first_request
# def create_user():
    # db.create_all()

# @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
# def fetch_stock_data(symbol, api_key):
    # base_url = 'https://www.alphavantage.co/query'
    # params = {
        # 'function': 'TIME_SERIES_INTRADAY',
        # 'symbol': symbol,
        # 'interval': '1min',
        # 'apikey': api_key
    # }
    # response = requests.get(base_url, params=params)
    # response.raise_for_status()  # Raise an HTTPError for bad responses
    # return response.json()


# @app.route('/stocks')
# @login_required
# def stocks():
    # if Stock.query.first() is None:
        # print("No stock data found in DB")
        
        # api_key = 'GN4INDL6W8UHIHSS'
        # symbols = ['AAPL', 'GOOG', 'MSFT', 'AMZN', 'TWTR', 'EA', 'FB', 'NVDA', 'CSCO']
        
        # for symbol in symbols:
            # try:
                # data = fetch_stock_data(symbol, api_key)
                # time_series = data.get('Time Series (1min)', {})
                # if time_series:
                    # latest_time = sorted(time_series.keys())[0]
                    # latest_data = time_series[latest_time]
                    # last_price = float(latest_data['4. close'])
                    # u = Stock(ticker=symbol, last=last_price, market='NASDAQ', timestamp=datetime.datetime.now())
                    # db.session.add(u)
            # except requests.exceptions.RequestException as e:
                # print(f"Failed to fetch data for {symbol}: {e}")

        # db.session.commit()
        
    # else:
        # print("Found stock data in DB")
        # # do something
    # # query db for stocks
    # Stocks = UserStocks.query.filter_by(user_id=current_user.id).all()

    # # pass into html using render_template
    # return render_template("stocks.html", Stocks=Stocks)


# @app.route('/addNewStock', methods=['POST'])
# def addNewStock():
    # amount = Decimal(request.form['Amount'])  # Amount taken from posted form
    # ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    # queriedStock = Stock.query.filter_by(ticker=ticker).first()  # query the db for currency

    # if queriedStock is None:
        # flash('Unrecognized Ticker. Please select one of the supported tickers')
        # print('Unrecognized Ticker. Please select one of the supported tickers')
        # return redirect(url_for('stocks'))

    # exchange_rates = fetch_exchange_rates()
    # if exchange_rates is None:
        # flash('Failed to fetch exchange rates. Please try again later.')
        # return redirect(url_for('stocks'))

    # queriedCur = UserStocks.query.filter_by(ticker=ticker, user_id=current_user.id).first()

    # if queriedCur is not None:
        # queriedCur.amount += amount
        # queriedCur.timestamp = datetime.datetime.now()
        # print("Currency amount updated in DB")
    # else:
        # me = UserStocks(
            # user_id=current_user.id,
            # amount=float(amount),
            # ticker=queriedStock.ticker,
            # market=queriedStock.market,
            # price_in_usd=(queriedStock.last_decimal * amount),
            # price_in_eur=(queriedStock.last_decimal * amount * Decimal(exchange_rates['EUR'])),
            # price_in_cny=(queriedStock.last_decimal * amount * Decimal(exchange_rates['CNY'])),
            # last=queriedStock.last
        # )
        # db.session.add(me)
        # print("Currency added to DB")

    # db.session.commit()
    # return redirect(url_for('stocks'))

# def fetch_exchange_rates():
    # exchange_api_key = '03290e4fb9bf3a6765fa5968'
    # try:
        # response = requests.get(f'https://v6.exchangerate-api.com/v6/{exchange_api_key}/latest/USD')
        # response.raise_for_status()
        # data = response.json()
        # return data['conversion_rates']
    # except requests.RequestException as e:
        # print(f"Failed to fetch exchange rates: {e}")
        # return None





# # This route is used when a user adds a new currency. Info is submitted to server via POST.
# # Removed Get method. Design Principle from John Healy. Use only what you need.


# @app.route('/addNewCurrency', methods=['POST'])
# def addNewCurrency():
    # # ... (rest of the code)

    # if currency is not None:
        # if queriedCur is not None:
            # queriedCur.amount += Decimal(amount)
            # queriedCur.timestamp = datetime.datetime.now()
            # queriedCur.priceInBTC = str(float(currency.last) * float(queriedCur.amount))  # Convert to string
            # queriedCur.priceInUSD = str(queriedCur.priceInBTC * float(usd2btc.last))  # Convert to string
            # queriedCur.priceInEUR = str(queriedCur.priceInUSD * float(usd2fiat['conversion_rates']['EUR']))  # Convert to string
            # queriedCur.priceInCHY = str(queriedCur.priceInUSD * float(usd2fiat['conversion_rates']['CNY']))  # Convert to string
            # print("Currency amount updated in DB")
        # else:
            # me = UserCurrency(
                # amount=float(amount), 
                # id=current_user.id, 
                # ticker=currency.ticker, 
                # last=currency.last, 
                # bid=currency.bid, 
                # ask=currency.last, 
                # timestamp=datetime.datetime.now(), 
                # priceInBTC=str(float(currency.last) * float(amount)),  # Convert to string
                # priceInUSD=str(float(usd2btc.last) * (float(currency.last) * float(amount))),  # Convert to string
                # priceInEUR=str((float(usd2btc.last) * (float(currency.last) * float(amount)) * float(usd2fiat['conversion_rates']['EUR']))),  # Convert to string
                # priceInCHY=str((float(usd2btc.last) * (float(currency.last) * float(amount)) * float(usd2fiat['conversion_rates']['CNY'])))  # Convert to string
            # )

            # db.session.add(me)
            # print("Currency added to DB")
        # db.session.commit()
    # else:
        # flash('Unrecognised Ticker. Please select one of the supported tickers')
    # return redirect(url_for('currencies'))


# # @app.route('/addNewCurrency', methods=['POST'])
# # def addNewCurrency():
    # # amount = request.form['Amount']  # Amount taken from posted form
    # # ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    # # currency = Currency.query.filter_by(ticker='BTC_'+ticker).first()  # query the db for currency
    # # usd2btc = Currency.query.filter_by(ticker='USDT_BTC').first()
    
    # # # Use ExchangeRate-API to get the latest exchange rates
    # # response = requests.get('https://v6.exchangerate-api.com/v6/03290e4fb9bf3a6765fa5968/latest/USD')
    # # usd2fiat = response.json()
    
    # # queriedCur = UserCurrency.query.filter_by(ticker='BTC_'+ticker, id=current_user.id).first()
    # # if currency is not None:
        # # if queriedCur is not None:
            # # queriedCur.amount += Decimal(amount)
            # # queriedCur.timestamp = datetime.datetime.now()
            # # queriedCur.priceInBTC = (float(currency.last) * float(queriedCur.amount))
            # # queriedCur.priceInUSD = (queriedCur.priceInBTC * float(usd2btc.last))
            # # queriedCur.priceInEUR = queriedCur.priceInUSD * usd2fiat['conversion_rates']['EUR']
            # # queriedCur.priceInCHY = queriedCur.priceInUSD * usd2fiat['conversion_rates']['CNY']
            # # print("Currency amount updated in DB")
        # # else:
            # # me = UserCurrency(
                # # amount=float(amount), 
                # # id=current_user.id, 
                # # ticker=currency.ticker, 
                # # last=currency.last, 
                # # bid=currency.bid, 
                # # ask=currency.last, 
                # # timestamp=datetime.datetime.now(), 
                # # priceInBTC=(float(currency.last) * float(amount)), 
                # # priceInUSD=(float(usd2btc.last) * (float(currency.last) * float(amount))), 
                # # priceInEUR=((float(usd2btc.last) * (float(currency.last) * float(amount)) * float(usd2fiat['conversion_rates']['EUR']))), 
                # # priceInCHY=((float(usd2btc.last) * (float(currency.last) * float(amount)) * float(usd2fiat['conversion_rates']['CNY'])))
            # # )

            # # db.session.add(me)
            # # print("Currency added to DB")
        # # db.session.commit()
    # # else:
        # # flash('Unrecognised Ticker. Please select one of the supported tickers')
    # # return redirect(url_for('currencies'))




# @app.route('/currencies/delete/<ticker>')
# def deleteentry(ticker):
    # queriedCur = UserCurrency.query.filter_by(ticker=ticker, id=current_user.id).first()
    # if queriedCur is not None:
        # UserCurrency.query.filter_by(ticker=ticker, user_id=current_user.id).delete()
        # print("Deleted Currency")
    # else:
        # print("Could not delete. Redirecting")

    # db.session.commit()
    # return redirect(url_for('currencies'))

# # This route is triggered via the stocks route
# # Db is queried for provided stock and if user has stock it removes from db and commits change
# # If nothing there it prints this to console and redirects


# @app.route('/stocks/delete/<ticker>')
# def deletestock(ticker):
    # queriedCur = UserStocks.query.filter_by(ticker=ticker, id=current_user.id).first()
    # if queriedCur is not None:
        # UserStocks.query.filter_by(ticker=ticker, user_id=current_user.id).delete()
        # print("Deleted Currency")
    # else:
        # print("Could not delete. Redirecting")

    # db.session.commit()
    # return redirect(url_for('stocks'))
# """"
# # Charts view allows for visual represententation of the users assets
# # I leveraged the skills I learned in my Graphics Programming module
# # and utilised chart js. This is the only part of my project that uses JS apart from the menu toggle
# """

# @app.route("/charts")
# def chart():
    # labels = []
    # valuesAmount = []
    # valuesInEur = []
    # valuesInUSD = []
    # valuesInCNY = []

    # Currencies = UserCurrency.query.filter_by(user_id=current_user.id).all()
    # for row in Currencies:
        # labels.append(row.ticker)
        # valuesAmount.append(row.amount)
        # valuesInEur.append(row.priceInEUR)
        # valuesInUSD.append(row.priceInUSD)
        # valuesInCNY.append(row.priceInCHY)

    # print(len(valuesAmount))
    # colors = ["#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA", "#ABCDEF", "#DDDDDD", "#ABCABC"]
    # return render_template('charts.html', set=list(zip(valuesAmount, valuesInEur, valuesInUSD, valuesInCNY, labels, colors)))

# # Example function to update currency prices using ExchangeRate-API
# # def update_currency_prices():
    # # response = requests.get('https://v6.exchangerate-api.com/v6/03290e4fb9bf3a6765fa5968/latest/USD')
    # # exchange_rates = response.json()

    # # Update your database with the new exchange rates
    # # Example: update UserCurrency prices based on the new rates
    # # Currencies = UserCurrency.query.filter_by(id=current_user.id).all()
    # # for row in Currencies:
        # # row.priceInEUR = Decimal(row.priceInEUR)  # Convert to Decimal
        # # row.priceInUSD = Decimal(row.priceInUSD)  # Convert to Decimal
        # # row.priceInCNY = Decimal(row.priceInCNY)  # Convert to Decimal
    
    # # currencies = UserCurrency.query.all()
     # # Currencies = UserCurrency.query.filter_by(user_id=current_user.id).all()
    # # for currency in currencies:
         # # currency.priceInEUR = Decimal(currency.priceInUSD * exchange_rates['conversion_rates']['EUR'])
         # # currency.priceInCNY = Decimal(currency.priceInUSD * exchange_rates['conversion_rates']['CNY'])
         # # db.session.commit()

# def update_currency_prices():
    # response = requests.get('https://v6.exchangerate-api.com/v6/03290e4fb9bf3a6765fa5968/latest/USD')
    # exchange_rates = response.json()

    # # Update your database with the new exchange rates
    # # Example: update UserCurrency prices based on the new rates
    # currencies = UserCurrency.query.all()
    # for currency in currencies:
        # # Calculate and update prices in EUR and CNY
        # currency.priceInEUR = Decimal(currency.priceInUSD) * Decimal(exchange_rates['conversion_rates']['EUR'])
        # currency.priceInCNY = Decimal(currency.priceInUSD) * Decimal(exchange_rates['conversion_rates']['CNY'])

    # # Commit changes to the database
    # db.session.commit()

# # Call this function periodically to keep your exchange rates up to date
# update_currency_prices()



# @app.route('/api/sdc')
# @login_required
# def BTC_SDC():
    # # Pull JSON market data from CoinGecko
    # r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,sdcoin&vs_currencies=usd')
    # data = r.json()
    
    # # Extract data for BTC and SDC
    # btc_usd = data['bitcoin']['usd']
    # sdc_usd = data['sdcoin']['usd']
    
    # # Calculate average price
    # pricesList = [btc_usd, sdc_usd]
    # avgPrice = sum(pricesList) / float(len(pricesList))
    
    # # Fill JSON with the data
    # providedJson = {
        # "btc_usd": btc_usd,
        # "sdc_usd": sdc_usd,
        # "priceObject": pricesList,
        # "avgPrice": avgPrice
    # }

    # return json.dumps(providedJson)

# @app.route('/api/eth')
# def BTC_ETH():
    # # Pull JSON market data from CoinGecko
    # r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd')
    # data = r.json()
    
    # # Extract data for BTC and ETH
    # btc_usd = data['bitcoin']['usd']
    # eth_usd = data['ethereum']['usd']
    
    # # Calculate average price
    # pricesList = [btc_usd, eth_usd]
    # avgPrice = sum(pricesList) / float(len(pricesList))
    
    # # Fill JSON with the data
    # providedJson = {
        # "btc_usd": btc_usd,
        # "eth_usd": eth_usd,
        # "priceObject": pricesList,
        # "avgPrice": avgPrice
    # }

    # return json.dumps(providedJson)

# @app.route('/api/xmr')
# def BTC_XMR():
    # # Pull JSON market data from CoinGecko
    # r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,monero&vs_currencies=usd')
    # data = r.json()
    
    # # Extract data for BTC and XMR
    # btc_usd = data['bitcoin']['usd']
    # xmr_usd = data['monero']['usd']
    
    # # Calculate average price
    # pricesList = [btc_usd, xmr_usd]
    # avgPrice = sum(pricesList) / float(len(pricesList))
    
    # # Fill JSON with the data
    # providedJson = {
        # "btc_usd": btc_usd,
        # "xmr_usd": xmr_usd,
        # "priceObject": pricesList,
        # "avgPrice": avgPrice
    # }

    # return json.dumps(providedJson)



# """
# # Bind to PORT if defined, otherwise default to 5000.
# # I have this here as Heroku or Digital Ocean will needs the ability to specify a port
# # I run the app on 0.0.0.0 so that I can use and consume the app on mobile devices. 
# # When in GMIT if I do this anyone on the eduroam system can access the webapp using <computers ip>:5000
# # Remove this and it will default to localhost. I keep it this way as I designed for mobile users also.
# """
# port = int(os.environ.get('PORT', 5000))
# app.run(host='0.0.0.0', port=port)
