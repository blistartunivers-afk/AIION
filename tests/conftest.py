"""pytest configuration and shared fixtures for AIION tests."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Asegurar que aiion es importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES GLOBALES
# =============================================================================

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Raíz del proyecto AIION."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def aiion_data_dir(project_root) -> Path:
    """Directorio de datos de AIION (aislado para tests)."""
    return project_root / "data"


@pytest.fixture
def temp_dir() -> Path:
    """Directorio temporal único por test."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_termux_api():
    """Mock de termux-api para tests sin dispositivo Android."""
    with patch("subprocess.run") as mock_run:
        # Configurar respuestas por defecto para comandos comunes
        def side_effect(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            
            if "termux-battery-status" in cmd_str:
                mock_result.stdout = '{"percentage": 85, "status": "DISCHARGING", "temperature": 30.0, "health": "GOOD"}'
            elif "termux-wifi-connectioninfo" in cmd_str:
                mock_result.stdout = '{"ssid": "TEST_WIFI", "bssid": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.100", "link_speed": 72}'
            elif "termux-system-info" in cmd_str:
                mock_result.stdout = '{"arch": "aarch64", "manufacturer": "Google", "model": "Pixel", "version": {"sdk": 34, "release": "14"}}'
            elif "termux-location" in cmd_str:
                mock_result.stdout = '{"latitude": 40.4168, "longitude": -3.7038, "accuracy": 10.0, "provider": "network"}'
            elif "termux-sensor" in cmd_str:
                mock_result.stdout = '[{"name": "accelerometer", "values": [0.0, 9.8, 0.0], "timestamp": 1234567890}]'
            elif "termux-clipboard-get" in cmd_str:
                mock_result.stdout = "clipboard content"
            elif "termux-notification-list" in cmd_str:
                mock_result.stdout = '[]'
            elif "termux-sms-list" in cmd_str:
                mock_result.stdout = '[]'
            elif "termux-call-log" in cmd_str:
                mock_result.stdout = '[]'
            elif "termux-telephony-deviceinfo" in cmd_str:
                mock_result.stdout = '{"device_id": "test123", "sim_serial": "sim123", "phone_number": "+123456789"}'
            elif "termux-camera-info" in cmd_str:
                mock_result.stdout = '[{"id": 0, "facing": "back"}, {"id": 1, "facing": "front"}]'
            
            return mock_result
        
        mock_run.side_effect = side_effect
        yield mock_run


@pytest.fixture
def mock_ollama_local():
    """Mock de Ollama local (localhost:11434)."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"models": [{"name": "qwen3-coder:latest", "size": 4000000000}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        yield mock_urlopen


@pytest.fixture
def mock_ollama_cloud():
    """Mock de Ollama Cloud API."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"models": [{"name": "qwen3-coder:480b", "size": 480000000000}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        yield mock_urlopen


@pytest.fixture
def mock_groq_tts():
    """Mock de Groq TTS API."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake_audio_data"
        mock_response.headers.get.return_value = "audio/mpeg"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        yield mock_urlopen


# =============================================================================
# FIXTURES DE MÓDULOS AIION
# =============================================================================

@pytest.fixture
def config_module():
    """Módulo config con paths temporales."""
    from aiion import config
    original_home = config.AIION_HOME
    with tempfile.TemporaryDirectory() as tmp:
        config.AIION_HOME = Path(tmp) / "AIION" / "data"
        config.AIION_HOME.mkdir(parents=True, exist_ok=True)
        config.MEMORY_FILE = config.AIION_HOME / "aiion_memory.md"
        config.HISTORY_FILE = config.AIION_HOME / "aiion_history.jsonl"
        config.SENSOR_DB = config.AIION_HOME / "aiion_sensor_data.db"
        yield config
    # Restaurar
    config.AIION_HOME = original_home
    config.MEMORY_FILE = original_home / "aiion_memory.md"
    config.HISTORY_FILE = original_home / "aiion_history.jsonl"
    config.SENSOR_DB = original_home / "aiion_sensor_data.db"


@pytest.fixture
def memory_persistence(config_module):
    """Instancia de MemoryPersistence con archivos temporales."""
    from aiion.memory.persistence import MemoryPersistence
    return MemoryPersistence()


@pytest.fixture
def cognitive_index(config_module):
    """Instancia de CognitiveIndex con archivos temporales."""
    from aiion.memory.cognitive_index import CognitiveIndex
    return CognitiveIndex()


@pytest.fixture
def ram_guard(config_module):
    """Instancia de RAMGuard para tests."""
    from aiion.memory.ram_guard import RAMGuard
    guard = RAMGuard()
    yield guard
    guard.stop()


@pytest.fixture
def sensor_collectors(config_module, mock_termux_api):
    """Instancia de SensorCollectors con termux-api mockeado."""
    from aiion.sensors.collectors import SensorCollectors
    return SensorCollectors()


@pytest.fixture
def sensor_daemon(config_module, mock_termux_api):
    """Instancia de SensorDaemon con termux-api mockeado."""
    from aiion.sensors.daemon import SensorDaemon
    daemon = SensorDaemon()
    yield daemon
    daemon.stop()


@pytest.fixture
def tts_engine(config_module, mock_groq_tts):
    """Instancia de TTSEngine con Groq mockeado."""
    from aiion.voice.tts import TTSEngine
    return TTSEngine()


@pytest.fixture
def stt_engine(config_module, mock_termux_api):
    """Instancia de STTEngine con termux-speech-to-text mockeado."""
    from aiion.voice.stt import STTEngine
    return STTEngine()


@pytest.fixture
def llm_client(config_module, mock_ollama_local, mock_ollama_cloud):
    """Instancia de LLMClient con Ollama mockeado."""
    from aiion.llm.client import LLMClient
    return LLMClient()


@pytest.fixture
def tool_registry(config_module, mock_termux_api):
    """Registry de tools con dependencias mockeadas."""
    from aiion.tools.registry import ToolRegistry
    return ToolRegistry()


# =============================================================================
# HELPERS PARA TESTS
# =============================================================================

class MockSubprocess:
    """Helper para mockear subprocess.run con respuestas personalizadas."""
    def __init__(self):
        self.responses = {}
    
    def add_response(self, cmd_contains: str, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.responses[cmd_contains] = (stdout, stderr, returncode)
    
    def __call__(self, cmd, *args, **kwargs):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        for key, (stdout, stderr, rc) in self.responses.items():
            if key in cmd_str:
                result = MagicMock()
                result.stdout = stdout
                result.stderr = stderr
                result.returncode = rc
                return result
        # Default
        result = MagicMock()
        result.stdout = ""
        result.stderr = ""
        result.returncode = 0
        return result


@pytest.fixture
def mock_subprocess():
    """Fixture que provee MockSubprocess configurable."""
    return MockSubprocess()


@pytest.fixture
def mock_psutil():
    """Mock de psutil para tests sin instalar la librería."""
    mock_module = MagicMock()
    
    # Mock process_iter
    mock_proc = MagicMock()
    mock_proc.status.return_value = 'running'
    mock_proc.pid = 12345
    mock_module.process_iter.return_value = [mock_proc]
    
    # Mock swap_memory
    mock_swap = MagicMock()
    mock_swap.percent = 10.0
    mock_module.swap_memory.return_value = mock_swap
    
    # Mock virtual_memory
    mock_vm = MagicMock()
    mock_vm.percent = 45.0
    mock_vm.available = 2000000000
    mock_vm.total = 4000000000
    mock_module.virtual_memory.return_value = mock_vm
    
    with patch.dict('sys.modules', {'psutil': mock_module}):
        yield mock_module


# =============================================================================
# MARKERS PERSONALIZADOS
# =============================================================================

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external deps)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (may need termux-api)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take >5 seconds"
    )
    config.addinivalue_line(
        "markers", "android: Tests requiring Android/Termux environment"
    )
    config.addinivalue_line(
        "markers", "llm: Tests requiring LLM API (mocked or real)"
    )
    config.addinivalue_line(
        "markers", "voice: Tests requiring TTS/STT"
    )
    config.addinivalue_line(
        "markers", "sensor: Tests requiring sensor daemon/collectors"
    )


# =============================================================================
# CLEANUP AUTOMÁTICO
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Limpia singletons globales entre tests."""
    yield
    # Limpiar módulos que usan estado global
    import aiion.config as config_module
    import aiion.memory.ram_guard as ram_guard_module
    import aiion.sensors.daemon as daemon_module
    
    # Resetear instancias globales si existen
    for module in [config_module, ram_guard_module, daemon_module]:
        for attr in dir(module):
            obj = getattr(module, attr)
            if hasattr(obj, 'stop') and callable(obj.stop):
                try:
                    obj.stop()
                except Exception:
                    pass
