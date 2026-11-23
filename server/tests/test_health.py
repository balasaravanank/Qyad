from fastapi.testclient import TestClient
from app.main import app

def test_public_health_has_no_data_and_is_not_cached():
    response=TestClient(app).get('/api/v1/health')
    assert response.status_code==200
    assert response.json()=={'ok':True}
    assert response.headers['cache-control']=='no-store'
