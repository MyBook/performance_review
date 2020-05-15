from apps.reviews.factories import IntervalFactory, UserFactory


def test_no_current_interval(db, client):
    IntervalFactory(name='2018Q1', finished=True)
    IntervalFactory(name='2018Q2', finished=True)
    IntervalFactory(name='2018Q3', pending=True)
    client.force_login(user=UserFactory())
    response = client.get('/about/')
    assert response.status_code == 200


def test_current_pending_interval(db, client):
    IntervalFactory(name='2018Q1', finished=True)
    IntervalFactory(name='2018Q2', started=True)
    IntervalFactory(name='2018Q3', pending=True)
    client.force_login(user=UserFactory(email='raymond.penners@example.com'))
    response = client.get('/', follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == ('/2018Q2/users/raymond.penners@example.com/', 302)
