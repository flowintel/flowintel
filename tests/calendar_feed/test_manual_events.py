from datetime import datetime

import pytest

from app import db
from app.db_class.db import Calendar_Event, Case, Task, User


SEPTEMBER = {'start': '2026-09-01T00:00:00+02:00', 'end': '2026-10-01T00:00:00+02:00'}
EVENT = {'title': 'Team planning', 'start': '2026-09-25', 'all_day': True}


def login(client, app, api_key='editor_api_key'):
    with app.app_context():
        user_id = User.query.filter_by(api_key=api_key).one().id
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
    return user_id


def share_org(client, app, api_key):
    with app.app_context():
        owner = User.query.filter_by(api_key='editor_api_key').one()
        colleague = User.query.filter_by(api_key=api_key).one()
    
    response = client.post(
        f"/api/admin/edit_user/{colleague.id}",
        content_type='application/json',
        headers={"X-API-KEY": "admin_api_key"},
        json={"org": owner.org_id},
    )
    assert response.status_code == 200


def test_create_edit_delete_standalone_event(client, app):
    user_id = login(client, app)
    response = client.post('/calendar/events', json={**EVENT, 'title': '  Planning  '})
    assert response.status_code == 201
    event = response.json['event']
    assert event['title'] == 'Planning'
    assert event['end'] == '2026-09-26'
    assert event['visibility'] == 'private'
    assert event['can_edit'] is True

    with app.app_context():
        saved = db.session.get(Calendar_Event, event['id'])
        assert saved.user_id == user_id
        assert saved.org_id is None
        assert Case.query.count() == Task.query.count() == 0

    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'] == [event]
    response = client.put(f"/calendar/events/{event['id']}", json={
        **EVENT, 'title': 'Updated', 'description': 'Agenda', 'end': '2026-09-28',
        'visibility': 'organisation',
    })
    assert response.status_code == 200
    assert response.json['event']['title'] == 'Updated'
    assert response.json['event']['visibility'] == 'organisation'
    assert response.json['event']['description'] == 'Agenda'
    assert client.delete(f"/calendar/events/{event['id']}").status_code == 200
    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'] == []
    assert client.get(f"/calendar/download_event_ics/{event['id']}").status_code == 404


@pytest.mark.legacy_db
def test_events_shared_with_org_but_only_editable_by_creator(client, app):
    login(client, app)
    private = client.post('/calendar/events', json={**EVENT, 'title': 'Private planning'}).json['event']
    shared = client.post('/calendar/events', json={**EVENT, 'visibility': 'organisation'}).json['event']

    # An admin in another organisation cannot see either event.
    login(client, app, 'admin_api_key')
    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'] == []
    for event in (private, shared):
        event_id = event['id']
        assert client.get(f'/calendar/download_event_ics/{event_id}').status_code == 404
        assert client.put(f'/calendar/events/{event_id}', json=EVENT).status_code == 404
        assert client.delete(f'/calendar/events/{event_id}').status_code == 404

    share_org(client, app, 'orgadmin_api_key')
    login(client, app, 'orgadmin_api_key')
    visible = client.get('/calendar/events', query_string=SEPTEMBER).json['events']
    assert [event['id'] for event in visible] == [shared['id']]
    assert visible[0]['can_edit'] is False
    assert client.get(f"/calendar/download_event_ics/{shared['id']}").status_code == 200
    assert client.put(f"/calendar/events/{shared['id']}", json=EVENT).status_code == 404
    assert client.delete(f"/calendar/events/{shared['id']}").status_code == 404

    login(client, app)
    assert client.put(f"/calendar/events/{shared['id']}", json=EVENT).status_code == 200
    login(client, app, 'orgadmin_api_key')
    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'] == []


@pytest.mark.legacy_db
def test_read_only_user_can_view_shared_events_but_cannot_write(client, app):
    login(client, app)
    event = client.post('/calendar/events', json={**EVENT, 'visibility': 'organisation'}).json['event']
    share_org(client, app, 'read_api_key')
    login(client, app, 'read_api_key')
    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'][0]['can_edit'] is False
    assert client.post('/calendar/events', json=EVENT).status_code == 403
    assert client.put(f"/calendar/events/{event['id']}", json=EVENT).status_code == 403
    assert client.delete(f"/calendar/events/{event['id']}").status_code == 403
    assert client.get(f"/calendar/download_event_ics/{event['id']}").status_code == 200


