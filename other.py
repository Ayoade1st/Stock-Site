import requests
import json
import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
db = SQLAlchemy(app)

# Define your Stock model here
class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10))
    last = db.Column(db.Float)
    market = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime)

@app.before_first_request
def create_user():
    db.create_all()

def stocks():
    # We want the price of 5+ stocks
    if Stock.query.first() is None:
        print("No stock data found in DB")
        
        # Replace with Alpha Vantage API call
        api_key = 'your_alpha_vantage_api_key'
        symbols = ['AAPL', 'GOOG', 'MSFT', 'AMZN', 'TWTR', 'EA', 'FB', 'NVDA', 'CSCO']
        base_url = 'https://www.alphavantage.co/query'
        
        for symbol in symbols:
            params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': symbol,
                'interval': '1min',
                'apikey': api_key
            }
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                try:
                    data = response.json()
                    time_series = data.get('Time Series (1min)', {})
                    if time_series:
                        latest_time = sorted(time_series.keys())[0]
                        latest_data = time_series[latest_time]
                        last_price = float(latest_data['4. close'])
                        u = Stock(ticker=symbol, last=last_price, market='NASDAQ', timestamp=datetime.datetime.now())
                        db.session.add(u)
                except json.JSONDecodeError:
                    print(f"Failed to decode JSON for {symbol}")
            else:
                print(f"Failed to fetch data for {symbol}, status code: {response.status_code}")

        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)



import requests
import json
import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from tenacity import retry, stop_after_attempt, wait_fixed

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
db = SQLAlchemy(app)

# Define your Stock model here
class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10))
    last = db.Column(db.Float)
    market = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime)

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

def stocks():
    if Stock.query.first() is None:
        print("No stock data found in DB")
        
        api_key = 'your_alpha_vantage_api_key'
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
    Stocks = UserStocks.query.filter_by(id=current_user.id).all()

    # pass into html using render_template
    return render_template("stocks.html", Stocks=Stocks)

if __name__ == '__main__':
    app.run(debug=True)




import requests
import json
import datetime
from flask import request, redirect, url_for, flash
from decimal import Decimal
from flask_security import current_user
from your_app import db
from your_app.models import Stock, UserStocks

def addNewStock():
    amount = request.form['Amount']  # Amount taken from posted form
    ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    queriedStock = Stock.query.filter_by(ticker=ticker).first()  # query the db for currency

    # Fetch currency exchange rates from ExchangeRate-API
    exchange_api_key = 'your_exchange_rate_api_key'
    fiat = requests.get(f'https://v6.exchangerate-api.com/v6/{exchange_api_key}/latest/USD')
    usd2fiat = fiat.json()

    queriedCur = UserStocks.query.filter_by(ticker=ticker, user_id=current_user.id).first()

    if queriedStock is not None:
        if queriedCur is not None:
            queriedCur.amount += Decimal(amount)
            queriedCur.timestamp = datetime.datetime.now()
            print("Currency amount updated in DB")
        else:
            me = UserStocks(
                amount=float(amount),
                user_id=current_user.id,
                ticker=queriedStock.ticker,
                market=queriedStock.market,
                last=queriedStock.last,
                timestamp=datetime.datetime.now(),
                price_in_usd=(float(queriedStock.last) * float(amount)),
                price_in_eur=(float(queriedStock.last) * float(amount) * float(usd2fiat['conversion_rates']['EUR'])),
                price_in_cny=(float(queriedStock.last) * float(amount) * float(usd2fiat['conversion_rates']['CNY']))
            )

            db.session.add(me)
            print("Currency added to DB")
        db.session.commit()
    else:
        flash('Unrecognized Ticker. Please select one of the supported tickers')
        print('Unrecognized Ticker. Please select one of the supported tickers')
    return redirect(url_for('stocks'))






import requests
from flask import Flask, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
db = SQLAlchemy(app)

class Currency(db.Model):
    # Define your Currency model here
    pass

class UserCurrency(db.Model):
    # Define your UserCurrency model here
    pass

