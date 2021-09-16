from unittest.mock import ANY

import pytest
from bs4 import BeautifulSoup
from flask import session, url_for
from flask_login import current_user

from tests.conftest import normalize_spaces


def test_render_register_returns_template_with_form(client):
    response = client.get('/register')

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('input', attrs={'name': 'auth_type'}).attrs['value'] == 'sms_auth'
    assert page.select_one('#email_address')['spellcheck'] == 'false'
    assert page.select_one('#email_address')['autocomplete'] == 'email'
    assert page.select_one('#password')['autocomplete'] == 'new-password'
    assert 'Create an account' in response.get_data(as_text=True)


def test_logged_in_user_redirects_to_account(
    client_request,
):
    client_request.get(
        'main.register',
        _expected_status=302,
        _expected_redirect=url_for('main.show_accounts_or_dashboard', _external=True),
    )


@pytest.mark.parametrize('phone_number_to_register_with', [
    '+4407700900460',
    '+1800-555-555',
])
@pytest.mark.parametrize('password', [
    'the quick brown fox',
    '   the   quick   brown   fox   ',
])
def test_register_creates_new_user_and_redirects_to_continue_page(
    client,
    mock_send_verify_code,
    mock_register_user,
    mock_get_user_by_email_not_found,
    mock_email_is_not_already_in_use,
    mock_send_verify_email,
    mock_login,
    phone_number_to_register_with,
    password,
):
    user_data = {'name': 'Some One Valid',
                 'email_address': 'notfound@example.gov.uk',
                 'mobile_number': phone_number_to_register_with,
                 'password': password,
                 'auth_type': 'sms_auth'
                 }

    response = client.post(url_for('main.register'), data=user_data, follow_redirects=True)
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('main p')[0].text == 'An email has been sent to notfound@example.gov.uk.'

    mock_send_verify_email.assert_called_with(ANY, user_data['email_address'])
    mock_register_user.assert_called_with(user_data['name'],
                                          user_data['email_address'],
                                          user_data['mobile_number'],
                                          user_data['password'],
                                          user_data['auth_type'])


def test_register_continue_handles_missing_session_sensibly(
    client,
):
    # session is not set
    response = client.get(url_for('main.registration_continue'))
    assert response.status_code == 302
    assert response.location == url_for('main.show_accounts_or_dashboard', _external=True)


