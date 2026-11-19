"""Ascending/descending order of the case index (/case/sort_cases) holds across pages."""
from app.case.CaseCore import CaseCore
from app.db_class.db import User

ADMIN_KEY = "admin_api_key"


def _create(client, title):
    r = client.post("/api/case/create", content_type='application/json',
                    headers={"X-API-KEY": ADMIN_KEY}, json={"title": title})
    assert r.status_code == 201
    return r.json["case_id"]



def test_sort_order_is_global_not_per_page(app, client):
    ids = [_create(client, f"Order case {i:02d}") for i in range(30)]
    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        core = CaseCore()
        desc_p1, nb = core.sort_cases(1, False, filter="id", user=admin)
        asc_p1, nb_asc = core.sort_cases(1, False, filter="id", user=admin, order="asc")
        assert nb == nb_asc == 2
        assert [c.id for c in desc_p1][0] == max(ids)
        assert [c.id for c in asc_p1][0] == min(ids)
        assert [c.id for c in asc_p1] == sorted(c.id for c in asc_p1)


def test_sort_title_asc(app, client):
    for t in ["Bravo", "alpha", "Charlie"]:
        _create(client, t)
    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        cases, _ = CaseCore().sort_cases(1, False, filter="title", user=admin, order="asc")
        assert [c.title for c in cases] == ["alpha", "Bravo", "Charlie"]


def test_per_page(app, client):
    for i in range(12):
        _create(client, f"Per page {i}")
    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        core = CaseCore()
        cases, nb = core.sort_cases(1, False, user=admin, per_page=10)
        assert len(cases) == 10 and nb == 2
        # an unknown size falls back to 25
        cases, nb = core.sort_cases(1, False, user=admin, per_page=7)
        assert len(cases) == 12 and nb == 1


def test_total_counts_only_visible_cases(app, client):
    """A non-admin outside a private case's orgs neither sees it nor counts it."""
    from app.db_class.db import db, Case
    ids = [_create(client, f"Visible {i}") for i in range(5)]
    with app.app_context():
        admin = User.query.filter_by(api_key=ADMIN_KEY).first()
        editor = User.query.filter_by(api_key="editor_api_key").first()
        assert editor.org_id != admin.org_id
        for cid in ids[:2]:
            db.session.get(Case, cid).is_private = True
        db.session.commit()
        core = CaseCore()
        _, _, admin_total = core.sort_cases(1, False, user=admin, with_total=True)
        cases, _, editor_total = core.sort_cases(1, False, user=editor, with_total=True)
        assert admin_total - editor_total == 2
        assert editor_total == len(cases)
        assert not {c.id for c in cases} & set(ids[:2])