@app.route('/addNewCurrency', methods=['POST'])
def addNewCurrency():
    amount = request.form['Amount']  # Amount taken from posted form
    ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    currency = Currency.query.filter_by(ticker='BTC_'+ticker).first()  # query the db for currency
    usd2btc = Currency.query.filter_by(ticker='USDT_BTC').first()
    
    # Use ExchangeRate-API to get the latest exchange rates
    response = requests.get('https://v6.exchangerate-api.com/v6/YOUR_API_KEY/latest/USD')
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





import requests
from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
db = SQLAlchemy(app)

class UserCurrency(db.Model):
    # Define your UserCurrency model here
    pass

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
    response = requests.get('https://v6.exchangerate-api.com/v6/YOUR_API_KEY/latest/USD')
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



# @app.route("/charts")
# def chart():
    # labels = []
    # valuesAmount = []
    # valuesInEur = []
    # # valuesInGBP = []
    # valuesInUSD = []
    # valuesInCNY = []

    # Currencies = UserCurrency.query.filter_by(id=current_user.id).all()
    # for row in Currencies:
        # labels.append(row.ticker)
        # valuesAmount.append(row.amount)
        # valuesInEur.append(row.priceInEUR)
        # # valuesInGBP.append(row.priceInGBP)
        # valuesInUSD.append(row.priceInUSD)
        # valuesInCNY.append(row.priceInCHY)

    # print(len(valuesAmount))
    # colors = ["#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA", "#ABCDEF", "#DDDDDD", "#ABCABC"]
    # return render_template('charts.html', set=list(zip(valuesAmount, valuesInEur, valuesInUSD, valuesInCNY, labels, colors)))
# """"
# This starts the API section. I initially set out on this project as I noticed there was no API
# for averaged data for crypto currencies. In my api I have set up averaged prices for a number of top
# cryptocurrencies. It is my hope after this project it may be improved by the open source community.



# import requests
# from flask import Flask, request, json
# from flask_login import login_required, current_user

# app = Flask(__name__)




# @app.route('/addNewCurrency', methods=['POST'])
# def addNewCurrency():
    # amount = request.form['Amount']  # Amount taken from posted form
    # ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    # currency = Currency.query.filter_by(ticker='BTC_'+ticker).first()  # query the db for currency
    # usd2btc = Currency.query.filter_by(ticker='USDT_BTC').first()
    # fiat = requests.get('http://api.fixer.io/latest?base=USD')
    # usd2fiat = fiat.json()
    # queriedCur = UserCurrency.query.filter_by(ticker='BTC_'+ticker, id=current_user.id).first()
    # if currency is not None:
        # if queriedCur is not None:
            # queriedCur.amount += Decimal(amount)
            # queriedCur.timestamp = datetime.datetime.now()
            # queriedCur.priceInBTC = (float(currency.last)*float(queriedCur.amount))
            # queriedCur.priceInUSD = (queriedCur.priceInBTC * float(usd2btc.last))
            # queriedCur.priceInEUR = queriedCur.priceInUSD * usd2fiat['rates']['EUR']
            # queriedCur.priceInCHY = queriedCur.priceInUSD * usd2fiat['rates']['CNY']
            # print("Currency amount updated in DB")
        # else:
            # me = UserCurrency(amount=float(amount), id=current_user.id, ticker=currency.ticker, last=currency.last, bid=currency.bid, ask=currency.last, timestamp=datetime.datetime.now(), priceInBTC=(float(currency.last)*float(amount)), priceInUSD=(float(usd2btc.last)*(float(currency.last)*float(amount))), priceInEUR=((float(usd2btc.last)*(float(currency.last)*float(amount))*float(usd2fiat['rates']['EUR']))), priceInCHY=((float(usd2btc.last)*(float(currency.last)*float(amount)) * float(usd2fiat['rates']['CNY']))))

            # db.session.add(me)
            # print("Currency added to DB")
        # db.session.commit()
    # else:
        # flash('Unrecognised Ticker. Please select one of the supported tickers')
    # return redirect(url_for('currencies'))


# This route is triggered via the currency route
# Db is queried for provided currency and if user has stock it removes from db and commits change
# If nothing there it prints this to console and redirects