def test_process_register_returns_200_when_mobile_number_is_invalid(
    client,
    mock_send_verify_code,
    mock_get_user_by_email_not_found,
    mock_login,
):
    response = client.post(url_for('main.register'),
                           data={'name': 'Bad Mobile',
                                 'email_address': 'bad_mobile@example.gov.uk',
                                 'mobile_number': 'not good',
                                 'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Must not contain letters or symbols' in response.get_data(as_text=True)


@pytest.mark.parametrize('email_address', (
    'notfound@example.gov.uk',
    'example@lsquo.net',
    pytest.param('example@ellipsis.com', marks=pytest.mark.xfail(raises=AssertionError, strict=False)),
))
def test_should_add_user_details_to_session(
    client,
    mock_send_verify_code,
    mock_register_user,
    mock_get_user_by_email_not_found,
    mock_get_organisations_with_unusual_domains,
    mock_email_is_not_already_in_use,
    mock_send_verify_email,
    mock_login,
    email_address,
):
    response = client.post(
        url_for('main.register'),
        data={
            'name': 'Test Codes',
            'email_address': email_address,
            'mobile_number': '+4407700900460',
            'password': 'validPassword!'
        },
    )
    assert response.status_code == 302
    assert session['user_details']['email'] == email_address


def test_should_return_200_if_password_is_on_list_of_commonly_used_passwords(
    client,
    mock_get_user_by_email,
    mock_login,
):
    response = client.post(url_for('main.register'),
                           data={'name': 'Bad Mobile',
                                 'email_address': 'bad_mobile@example.gov.uk',
                                 'mobile_number': '+44123412345',
                                 'password': 'password'})

    assert response.status_code == 200
    assert 'Choose a password that’s harder to guess' in response.get_data(as_text=True)


def test_register_with_existing_email_sends_emails(
    client,
    api_user_active,
    mock_get_user_by_email,
    mock_send_already_registered_email,
):
    user_data = {
        'name': 'Already Hasaccount',
        'email_address': api_user_active['email_address'],
        'mobile_number': '+4407700900460',
        'password': 'validPassword!'
    }

    response = client.post(url_for('main.register'),
                           data=user_data)
    assert response.status_code == 302
    assert response.location == url_for('main.registration_continue', _external=True)


@pytest.mark.parametrize('email_address, expected_value', [
    ("first.last@example.com", "First Last"),
    ("first.middle.last@example.com", "First Middle Last"),
    ("first.m.last@example.com", "First Last"),
    ("first.last-last@example.com", "First Last-Last"),
    ("first.o'last@example.com", "First O’Last"),
    ("first.last+testing@example.com", "First Last"),
    ("first.last+testing+testing@example.com", "First Last"),
    ("first.last6@example.com", "First Last"),
    ("first.last.212@example.com", "First Last"),
    ("first.2.last@example.com", "First Last"),
    ("first.2b.last@example.com", "First Last"),
    ("first.1.2.3.last@example.com", "First Last"),
    ("first.last.1.2.3@example.com", "First Last"),
    # Instances where we can’t make a good-enough guess:
    ("example123@example.com", None),
    ("f.last@example.com", None),
    ("f.m.last@example.com", None),
])
def test_shows_name_on_registration_page_from_invite(
    client_request,
    fake_uuid,
    email_address,
    expected_value,
    sample_invite,
    mock_get_invited_user_by_id,
):
    sample_invite['email_address'] = email_address
    with client_request.session_transaction() as session:
        session['invited_user_id'] = sample_invite

    page = client_request.get('main.register_from_invite')
    assert page.select_one('input[name=name]').get('value') == expected_value


def test_shows_hidden_email_address_on_registration_page_from_invite(
    client_request,
    fake_uuid,
    sample_invite,
    mock_get_invited_user_by_id,
):

    with client_request.session_transaction() as session:
        session['invited_user_id'] = sample_invite

    page = client_request.get('main.register_from_invite')
    assert normalize_spaces(page.select_one('main p').text) == (
        'Your account will be created with this email address: invited_user@test.gov.uk'
    )
    hidden_input = page.select_one('form .govuk-visually-hidden input')
    for attr, value in (
        ('type', 'email'),
        ('name', 'username'),
        ('id', 'username'),
        ('value', 'invited_user@test.gov.uk'),
        ('disabled', "disabled"),
        ('tabindex', '-1'),
        ('aria-hidden', 'true'),
        ('autocomplete', 'username'),
    ):
        assert hidden_input[attr] == value


@pytest.mark.parametrize('extra_data', (
    {},
    # The username field is present in the page but the POST request
    # should ignore it
    {'username': 'invited@user.com'},
    {'username': 'anythingelse@example.com'},
))
def test_register_from_invite(
    client,
    fake_uuid,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_accept_invite,
    mock_get_invited_user_by_id,
    sample_invite,
    extra_data,
):
    with client.session_transaction() as session:
        session['invited_user_id'] = sample_invite['id']
    response = client.post(
        url_for('main.register_from_invite'),
        data=dict(
            name='Registered in another Browser',
            email_address=sample_invite['email_address'],
            mobile_number='+4407700900460',
            service=sample_invite['service'],
            password='somreallyhardthingtoguess',
            auth_type='sms_auth',
            **extra_data
        ),
    )
    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)
    mock_register_user.assert_called_once_with(
        'Registered in another Browser',
        sample_invite['email_address'],
        '+4407700900460',
        'somreallyhardthingtoguess',
        'sms_auth',
    ),
    mock_get_invited_user_by_id.assert_called_once_with(sample_invite['id'])


def test_register_from_invite_when_user_registers_in_another_browser(
    client,
    api_user_active,
    mock_get_user_by_email,
    mock_accept_invite,
    mock_get_invited_user_by_id,
    sample_invite,
):
    sample_invite['email_address'] = api_user_active['email_address']
    with client.session_transaction() as session:
        session['invited_user_id'] = sample_invite['id']
    response = client.post(
        url_for('main.register_from_invite'),
        data={
            'name': 'Registered in another Browser',
            'email_address': api_user_active['email_address'],
            'mobile_number': api_user_active['mobile_number'],
            'service': sample_invite['service'],
            'password': 'somreallyhardthingtoguess',
            'auth_type': 'sms_auth'
        }
    )
    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)


