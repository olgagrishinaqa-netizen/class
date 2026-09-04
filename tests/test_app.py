import pytest
from app import app

@pytest.fixture
def client():
    # Настраиваем Flask-приложение для режима тестирования
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_page_status_code(client):
    """Тест проверяет, что главная страница (авторизация) доступна и возвращает код 200"""
    response = client.get('/')
    assert response.status_code == 200

def test_contacts_page_status_code(client):
    """Тест проверяет, что неавторизованный доступ к контактам перенаправляет на логин (302)"""
    response = client.get('/contacts', follow_redirects=False)
    assert response.status_code == 302