def test_event_routes_require_login(client):
    assert client.get('/calendar/events', query_string=SEPTEMBER).status_code == 302
    assert client.post('/calendar/events', json=EVENT).status_code == 302
    assert client.put('/calendar/events/1', json=EVENT).status_code == 302
    assert client.delete('/calendar/events/1').status_code == 302
    assert client.get('/calendar/download_event_ics/1').status_code == 302


def test_invalid_events_are_rejected_without_changing_saved_event(client, app):
    login(client, app)
    event = client.post('/calendar/events', json=EVENT).json['event']
    invalid_payloads = [
        None, [], {'title': 'Missing date'},
        {**EVENT, 'title': '   '}, {**EVENT, 'title': 'x' * 256}, {**EVENT, 'title': 42},
        {**EVENT, 'start': '2026-02-30'}, {**EVENT, 'start': None},
        {**EVENT, 'end': '2026-09-25'}, {**EVENT, 'end': '2026-09-24'},
        {**EVENT, 'description': {}}, {**EVENT, 'description': 'é' * 30001},
        {**EVENT, 'all_day': 'false'}, {**EVENT, 'visibility': 'everyone'},
        {**EVENT, 'all_day': False, 'start': '2026-09-25T10:00:00'},
        {**EVENT, 'all_day': False, 'start': '2026-09-25T10:00:00Z', 'end': '2026-09-25T11:00:00+02:00'},
    ]
    for payload in invalid_payloads:
        assert client.post('/calendar/events', json=payload).status_code == 400
        assert client.put(f"/calendar/events/{event['id']}", json=payload).status_code == 400
    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'] == [event]


def test_event_owner_and_org_cannot_be_spoofed(client, app):
    user_id = login(client, app)
    response = client.post('/calendar/events', json={
        **EVENT, 'user_id': 1, 'org_id': 1, 'visibility': 'organisation',
    })
    assert response.status_code == 201
    with app.app_context():
        event = db.session.get(Calendar_Event, response.json['event']['id'])
        assert event.user_id == user_id
        assert event.org_id == db.session.get(User, user_id).org_id


@pytest.mark.parametrize('offset', ['+02:00', '-07:00'])
def test_visible_range_includes_spanning_events_and_respects_all_day_bounds(client, app, offset):
    login(client, app)
    for values in [
        {'title': 'Spans month', 'start': '2026-08-30', 'end': '2026-09-02'},
        {'title': 'First day', 'start': '2026-09-01'},
        {'title': 'Last day', 'start': '2026-09-30'},
        {'title': 'Ends at boundary', 'start': '2026-08-30', 'end': '2026-09-01'},
        {'title': 'Starts at boundary', 'start': '2026-10-01'},
    ]:
        assert client.post('/calendar/events', json={**EVENT, **values}).status_code == 201
    response = client.get('/calendar/events', query_string={
        'start': f'2026-09-01T00:00:00{offset}', 'end': f'2026-10-01T00:00:00{offset}',
    })
    assert [event['title'] for event in response.json['events']] == ['Spans month', 'First day', 'Last day']


def test_timed_event_normalizes_timezone_and_exports_utc(client, app):
    login(client, app)
    event = client.post('/calendar/events', json={
        **EVENT, 'all_day': False, 'start': '2026-10-01T00:30:00+02:00',
        'end': '2026-10-01T01:30:00+02:00',
    }).json['event']
    assert event['start'] == '2026-09-30T22:30:00Z'
    assert event['end'] == '2026-09-30T23:30:00Z'
    with app.app_context():
        assert db.session.get(Calendar_Event, event['id']).start == datetime(2026, 9, 30, 22, 30)
    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'] == []
    response = client.get('/calendar/events', query_string={
        'start': '2026-09-01T00:00:00Z', 'end': '2026-10-01T00:00:00Z',
    })
    assert response.json['events'] == [event]
    ics = client.get(f"/calendar/download_event_ics/{event['id']}").get_data(as_text=True)
    assert 'DTSTART:20260930T223000Z' in ics
    assert 'DTEND:20260930T233000Z' in ics