@pytest.mark.parametrize('invite_email_address', ['gov-user@gov.uk', 'non-gov-user@example.com'])
def test_register_from_email_auth_invite(
    client,
    sample_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_get_user,
    mock_send_verify_email,
    mock_send_verify_code,
    mock_accept_invite,
    mock_create_event,
    mock_add_user_to_service,
    mock_get_service,
    mock_get_invited_user_by_id,
    invite_email_address,
    service_one,
    fake_uuid,
    mocker,
):
    mock_audit_event = mocker.patch('app.event_handlers.create_add_user_to_service_event')

    sample_invite['auth_type'] = 'email_auth'
    sample_invite['email_address'] = invite_email_address
    with client.session_transaction() as session:
        session['invited_user_id'] = sample_invite['id']
    assert not current_user.is_authenticated

    data = {
        'name': 'invited user',
        'email_address': sample_invite['email_address'],
        'mobile_number': '07700900001',
        'password': 'FSLKAJHFNvdzxgfyst',
        'service': sample_invite['service'],
        'auth_type': 'email_auth',
    }

    resp = client.post(url_for('main.register_from_invite'), data=data)
    assert resp.status_code == 302
    assert resp.location == url_for('main.service_dashboard', service_id=sample_invite['service'], _external=True)

    # doesn't send any 2fa code
    assert not mock_send_verify_email.called
    assert not mock_send_verify_code.called
    # creates user with email_auth set
    mock_register_user.assert_called_once_with(
        data['name'],
        data['email_address'],
        data['mobile_number'],
        data['password'],
        data['auth_type']
    )
    # this is actually called twice, at the beginning of the function and then by the activate_user function
    mock_get_invited_user_by_id.assert_called_with(sample_invite['id'])
    mock_accept_invite.assert_called_once_with(sample_invite['service'], sample_invite['id'])
    # just logs them in
    assert current_user.is_authenticated
    assert mock_add_user_to_service.called

    mock_audit_event.assert_called_once_with(invited_by_id=service_one['users'][0],
                                             service_id=sample_invite['service'],
                                             user_id=fake_uuid)

    with client.session_transaction() as session:
        # invited user details are still there so they can get added to the service
        assert session['invited_user_id'] == sample_invite['id']


def test_can_register_email_auth_without_phone_number(
    client,
    sample_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_get_user,
    mock_send_verify_email,
    mock_send_verify_code,
    mock_accept_invite,
    mock_create_event,
    mock_add_user_to_service,
    mock_get_service,
    mock_get_invited_user_by_id,
):
    sample_invite['auth_type'] = 'email_auth'
    with client.session_transaction() as session:
        session['invited_user_id'] = sample_invite['id']

    data = {
        'name': 'invited user',
        'email_address': sample_invite['email_address'],
        'mobile_number': '',
        'password': 'FSLKAJHFNvdzxgfyst',
        'service': sample_invite['service'],
        'auth_type': 'email_auth'
    }

    resp = client.post(url_for('main.register_from_invite'), data=data)
    assert resp.status_code == 302
    assert resp.location == url_for('main.service_dashboard', service_id=sample_invite['service'], _external=True)

    mock_register_user.assert_called_once_with(
        ANY,
        ANY,
        None,  # mobile_number
        ANY,
        ANY
    )


def test_cannot_register_with_sms_auth_and_missing_mobile_number(
    client,
    mock_send_verify_code,
    mock_get_user_by_email_not_found,
    mock_login,
):
    response = client.post(url_for('main.register'),
                           data={'name': 'Missing Mobile',
                                 'email_address': 'missing_mobile@example.gov.uk',
                                 'password': 'validPassword!'})

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    err = page.select_one('.govuk-error-message')
    assert err.text.strip() == 'Error: Cannot be empty'
    assert err.attrs['data-error-label'] == 'mobile_number'


def test_register_from_invite_form_doesnt_show_mobile_number_field_if_email_auth(
    client,
    sample_invite,
    mock_get_invited_user_by_id,
):
    sample_invite['auth_type'] = 'email_auth'
    with client.session_transaction() as session:
        session['invited_user_id'] = sample_invite['id']

    response = client.get(url_for('main.register_from_invite'))

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('input', attrs={'name': 'auth_type'}).attrs['value'] == 'email_auth'
    assert page.find('input', attrs={'name': 'mobile_number'}) is None