# def addNewStock():
    # amount = request.form['Amount']  # Amount taken from posted form
    # ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    # queriedStock = Stock.query.filter_by(ticker=ticker).first()  # query the db for currency

    # # Fetch currency exchange rates from ExchangeRate-API
    # exchange_api_key = '03290e4fb9bf3a6765fa5968'
    # fiat = requests.get(f'https://v6.exchangerate-api.com/v6/{exchange_api_key}/latest/USD')
    # usd2fiat = fiat.json()

    # queriedCur = UserStocks.query.filter_by(ticker=ticker).first()

    # if queriedStock is not None:
        # if queriedCur is not None:
            # queriedCur.amount += Decimal(amount)
            # queriedCur.timestamp = datetime.datetime.now()
            # print("Currency amount updated in DB")
        # else:
            # me = UserStocks(
                # amount=float(amount),
                # user_id=current_user.id,
                # ticker=queriedStock.ticker,
                # market=queriedStock.market,
                # last=queriedStock.last,
                # timestamp=datetime.datetime.now(),
                # price_in_usd=(float(queriedStock.last) * float(amount)),
                # price_in_eur=(float(queriedStock.last) * float(amount) * float(usd2fiat['conversion_rates']['EUR'])),
                # price_in_cny=(float(queriedStock.last) * float(amount) * float(usd2fiat['conversion_rates']['CNY']))
            # )

            # db.session.add(me)
            # print("Currency added to DB")
        # db.session.commit()
    # else:
        # flash('Unrecognized Ticker. Please select one of the supported tickers')
        # print('Unrecognized Ticker. Please select one of the supported tickers')
    # return redirect(url_for('stocks'))




# def addNewStock():
    # amount = request.form['Amount']  # Amount taken from posted form
    # ticker = request.form['Ticker'].upper()  # Ticker taken from posted form
    # queriedStock = Stock.query.filter_by(ticker=ticker).first()  # query the db for currency
    # fiat = requests.get('http://api.fixer.io/latest?base=USD')  # Fiat is a term for financials i.e Euro, Dollar
    # usd2fiat = fiat.json()
    # queriedCur = UserStocks.query.filter_by(ticker=ticker, id=current_user.id).first()

    # if queriedStock is not None:
        # if queriedCur is not None:
            # queriedCur.amount += Decimal(amount)
            # queriedCur.timestamp = datetime.datetime.now()
            # print("Currency amount updated in DB")
        # else:
            # me = UserStocks(amount=float(amount), id=current_user.id, ticker=queriedStock.ticker, market=queriedStock.market, last=queriedStock.last, timestamp=datetime.datetime.now(), priceInUSD=((float(queriedStock.last)*float(amount))), priceInEUR=(((float(queriedStock.last)*float(amount))*float(usd2fiat['rates']['EUR']))), priceInCHY=(((float(queriedStock.last)*float(amount)) * float(usd2fiat['rates']['CNY']))))

            # db.session.add(me)
            # print("Currency added to DB")
        # db.session.commit()
    # else:
        # flash('Unrecognised Ticker. Please select one of the supported tickers')
        # print('Unrecognised Ticker. Please select one of the supported tickers')
    # return redirect(url_for('stocks'))
    
    
    
    # @app.route('/stocks')
# @login_required
# def stocks():
    # # We want the price of 5+ stocks
    # if Stock.query.first() is None:
        # print("No stock data found in DB")
        
        # # Replace with Alpha Vantage API call
        # api_key = 'GN4INDL6W8UHIHSS'
        # symbols = ['AAPL', 'GOOG', 'MSFT', 'AMZN', 'TWTR', 'EA', 'FB', 'NVDA', 'CSCO']
        # base_url = 'https://www.alphavantage.co/query'
        
        # for symbol in symbols:
            # params = {
                # 'function': 'TIME_SERIES_INTRADAY',
                # 'symbol': symbol,
                # 'interval': '1min',
                # 'apikey': api_key
            # }
            # response = requests.get(base_url, params=params)
            # if response.status_code == 200:
                # try:
                    # data = response.json()
                    # time_series = data.get('Time Series (1min)', {})
                    # if time_series:
                        # latest_time = sorted(time_series.keys())[0]
                        # latest_data = time_series[latest_time]
                        # last_price = float(latest_data['4. close'])
                        # u = Stock(ticker=symbol, last=last_price, market='NASDAQ', timestamp=datetime.datetime.now())
                        # db.session.add(u)
                # except json.JSONDecodeError:
                    # print(f"Failed to decode JSON for {symbol}")
            # else:
                # print(f"Failed to fetch data for {symbol}, status code: {response.status_code}")

        # db.session.commit()


