from .models import Users
from .conftest import USER_CREDENTIALS
# import os
# from pyramid import testing


def test_public_view(app):
    response = app.get('/public', status='2*')
    assert response.status_code == 200


def test_private_view(app):
    response = app.get('/private', status='4*')
    assert response.status_code == 403


def test_user_db_exists(new_session):
    assert len(new_session.query(Users).all()) == 0


def test_user_gets_added_to_db(new_session):
    user = Users(username=USER_CREDENTIALS['username'], pass_hash='hashiehas')
    new_session.add(user)
    new_session.flush()
    assert len(new_session.query(Users).all()) == 1


def test_login_view_is_public(app):
    response = app.get('/login', status='2*')
    assert response.status_code == 200


def test_login_correct_user_info(app, populated_db):
    # import pdb; pdb.set_trace()
    auth_data = {'username': 'fake', 'password': 'fake'}
    response = app.post('/login', auth_data, status='3*')
    assert response.status_code == 302


# def test_private_view_accessable_to_authenticated(authenticated_app):
#     response = authenticated_app.get('private', status='2*')
#     assert response.status_code == 200


# # def test_createnewuser_view_is_public(app):
#     response = app.get('/new_user', status='2*')
#     assert response.status_code == 200