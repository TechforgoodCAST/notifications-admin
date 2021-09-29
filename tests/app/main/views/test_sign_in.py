import uuid

import pytest
from flask import url_for

from app.models.user import User
from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_render_sign_in_template_for_new_user(
    client_request
):
    client_request.logout()
    page = client_request.get('main.sign_in')
    assert normalize_spaces(page.select_one('h1').text) == 'Sign in'
    assert normalize_spaces(page.select('label')[0].text) == 'Email address'
    assert page.select_one('#email_address').get('value') is None
    assert page.select_one('#email_address')['autocomplete'] == 'email'
    assert normalize_spaces(page.select('label')[1].text) == 'Password'
    assert page.select_one('#password').get('value') is None
    assert page.select_one('#password')['autocomplete'] == 'current-password'
    assert page.select('main a')[0].text == 'create one now'
    assert page.select('main a')[0]['href'] == url_for('main.register')
    assert page.select('main a')[1].text == 'Forgotten your password?'
    assert page.select('main a')[1]['href'] == url_for('main.forgot_password')
    assert 'Sign in again' not in normalize_spaces(page.text)


def test_render_sign_in_template_with_next_link_for_password_reset(
    client_request
):
    client_request.logout()
    page = client_request.get(
        'main.sign_in',
        _optional_args=f"?next=/services/{SERVICE_ONE_ID}/templates",
        _test_page_title=False
    )
    forgot_password_link = page.find('a', class_="govuk-link govuk-link--no-visited-state page-footer-secondary-link")
    assert forgot_password_link.text == 'Forgotten your password?'
    assert forgot_password_link['href'] == url_for('main.forgot_password', next=f'/services/{SERVICE_ONE_ID}/templates')


def test_sign_in_explains_session_timeout(client):
    response = client.get(url_for('main.sign_in', next='/foo'))
    assert response.status_code == 200
    assert 'We signed you out because you have not used Notify for a while.' in response.get_data(as_text=True)


def test_sign_in_explains_other_browser(logged_in_client, api_user_active, mocker):
    api_user_active['current_session_id'] = str(uuid.UUID(int=1))
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)

    with logged_in_client.session_transaction() as session:
        session['current_session_id'] = str(uuid.UUID(int=2))

    response = logged_in_client.get(url_for('main.sign_in', next='/foo'))

    assert response.status_code == 200
    assert 'We signed you out because you logged in to Notify on another device' in response.get_data(as_text=True)


def test_doesnt_redirect_to_sign_in_if_no_session_info(
    client_request,
    api_user_active,
    mock_get_organisation_by_domain,
):
    api_user_active['current_session_id'] = str(uuid.UUID(int=1))

    with client_request.session_transaction() as session:
        session['current_session_id'] = None

    client_request.get('main.add_service')


@pytest.mark.parametrize('db_sess_id, cookie_sess_id', [
    (None, None),
    (None, uuid.UUID(int=1)),  # BAD - cookie doesn't match db
    (uuid.UUID(int=1), None),  # BAD - has used other browsers before but this is a brand new browser with no cookie
    (uuid.UUID(int=1), uuid.UUID(int=2)),  # BAD - this person has just signed in on a different browser
])
def test_redirect_to_sign_in_if_logged_in_from_other_browser(
    logged_in_client,
    api_user_active,
    mocker,
    db_sess_id,
    cookie_sess_id
):
    api_user_active['current_session_id'] = db_sess_id
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active)
    with logged_in_client.session_transaction() as session:
        session['current_session_id'] = str(cookie_sess_id)

    response = logged_in_client.get(url_for('main.choose_account'))
    assert response.status_code == 302
    assert response.location == url_for('main.sign_in', next='/accounts', _external=True)


def test_logged_in_user_redirects_to_account(
    client_request
):
    client_request.get(
        'main.sign_in',
        _expected_status=302,
        _expected_redirect=url_for('main.show_accounts_or_dashboard', _external=True),
    )


@pytest.mark.parametrize('redirect_url', [
    None,
    f'/services/{SERVICE_ONE_ID}/templates',
])
@pytest.mark.parametrize('email_address, password', [
    ('valid@example.gov.uk', 'val1dPassw0rd!'),
    (' valid@example.gov.uk  ', '  val1dPassw0rd!  '),
])
def test_process_sms_auth_sign_in_return_2fa_template(
    client,
    api_user_active,
    mock_send_verify_code,
    mock_get_user,
    mock_get_user_by_email,
    mock_verify_password,
    email_address,
    password,
    redirect_url
):
    response = client.post(
        url_for('main.sign_in', next=redirect_url), data={
            'email_address': email_address,
            'password': password})
    assert response.status_code == 302
    assert response.location == url_for('.two_factor_sms', next=redirect_url, _external=True)
    mock_verify_password.assert_called_with(api_user_active['id'], password)
    mock_get_user_by_email.assert_called_with('valid@example.gov.uk')