# def stocks():
    # # We want the price of 5+ stocks
    # # http://finance.google.com/finance/info?client=ig&q=NASDAQ%3AAAPL,GOOG,MSFT,AMZN,TWTR
    # if Stock.query.first() is None:
        # print("No stock data found in DB")
        # request = requests.get('http://finance.google.com/finance/info?client=ig&q=NASDAQ%3AAAPL,GOOG,MSFT,AMZN,TWTR,EA,FB,NVDA,CSCO')
        # request.encoding = 'utf-8'  # We need to change encoding as this API uses ISO and i use utf-8 everywhere else
        # o = request.text[4:]  # The response object contains some characters at start that we cant parse. Trim these off
        # result = json.loads(o)  # After we trim the characters, turn back into JSON
        # for i in result:
            # # Now! Thats what I call Pythonic
            # u = Stock(ticker=i['t'], last=i['l'], market=i['e'], timestamp=datetime.datetime.now())
            # db.session.add(u)

        # db.session.commit()
    





# # Create a user to test with
# @app.before_first_request
# def create_user():
    # # Create all tables if they don't exist
    # db.create_all()

    # # Check if the user already exists
    # if User.query.filter_by(email=email).first() is None:
        # print("No Users found, creating test user")
        # user_datastore.create_user(email='ryan@gordon.com', password='password', confirmed_at=datetime.datetime.now(), fs_uniquifier=generate_fs_uniquifier())
        
        # # Pull JSON market data from Poloniex
        # r = requests.get('https://poloniex.com/public?command=returnTicker')
        # data = r.json()
        
        # # Pull JSON market data from Bittrex
        # b = requests.get('https://bittrex.com/api/v1.1/public/getmarketsummaries')
        # bittrex = b.json()

        # # Process the data (this part is incomplete in your code)
        # for key in data.keys():
            # # Add your data processing logic here
            # u = Currency(ticker=key, last=data[key]['last'], ask=data[key]['lowestAsk'], bid=data[key]['highestBid'], timestamp=datetime.datetime.now())
        # db.session.commit()
    # else:
        # print("Found Users in DB")
# @app.before_first_request

# def create_user():
    # # Possible implementation
    # # Query db for users by email
    # # if dummy user does not exist, create him and attempt to fill the database
    # # if not perhaps check the db and if no currencies are there fill that up too.
    # #if db is None or User.query.first(email) is None:
    
    # if db is None or User.query.filter_by(email=email).first() is None:

        # print("No Users found, creating test user")
        # db.create_all()
        # user_datastore.create_user(email='ryan@gordon.com', password='password', confirmed_at=datetime.datetime.now(), fs_uniquifier = generate_fs_uniquifier())
        # r = requests.get('https://poloniex.com/public?command=returnTicker')
        # # Pull JSON market data from Bittrex
        # b = requests.get('https://bittrex.com/api/v1.1/public/getmarketsummaries')
        # # Print value to user and assign to variable
        # data = r.json()
        # # Print value to user and assign to variable
        # bittrex = b.json()

        # for key in data.keys():
            # u = Currency(ticker=key, last=data[key]['last'], ask=data[key]['lowestAsk'], bid=data[key]['highestBid'], timestamp=datetime.datetime.now())
            # db.session.add(u)

        # db.session.commit()
    # else:
        # print("Found Users in DB")
        
 # class Stock(db.Model, UserMixin):
    # __tablename__ = "Stocks"
    # id = db.Column(db.Integer, primary_key=True)  # Add this line
    # ticker = db.Column(db.String(255), unique=True)
    # last = db.Column(db.String(255))  # Store Decimal as string
    # market = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())

# class Stock(db.Model):
    # id = db.Column(db.Integer, primary_key=True)
    # ticker = db.Column(db.String(255), unique=True)
    # last = db.Column(db.String(255))  # Store last price as a string
    # market = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())

    # def __init__(self, *args, **kwargs):
        # super().__init__(*args, **kwargs)
        # if 'last' in kwargs:
            # self.last = str(kwargs['last'])  # Convert Decimal to string when initializing

    # def get_last_as_decimal(self):
        # return Decimal(self.last)  # Convert string back to Decimal when needed