@pytest.mark.legacy_db
def test_manual_events_in_web_and_api_feeds_respect_visibility(client, app):
    login(client, app)
    private = client.post('/calendar/events', json={**EVENT, 'title': 'Private event'}).json['event']
    shared = client.post('/calendar/events', json={
        **EVENT, 'title': 'Review, plan; act', 'description': 'First line\nSecond line',
        'visibility': 'organisation',
    }).json['event']
    download = client.get(f"/calendar/download_event_ics/{shared['id']}")
    ics = download.get_data(as_text=True)
    assert download.mimetype == 'text/calendar'
    assert 'SUMMARY:Review\\, plan\\; act' in ics
    assert 'DESCRIPTION:First line\\nSecond line' in ics
    assert 'DTSTART;VALUE=DATE:20260925' in ics
    assert 'DTEND;VALUE=DATE:20260926' in ics
    assert '/case/' not in ics
    for url, headers in [('/calendar/calendar_feed', {}), ('/api/calendar/feed', {'X-API-KEY': 'editor_api_key'})]:
        feed = client.get(url, headers=headers).get_data(as_text=True)
        assert f"UID:event-{private['id']}@flowintel" in feed
        assert f"UID:event-{shared['id']}@flowintel" in feed
    share_org(client, app, 'read_api_key')
    login(client, app, 'read_api_key')
    for url, headers in [('/calendar/calendar_feed', {}), ('/api/calendar/feed', {'X-API-KEY': 'read_api_key'})]:
        feed = client.get(url, headers=headers).get_data(as_text=True)
        assert f"UID:event-{private['id']}@flowintel" not in feed
        assert f"UID:event-{shared['id']}@flowintel" in feed
    external_feed = client.get('/api/calendar/feed', headers={'X-API-KEY': 'admin_api_key'}).get_data(as_text=True)
    assert 'UID:event-' not in external_feed


def test_bad_range_and_missing_events(client, app):
    login(client, app)
    for query in [{}, {'start': 'garbage', 'end': 'garbage'}, {**SEPTEMBER, 'end': SEPTEMBER['start']}]:
        assert client.get('/calendar/events', query_string=query).status_code == 400
    assert client.put('/calendar/events/999', json=EVENT).status_code == 404
    assert client.delete('/calendar/events/999').status_code == 404
    assert client.get('/calendar/download_event_ics/999').status_code == 404


def test_manual_event_mutations_require_csrf(client, app):
    login(client, app)
    event = client.post('/calendar/events', json=EVENT).json['event']
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/calendar/events', json=EVENT).status_code == 400
    assert client.put(f"/calendar/events/{event['id']}", json=EVENT).status_code == 400
    assert client.delete(f"/calendar/events/{event['id']}").status_code == 400


def test_calendar_page_renders_manual_event_controls(client, app):
    login(client, app)
    response = client.get('/calendar/')
    assert response.status_code == 200
    assert 'Add event' in response.get_data(as_text=True)
    assert 'My organisation' in response.get_data(as_text=True)



def test_api_create_manual_event_without_session_or_csrf(client, app):
    app.config['WTF_CSRF_ENABLED'] = True
    response = client.post('/api/calendar/events', headers={'X-API-KEY': 'editor_api_key'}, json={
        'title': '  API planning  ', 'start': '2026-09-25', 'description': 'Created by automation',
    })
    assert response.status_code == 201
    event = response.json['event']
    assert event['title'] == 'API planning'
    assert event['description'] == 'Created by automation'
    assert event['start'] == '2026-09-25'
    assert event['end'] == '2026-09-26'
    assert event['all_day'] is True
    assert event['visibility'] == 'private'
    with app.app_context():
        saved = db.session.get(Calendar_Event, event['id'])
        assert saved.user_id == User.query.filter_by(api_key='editor_api_key').one().id
        assert saved.org_id is None
        assert Case.query.count() == Task.query.count() == 0
    login(client, app)
    visible = client.get('/calendar/events', query_string=SEPTEMBER).json['events']
    assert visible == [{**event, 'can_edit': True}]
    feed = client.get('/api/calendar/feed', headers={'X-API-KEY': 'editor_api_key'}).get_data(as_text=True)
    assert f"UID:event-{event['id']}@flowintel" in feed