@pytest.mark.parametrize('redirect_url', [
    None,
    f'/services/{SERVICE_ONE_ID}/templates',
])
def test_process_email_auth_sign_in_return_2fa_template(
    client,
    api_user_active_email_auth,
    mock_send_verify_code,
    mock_verify_password,
    mocker,
    redirect_url
):
    mocker.patch('app.user_api_client.get_user', return_value=api_user_active_email_auth)
    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_active_email_auth)

    response = client.post(
        url_for('main.sign_in', next=redirect_url), data={
            'email_address': 'valid@example.gov.uk',
            'password': 'val1dPassw0rd!'})
    assert response.status_code == 302
    assert response.location == url_for('.two_factor_email_sent', _external=True, next=redirect_url)
    mock_send_verify_code.assert_called_with(api_user_active_email_auth['id'], 'email', None, redirect_url)
    mock_verify_password.assert_called_with(api_user_active_email_auth['id'], 'val1dPassw0rd!')


@pytest.mark.parametrize('redirect_url', [
    None,
    f'/services/{SERVICE_ONE_ID}/templates',
])
def test_process_webauthn_auth_sign_in_redirects_to_webauthn_with_next_redirect(
    client,
    api_user_active,
    mocker,
    mock_verify_password,
    redirect_url
):
    api_user_active['auth_type'] = 'webauthn_auth'
    mock_get_user_by_email = mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_active)

    response = client.post(
        url_for(
            'main.sign_in', next=redirect_url
        ),
        data={
            'email_address': 'valid@example.gov.uk',
            'password': 'val1dPassw0rd!'
        }
    )
    mock_get_user_by_email.assert_called_once_with('valid@example.gov.uk')
    assert response.status_code == 302
    assert response.location == url_for('.two_factor_webauthn', _external=True, next=redirect_url)


def test_should_return_locked_out_true_when_user_is_locked(
    client,
    mock_get_user_by_email_locked,
):
    resp = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'valid@example.gov.uk',
            'password': 'whatIsMyPassword!'})
    assert resp.status_code == 200
    assert 'The email address or password you entered is incorrect' in resp.get_data(as_text=True)


def test_should_return_200_when_user_does_not_exist(
    client,
    mock_get_user_by_email_not_found,
):
    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'notfound@gov.uk',
            'password': 'doesNotExist!'})
    assert response.status_code == 200
    assert 'The email address or password you entered is incorrect' in response.get_data(as_text=True)


def test_should_return_redirect_when_user_is_pending(
    client,
    mock_get_user_by_email_pending,
    api_user_pending,
    mock_verify_password,
):
    response = client.post(
        url_for('main.sign_in'),
        data={
            'email_address': 'pending_user@example.gov.uk',
            'password': 'val1dPassw0rd!'
        }
    )
    assert response.location == url_for('main.resend_email_verification', _external=True)
    with client.session_transaction() as s:
        assert s['user_details'] == {
            'email': api_user_pending['email_address'],
            'id': api_user_pending['id']
        }


@pytest.mark.parametrize('redirect_url', [
    None,
    f'/services/{SERVICE_ONE_ID}/templates',
])
def test_should_attempt_redirect_when_user_is_pending(
    client,
    mock_get_user_by_email_pending,
    mock_verify_password,
    redirect_url
):
    response = client.post(
        url_for('main.sign_in', next=redirect_url), data={
            'email_address': 'pending_user@example.gov.uk',
            'password': 'val1dPassw0rd!'})
    assert response.location == url_for('main.resend_email_verification', _external=True, next=redirect_url)
    assert response.status_code == 302


def test_email_address_is_treated_case_insensitively_when_signing_in_as_invited_user(
    client,
    mocker,
    mock_verify_password,
    api_user_active,
    sample_invite,
    mock_accept_invite,
    mock_send_verify_code,
    mock_get_invited_user_by_id,
):
    sample_invite['email_address'] = 'TEST@user.gov.uk'

    mocker.patch(
        'app.models.user.User.from_email_address_and_password_or_none',
        return_value=User(api_user_active),
    )

    with client.session_transaction() as session:
        session['invited_user_id'] = sample_invite['id']

    response = client.post(
        url_for('main.sign_in'), data={
            'email_address': 'test@user.gov.uk',
            'password': 'val1dPassw0rd!'})

    assert mock_accept_invite.called
    assert response.status_code == 302
    assert mock_send_verify_code.called
    mock_get_invited_user_by_id.assert_called_once_with(sample_invite['id'])


def test_when_signing_in_as_invited_user_you_cannot_accept_an_invite_for_another_email_address(
    client_request,
    mocker,
    mock_verify_password,
    api_user_active,
    sample_invite,
    mock_accept_invite,
    mock_send_verify_code,
    mock_get_invited_user_by_id,
):
    sample_invite['email_address'] = 'some_other_user@user.gov.uk'

    mocker.patch(
        'app.models.user.User.from_email_address_and_password_or_none',
        return_value=User(api_user_active),
    )

    client_request.logout()

    with client_request.session_transaction() as session:
        session['invited_user_id'] = sample_invite['id']

    page = client_request.post(
        'main.sign_in',
        _data={
            'email_address': 'test@user.gov.uk',
            'password': 'val1dPassw0rd!'
        },
        _expected_status=403
    )

    assert mock_accept_invite.called is False
    assert mock_send_verify_code.called is False
    assert page.select_one('.banner-dangerous').text.strip() == 'You cannot accept an invite for another person.'
