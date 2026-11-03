"""PostgreSQL: curtidas simultâneas da mesma pessoa contam uma (PR 3).

A unicidade (post_id, user_id) do banco é quem garante; o serviço trata o
conflito sem erro. Roda só no job PostgreSQL do CI (banco descartável).
"""

import os
import threading
import time

import pytest
from sqlalchemy import delete, func, select

from app import create_app
from app.extensions import db
from app.models.profile import ClientProfile
from app.models.user import User, UserRole
from app.models.work_post import WorkPost, WorkPostAuthorType, WorkPostLike, WorkPostStatus
from app.services import post_interactions


TEST_URL = os.environ.get("IDDUN_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not TEST_URL,
    reason="Requires an isolated PostgreSQL database in IDDUN_TEST_POSTGRES_URL",
)


@pytest.fixture()
def pg_app():
    flask_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "qa-postgres-social-secret",
        "SQLALCHEMY_DATABASE_URI": TEST_URL,
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        author = User(name="Autora PG", email="pg-social-author@example.com", role=UserRole.CLIENT)
        fan = User(name="Fã PG", email="pg-social-fan@example.com", role=UserRole.CLIENT)
        author.set_password("strong-test-password")
        fan.set_password("strong-test-password")
        db.session.add_all([author, fan])
        db.session.flush()
        profile = ClientProfile(user_id=author.id)
        db.session.add(profile)
        db.session.flush()
        post = WorkPost(
            author_type=WorkPostAuthorType.CLIENT,
            client_profile_id=profile.id,
            created_by_user_id=author.id,
            caption="Post para curtida concorrente",
            status=WorkPostStatus.PUBLISHED,
        )
        db.session.add(post)
        db.session.commit()
        ids = {"author": author.id, "fan": fan.id, "post": post.id, "profile": profile.id}
    yield flask_app, ids
    with flask_app.app_context():
        db.session.execute(delete(WorkPostLike).where(WorkPostLike.post_id == ids["post"]))
        db.session.execute(delete(WorkPost).where(WorkPost.id == ids["post"]))
        db.session.execute(delete(ClientProfile).where(ClientProfile.id == ids["profile"]))
        db.session.execute(delete(User).where(User.id.in_([ids["author"], ids["fan"]])))
        db.session.commit()
        db.session.remove()


def test_postgresql_concurrent_likes_count_once(pg_app, monkeypatch):
    flask_app, ids = pg_app
    original = post_interactions._visible_post

    def slow_visible(post_id):
        # Alarga a janela: as duas requisições leem "sem curtida" antes de gravar.
        post = original(post_id)
        time.sleep(0.3)
        return post

    monkeypatch.setattr(post_interactions, "_visible_post", slow_visible)
    start = threading.Barrier(3)
    results, failures = [], []

    def like():
        with flask_app.app_context():
            try:
                user = db.session.get(User, ids["fan"])
                start.wait(timeout=10)
                results.append(post_interactions.set_like(user, ids["post"], True))
            except Exception as exc:  # pragma: no cover - reportado abaixo
                failures.append(exc)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=like) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert not failures, failures
    assert [item["liked"] for item in results] == [True, True, True]
    with flask_app.app_context():
        total = db.session.scalar(
            select(func.count(WorkPostLike.id)).where(WorkPostLike.post_id == ids["post"])
        )
        assert total == 1
