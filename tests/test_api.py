"""
Testes para os endpoints da API.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app import app

# Cliente de teste
client = TestClient(app)

# API Key de teste
TEST_API_KEY = "test-api-key"

# Headers padrão para testes
headers = {"X-API-Key": TEST_API_KEY}

def test_generate_video():
    """Testa o endpoint de geração de vídeo."""
    with patch("app.store_job") as mock_store, \
         patch("app.generate_video_task") as mock_task:
        
        # Prepara o mock
        mock_store.return_value = None
        mock_task.delay.return_value = None
        
        # Dados de teste
        payload = {
            "comment": "Vídeo de teste",
            "resolution": "hd",
            "quality": "high",
            "scenes": [
                {
                    "background_color": "#000000",
                    "elements": [
                        {
                            "type": "image",
                            "src": "https://exemplo.com/imagem.jpg"
                        }
                    ]
                }
            ]
        }
        
        # Faz a requisição
        response = client.post("/generate-video", json=payload, headers=headers)
        
        # Verifica resposta
        assert response.status_code == 202
        assert "job_id" in response.json()
        assert response.json()["status"] == "queued"
        
        # Verifica se as funções foram chamadas
        mock_store.assert_called_once()
        mock_task.delay.assert_called_once()

def test_generate_image():
    """Testa o endpoint de geração de imagem."""
    with patch("app.store_job") as mock_store, \
         patch("app.generate_image_task") as mock_task:
        
        # Dados de teste
        payload = {
            "image_prompt": "Uma paisagem de montanhas",
            "width": 1280,
            "height": 720,
            "steps": 25
        }
        
        # Faz a requisição
        response = client.post("/generate-image", json=payload, headers=headers)
        
        # Verifica resposta
        assert response.status_code == 202
        assert "job_id" in response.json()
        assert response.json()["status"] == "queued"

def test_generate_tts():
    """Testa o endpoint de geração de áudio TTS."""
    with patch("app.store_job") as mock_store, \
         patch("app.generate_tts_task") as mock_task:
        
        # Dados de teste
        payload = {
            "text": "Olá, este é um teste de áudio",
            "language": "pt-BR",
            "voice": "male_1"
        }
        
        # Faz a requisição
        response = client.post("/generate-tts", json=payload, headers=headers)
        
        # Verifica resposta
        assert response.status_code == 202
        assert "job_id" in response.json()
        assert response.json()["status"] == "queued"
        assert "estimated_duration" in response.json()

def test_get_job_status():
    """Testa o endpoint de consulta de status."""
    with patch("app.get_job_status") as mock_get:
        # Configura mock
        mock_get.return_value = {
            "job_id": "test-123",
            "status": "processing",
            "progress": {"completed": 50, "total": 100}
        }
        
        # Faz a requisição
        response = client.get("/status/test-123", headers=headers)
        
        # Verifica resposta
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        assert "progress" in response.json()

def test_get_job_result():
    """Testa o endpoint de resultado do job."""
    with patch("app.get_job_status") as mock_get, \
         patch("app.get_presigned_url") as mock_url:
        
        # Configura mocks
        mock_get.return_value = {
            "job_id": "test-123",
            "status": "completed",
            "result": {
                "images": ["img1", "img2"],
                "audios": ["audio1"]
            }
        }
        mock_url.return_value = "https://minio.exemplo.com/arquivo.mp4"
        
        # Faz a requisição
        response = client.get("/result/test-123", headers=headers)
        
        # Verifica resposta
        assert response.status_code == 200
        assert "result_url" in response.json()
        assert "files" in response.json()
        assert "images" in response.json()["files"]
        assert "audios" in response.json()["files"]

def test_health_check():
    """Testa o endpoint de health check."""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert "status" in response.json()
    assert "version" in response.json()
    assert "uptime" in response.json()
    assert "database_status" in response.json()
    assert "redis_status" in response.json()
    assert "minio_status" in response.json()

def test_invalid_api_key():
    """Testa autenticação com API Key inválida."""
    response = client.post(
        "/generate-video",
        json={},
        headers={"X-API-Key": "invalid-key"}
    )
    
    assert response.status_code == 401
    assert "message" in response.json()["detail"]
    assert response.json()["detail"]["type"] == "authentication_error"

def test_missing_api_key():
    """Testa requisição sem API Key."""
    response = client.post("/generate-video", json={})
    
    assert response.status_code == 422  # FastAPI validation error
    assert "detail" in response.json()

@pytest.mark.parametrize("endpoint", [
    "/generate-video",
    "/generate-image",
    "/generate-tts"
])
def test_invalid_payload(endpoint):
    """Testa validação de payload inválido em diferentes endpoints."""
    response = client.post(endpoint, json={}, headers=headers)
    
    assert response.status_code == 422
    assert "detail" in response.json()

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 