from pyramid.response import Response
from pyramid.view import view_config

from pyramid.httpexceptions import HTTPFound

from sqlalchemy.exc import DBAPIError
from sqlalchemy import and_

from ..models import Stocks, Users, Association
try:
    from urllib.parse import urlencode
except ImportError: #pragma: no cover
    from urllib import urlencode

from pyramid.security import remember, forget
from ..security import check_credentials
from passlib.apps import custom_app_context as pwd_context

import datetime
import requests


@view_config(route_name='search', renderer='../templates/search.jinja2')
def search_stocks(request):
    msg = ''
    search_results = []
    if request.method == 'GET':
        return {'stocks': search_results, 'msg': msg}
    elif request.method == 'POST':
        try:
            search_name = request.params.get('search')
            search_query = request.dbsession.query(Stocks)\
                .filter(Stocks.name.startswith(search_name.lower().capitalize()))
        except DBAPIError: #pragma: no cover
            return Response(db_err_msg, content_type='text/plain', status=500)

        for row in search_query:
            search_results.append(row)
        if len(search_results) == 0:
            msg = 'No results found, try again.'
        return {'stocks': search_results, 'msg': msg}


@view_config(route_name='add', renderer='../templates/add_page.jinja2')
def add_stock_to_portfolio(request):
    if request.method == 'POST':
        user_id = 1
        new_user_id = user_id
        new_stock_id = request.matchdict['id']
        association_row = Association(user_id=new_user_id, stock_id=new_stock_id)
        query = request.dbsession.query(Association).filter(Association.user_id == user_id)
        list_of_stock_ids = []
        for row in query:
            list_of_stock_ids.append(row.stock_id)
        print(list_of_stock_ids)
        if int(new_stock_id) not in list_of_stock_ids:
            request.dbsession.add(association_row)
            msg = request.matchdict['name'] + ' was added to your portfolio.'
        else:
            msg = request.matchdict['name'] + ' is already in your portfolio.'
        return {'msg': msg}


@view_config(route_name='delete', renderer='../templates/delete_page.jinja2')
def delete_stock_from_portfolio(request):
    if request.method == 'POST':
        user_id = 1
        new_user_id = user_id
        new_stock_sym = request.matchdict['sym']
        try:
            query = request.dbsession.query(Stocks).filter(Stocks.symbol == new_stock_sym).first()
            query_del = request.dbsession.query(Association)\
                .filter(and_(Association.stock_id == query.id,
                Association.user_id == new_user_id)).first()
            request.dbsession.delete(query_del)
            msg = request.matchdict['sym'] + ' was removed from your portfolio.'
        except AttributeError:
            msg = 'Failed: tried to remove a stock that is not in the portfolio.'
    else:
        msg = 'Failed: improper request.'
    return {'msg': msg}

@view_config(route_name='private',
             renderer='string',
             permission='secret')
def private(request):
    return "I'm a private view."


@view_config(route_name='public', renderer='string',
             permission='view')
def pubic(request):
    return "I'm a public page"


@view_config(route_name='home_test',
             renderer='../templates/home_page_test.jinja2')
def home_test(request):
    return {}


@view_config(route_name='portfolio', renderer="../templates/portfolio.jinja2")
def portfolio(request):
    '''The main user portfolio page, displays a list of their stocks and other
       cool stuff'''

    user_id = 1
    query = request.dbsession.query(Users).filter(Users.id == user_id).first()
    query = query.children
    list_of_stock_ids = []
    for row in query:
        list_of_stock_ids.append(row.child.symbol)
    print(list_of_stock_ids)

    elements = []
    for stock in list_of_stock_ids:
        elements.append({'Symbol': str(stock), 'Type': 'price', 'Params': ['c']})

    return build_graph(request, elements)


@view_config(route_name='details', renderer="../templates/details.jinja2")
def single_stock_details(request):
    """Details for single-stock."""
    entries = {}
    msg = ''
    sym = request.matchdict['sym']
    resp = requests.get('http://dev.markitondemand.com/Api/v2/Quote/json?symbol=' + sym)
    if resp.status_code == 200:
        entries = {key: value for key, value in resp.json().items()}
        if 'Message' in entries.keys():
            msg = 'Bad request.'
            entries = {}
    else:
        entries = {}
        msg = 'Could not fulfill the request.'
    return {'entry': entries, 'msg': msg}



# @view_config(route_name='userinfo', renderer="../templates/userinfo.jinja2")
# def userinfo(request):
#     '''A page to display a users information to the user and allow them to
#         change and update it, or removethemselves from the list of users'''
#     return {'message': 'User info page'}


