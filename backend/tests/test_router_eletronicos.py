from http import HTTPStatus

from fastapi.testclient import TestClient

from backend.app import app

PREFIX = '/eletronicos'


def test_root_deve_retornar_lista():
    client = TestClient(app)

    response = client.get(f'{PREFIX}/')

    assert response.json() == {'message': 'Lista de eletrônicos'}
    assert response.status_code == HTTPStatus.OK
