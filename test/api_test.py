'''注：函数名为 test_* 才会发现，*_test不成。'''

def test_one():
    assert 1 == 1

def test_hello(app):
    with app.test_client() as c:
        r = c.get('/api/hello')
        assert r.status_code == 200
    
def test_db_create_user(client):
    from strong import db 
    from strong.models import User 
    user = User(name='test', password='test')
    db.session.add(user)
    db.session.commit()
    
    userc = User.query.filter_by(name='test').first()
    assert userc.name == 'test'

def test_login(client):
    r = client.post('/api/oauth/token')

def test_todo_get(client):
    pass

def test_todo_post(client):
    pass

def test_todo_delete(client):
    pass

def test_todo_put(client):
    pass


