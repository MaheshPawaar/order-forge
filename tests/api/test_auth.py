import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "S3cure-pass-123"


def register(client, **override):
    payload = {"username": "bob", "email": "bob@example.com", "password": PASSWORD, **override}
    return client.post("/api/v1/auth/register", payload, format="json")


def login(client, password=PASSWORD):
    payload = {"username": "bob", "password": password}
    return client.post("/api/v1/auth/login", payload, format="json")


def test_user_creates_user_with_hashed_password(api_client):
    response = register(api_client)

    assert response.status_code == 201
    assert "password" not in response.data
    user = User.objects.get(username="bob")
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)


def test_register_cannot_create_staff(api_client):
    response = register(api_client, is_staff=True, is_superuser=True)

    assert response.status_code == 201
    user = User.objects.get(username="bob")
    assert not user.is_staff
    assert not user.is_superuser


def test_register_rejects_duplicate_username(api_client):
    register(api_client)

    response = register(api_client, email="other@example.com")

    assert response.status_code == 400
    assert "username" in response.data


def test_register_rejects_weak_password(api_client):
    response = register(api_client, password="123")

    assert response.status_code == 400
    assert "password" in response.data
    assert not User.objects.filter(username="bob").exists()


def test_login_returns_access_and_refresh(api_client):
    register(api_client)

    response = login(api_client)

    assert response.status_code == 200
    assert {"access", "refresh"} <= response.data.keys()


def test_login_rejects_wrong_password(api_client):
    register(api_client)

    response = login(api_client, password="wrong-password")

    assert response.status_code == 401


def test_refresh_returns_new_access_token(api_client):
    register(api_client)
    refresh = login(api_client).data["refresh"]

    response = api_client.post("/api/v1/auth/refresh", {"refresh": refresh}, format="json")

    assert response.status_code == 200
    assert "access" in response.data