# class Stock(db.Model, UserMixin):
    # __tablename__ = "Stocks"
    # id = db.Column(db.Integer, primary_key=True)
    # ticker = db.Column(db.String(255), unique=True)
    # last = db.Column(db.String(255))
    # market = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())


# # Define your Stock model here
# class Stock(db.Model, UserMixin):
    # id = db.Column(db.Integer, primary_key=True)
    # ticker = db.Column(db.String(10))
    # last = db.Column(db.Float)
    # market = db.Column(db.String(10))
    # timestamp = db.Column(db.DateTime)
    
# class Stock(db.Model):
    # id = db.Column(db.Integer, primary_key=True)
    # ticker = db.Column(db.String(10), unique=True, nullable=False)
    # last = db.Column(db.Float, nullable=False)
    # market = db.Column(db.String(10), nullable=False)
    # timestamp = db.Column(db.DateTime, nullable=False)


# This class is used to model the table which will hold each users stock investments
# Contains id as a foreign key from User





# class UserStocks(db.Model, UserMixin):
    # __tablename__ = "users_stocks"
    # trans_id = db.Column(db.Integer, primary_key=True, index=True)
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Ensure this line is correct
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



# class UserStocks(db.Model, UserMixin):
    # trans_id = db.Column(db.Integer, primary_key=True, index=True)
    # id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # amount = db.Column(Float)
    # ticker = db.Column(db.String(255))
    # market = db.Column(db.String(255))
    # priceInBTC = db.Column(Float)
    # priceInUSD = db.Column(Float)
    # priceInEUR = db.Column(Float)
    # priceInCNY = db.Column(Float)
    # last = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())
    # index = index_property('id', 'index')



# class UserStocks(db.Model, UserMixin):
    # __tablename__ = "users_stocks"
    # trans_id = db.Column(db.Integer, primary_key=True, index=True)
    # id = db.Column(db.Integer)

    # amount = db.Column(db.Numeric())
    # ticker = db.Column(db.String(255))
    # market = db.Column(db.String(255))
    # priceInBTC = db.Column(db.Numeric())
    # priceInUSD = db.Column(db.Numeric())
    # priceInEUR = db.Column(db.Numeric())
    # priceInCHY = db.Column(db.Numeric())
    # last = db.Column(db.String(255))
    # timestamp = db.Column(db.DateTime())
    # index = index_property('id', 'index')
    
    
    
# class User(db.Model, UserMixin):
    # __tablename__ = 'user'  # Double-check this line
    # id = db.Column(db.Integer, primary_key=True)
    # email = db.Column(db.String(255), unique=True)
    # password = db.Column(db.String(255))
    # fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    # active = db.Column(db.Boolean())
    # confirmed_at = db.Column(db.DateTime())
    # roles = db.relationship('Role', secondary=roles_users,
                            # backref=db.backref('users', lazy='dynamic'))
# This class is used to model the table which will hold the currencies themselves
# Information acquired via the /GET/ method of a publicly available REST API

def generate_fs_uniquifier():
    return '2222222233444555'



# class User(db.Model, UserMixin):
    # id = db.Column(db.Integer, primary_key=True)
    # email = db.Column(db.String(255), unique=True)
    # password = db.Column(db.String(255))
    # active = db.Column(db.Boolean())
    # confirmed_at = db.Column(db.DateTime())
    # fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    # roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    
    
    
    email = 'example@example.com'




# from flask import Flask, session, g
# from flask import render_template, json, redirect, url_for, request, flash
# from flask_security import Security, SQLAlchemyUserDatastore
# from flask_security import UserMixin, RoleMixin, login_required, current_user
# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.ext.indexable import index_property
# from flask_mail import Mail
# from decimal import *
# import os
# import secrets
# import requests
# import datetime
# import uuid
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
# MAIL_DEFAULT_SENDER = 'fissyayoade@yahoo' 
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
# app.config['SECURITY_PASSWORD_SALT'] = 'secrets.token_hex(16)'  # Add this line
# app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'

# db = SQLAlchemy(app)  # Create database connection object with SQLAlchemy
# email = 'example@example.com'