@pytest.mark.legacy_db
@pytest.mark.parametrize('visibility', ['private', 'organisation'])
def test_api_event_visibility_and_ownership_follow_api_key(client, app, visibility):
    admin_id = login(client, app, 'admin_api_key')
    with app.app_context():
        admin_org_id = db.session.get(User, admin_id).org_id
    response = client.post('/api/calendar/events', headers={'X-API-KEY': 'editor_api_key'}, json={
        **EVENT, 'visibility': visibility, 'user_id': admin_id, 'org_id': admin_org_id,
    })
    assert response.status_code == 201
    event = response.json['event']
    with app.app_context():
        owner = User.query.filter_by(api_key='editor_api_key').one()
        saved = db.session.get(Calendar_Event, event['id'])
        assert saved.user_id == owner.id
        assert saved.org_id == (owner.org_id if visibility == 'organisation' else None)
    assert client.get('/calendar/events', query_string=SEPTEMBER).json['events'] == []
    share_org(client, app, 'read_api_key')
    login(client, app, 'read_api_key')
    visible = client.get('/calendar/events', query_string=SEPTEMBER).json['events']
    assert visible == ([{**event, 'can_edit': False}] if visibility == 'organisation' else [])
    feed = client.get('/api/calendar/feed', headers={'X-API-KEY': 'read_api_key'}).get_data(as_text=True)
    assert (f"UID:event-{event['id']}@flowintel" in feed) == (visibility == 'organisation')


@pytest.mark.parametrize('api_key', [None, 'invalid_api_key', 'read_api_key'])
def test_api_event_creation_requires_writable_api_key_even_with_admin_session(client, app, api_key):
    login(client, app, 'admin_api_key')
    headers = {'X-API-KEY': api_key} if api_key else {}
    response = client.post('/api/calendar/events', headers=headers, json=EVENT)
    assert response.status_code == 403
    with app.app_context():
        assert Calendar_Event.query.count() == 0


def test_api_timed_events_and_exclusive_all_day_end(client):
    headers = {'X-API-KEY': 'editor_api_key'}
    for end, expected_end in [(None, '2026-09-25T08:30:00Z'), ('2026-09-25T10:00:00+02:00', '2026-09-25T08:00:00Z')]:
        response = client.post('/api/calendar/events', headers=headers, json={
            **EVENT, 'all_day': False, 'start': '2026-09-25T09:30:00+02:00', 'end': end,
        })
        assert response.status_code == 201
        assert response.json['event']['start'] == '2026-09-25T07:30:00Z'
        assert response.json['event']['end'] == expected_end
    response = client.post('/api/calendar/events', headers=headers, json={**EVENT, 'end': '2026-09-28'})
    assert response.status_code == 201
    assert response.json['event']['end'] == '2026-09-28'


def test_api_invalid_manual_events_do_not_create_records(client, app):
    headers = {'X-API-KEY': 'editor_api_key'}
    for payload in [
        None, [], {}, {**EVENT, 'title': '  '}, {**EVENT, 'title': 'x' * 256},
        {**EVENT, 'start': '2026-02-30'}, {**EVENT, 'end': EVENT['start']},
        {**EVENT, 'all_day': 'false'}, {**EVENT, 'visibility': 'public'},
        {**EVENT, 'description': {}}, {**EVENT, 'all_day': False, 'start': '2026-09-25T10:00:00'},
    ]:
        response = client.post('/api/calendar/events', headers=headers, json=payload)
        assert response.status_code == 400
        assert response.json['message']
    malformed = client.post('/api/calendar/events', headers=headers, data='{', content_type='application/json')
    assert malformed.status_code == 400
    with app.app_context():
        assert Calendar_Event.query.count() == 0


def test_api_calendar_event_creation_documented_in_swagger(client):
    response = client.get('/api/swagger.json')
    assert response.status_code == 200
    operation = response.json['paths']['/calendar/events']['post']
    assert '201' in operation['responses']
    body = next(param for param in operation['parameters'] if param['in'] == 'body')
    model_name = body['schema']['$ref'].rsplit('/', 1)[-1]
    model = response.json['definitions'][model_name]
    assert set(model['required']) == {'title', 'start'}
    assert model['properties']['visibility']['enum'] == ['private', 'organisation']