@view_config(route_name='admin', renderer="../templates/admin.jinja2",
             permission='admin')
def admin(request):
    '''A page to display a users information to the site adimn and allow
        them to change and update user information, or remove user'''
    try:
        query = request.dbsession.query(Users)
        users = query.all()
    except DBAPIError:
        return Response(db_err_msg, content_type='text/plain', status=500)
    return {'users': users, 'messages': {}}


# TODO: if there is a login failure give a message, and stay here
@view_config(route_name='login', renderer='templates/login.jinja2')
def login(request):
    if request.method == 'POST':
        # import pdb; pdb.set_trace()

        username = request.params.get('username', '')
        password = request.params.get('password', '')
        # import pdb; pdb.set_trace()
        if check_credentials(request, username, password):
            headers = remember(request, username)
            try:
                query = request.dbsession.query(Users)
                user = query.filter_by(username=username).first()
                user.date_last_logged = datetime.datetime.now()
            except DBAPIError:
                return Response(db_err_msg, content_type='text/plain', status=500)
            return HTTPFound(location=request.route_url('portfolio'),
                             headers=headers)
        else:
            return {'error': "Username or Password Not Recognized"}
    return {'error': ''}


def build_graph(request, elements):
    url = 'http://dev.markitondemand.com/MODApis/Api/v2/InteractiveChart/json'
    req_obj = {
        "parameters":
        {
            'Normalized': 'false',
            'NumberOfDays': 7,
            'DataPeriod': 'Day',
            'Elements': elements
        }
    }

    resp = requests.get(url, params=urlencode(req_obj))

    if resp.status_code == 200:
        entries = {}
        for key, value in resp.json().items():
            entries[key] = value

        # build export dict for template
        export = {}
        print(entries)

        export['dates'] = entries['Dates']
        export['x_values'] = entries['Positions']

        stocks = {}
        for series in entries['Elements']:
            stocks[series['Symbol']] = {
                'y_values': series['DataSeries']['close']['values'],
                'currency': series['Currency'],
                'max': series['DataSeries']['close']['max'],
                'min': series['DataSeries']['close']['min'],

            }
        export['stocks'] = stocks
        print(export)
        return {'entry': export}

    else:
        print('Error connecting to API')
        print(resp.status_code)


@view_config(route_name='new_user', renderer='templates/new_user.jinja2')
def new_user(request):
    username = password = password_verify = first_name = ''
    last_name = phone_number = email = error = message = ''

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        password_verify = request.POST['password_verify']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone_number = request.POST['phone_number']
        email = request.POST['email']

        try:
            query = request.dbsession.query(Users)
            result = query.filter_by(username=username).first()
        except DBAPIError:
            return Response(db_err_msg, content_type='text/plain', status=500)

        if result:
            message = 'User "{}" already exists.'.format(username)
        else:
            if username != '' and password != '' and password_verify != ''\
               and first_name != '' and last_name != '' and email != '':

                if (password == password_verify) and (len(password) > 6):
                    message = "good job, you can enter info"
                    date_joined = datetime.datetime.now()
                    date_last_logged = datetime.datetime.now()
                    new = Users(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        email_verified=0,
                        date_joined=date_joined,
                        date_last_logged=date_last_logged,
                        pass_hash=pwd_context.encrypt(password),
                        phone_number=phone_number,
                        phone_number_verified=0,
                        active=1,
                        password_last_changed=datetime.datetime.now(),
                        password_expired=1,
                    )
                    request.dbsession.add(new)
                    return HTTPFound(location=request.route_url('admin'))
                else:
                    error = 'Passwords do not match or password \
                             is less then 6 characters'
            else:
                error = 'Missing Required Fields'

    return {'error': error, 'username': username, 'first_name': first_name,
            'last_name': last_name, 'phone_number': phone_number,
            'email': email, 'message': message}


@view_config(route_name='single_stock_info_test', renderer='../templates/single_stock_info_test.jinja2')
def single_stock_info_test(request):
    resp = requests.get('http://dev.markitondemand.com/Api/v2/Quote/json?symbol=AAPL')
    if resp.status_code == 200:
        entry = {}
        for key, value in resp.json().items():
            entry[key] = value
    else:
        print('Error connecting to API')
        print(resp.status_code)
    return {'entry': entry}


db_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_market-analysis_db" script
    to initialize your database tables.  Check your virtual
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""
