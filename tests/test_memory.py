"""Tests for AIION memory subsystem: persistence, cognitive index, RAM guard."""
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


# =============================================================================
# TESTS: MemoryPersistence
# =============================================================================

class TestMemoryPersistence:
    """Tests for aiion.memory.persistence.MemoryPersistence."""

    def test_init_creates_files(self, config_module):
        """Verifica que la inicialización crea archivos necesarios."""
        from aiion.memory.persistence import MemoryPersistence
        
        persistence = MemoryPersistence()
        
        assert config_module.MEMORY_FILE.exists()
        assert config_module.HISTORY_FILE.exists()
        assert config_module.SENSOR_DB.exists()
    
    def test_remember_and_recall(self, config_module, memory_persistence):
        """Test básico de recordar y recuperar hechos."""
        fact = "El usuario prefiere café con leche"
        memory_persistence.remember(fact)
        
        # Verificar que se escribió en el archivo
        content = config_module.MEMORY_FILE.read_text()
        assert fact in content
        
        # Verificar recall
        recalled = memory_persistence.recall()
        assert fact in recalled
    
    def test_remember_multiple_facts(self, config_module, memory_persistence):
        """Múltiples hechos se acumulan."""
        facts = [
            "Hecho 1: El usuario vive en Madrid",
            "Hecho 2: Le gusta Python",
            "Hecho 3: Usa Termux en Android"
        ]
        
        for fact in facts:
            memory_persistence.remember(fact)
        
        content = config_module.MEMORY_FILE.read_text()
        for fact in facts:
            assert fact in content
    
    def test_history_append_and_search(self, config_module, memory_persistence):
        """Test de historial conversacional y búsqueda."""
        # Añadir entradas al historial
        memory_persistence.append_history("user", "Hola")
        memory_persistence.append_history("agent", "¡Hola! ¿En qué te ayudo?")
        memory_persistence.append_history("user", "¿Cuál es la capital de Francia?")
        memory_persistence.append_history("agent", "París es la capital de Francia.")
        
        # Verificar archivo JSONL
        lines = config_module.HISTORY_FILE.read_text().strip().split('\n')
        assert len(lines) == 4
        
        # Buscar en historial
        results = memory_persistence.history_search("capital")
        assert len(results) >= 1  # Puede encontrar pregunta y/o respuesta
        # Verificar que al menos uno contiene la palabra
        assert any("capital" in (r.get("user","") + r.get("agent","")) for r in results)
    
    def test_history_max_limit(self, config_module, memory_persistence):
        """Verifica que el historial respeta MAX_HISTORY."""
        from aiion import config
        original_max = config.MAX_HISTORY
        config.MAX_HISTORY = 3
        
        try:
            for i in range(5):
                memory_persistence.append_history("user", f"Mensaje {i}")
                memory_persistence.append_history("agent", f"Respuesta {i}")
            
            lines = config_module.HISTORY_FILE.read_text().strip().split('\n')
            # MAX_HISTORY = 3 significa 3 pares user/agent = 6 líneas
            assert len(lines) <= 6
        finally:
            config.MAX_HISTORY = original_max
    
    def test_tfidf_search(self, config_module, memory_persistence):
        """Test de búsqueda semántica TF-IDF."""
        # Poblar con contenido variado
        docs = [
            "Python es un lenguaje de programación popular",
            "JavaScript se usa en desarrollo web",
            "Rust es un lenguaje de sistemas seguro",
            "Go es bueno para concurrencia",
        ]
        for doc in docs:
            memory_persistence.remember(doc)
        
        # Buscar términos relacionados
        results = memory_persistence.history_search("programación")
        assert len(results) > 0
        
        results = memory_persistence.history_search("sistemas")
        assert len(results) > 0
        assert any("Rust" in str(r) for r in results)
    
    def test_clear_history(self, config_module, memory_persistence):
        """Test de limpieza de historial."""
        memory_persistence.append_history("user", "test")
        memory_persistence.append_history("agent", "response")
        
        memory_persistence.clear_history()
        
        assert config_module.HISTORY_FILE.read_text() == ""
    
    def test_clear_memory(self, config_module, memory_persistence):
        """Test de limpieza de memoria de hechos."""
        memory_persistence.remember("Hecho de prueba")
        memory_persistence.clear_memory()
        
        assert config_module.MEMORY_FILE.read_text() == ""


# =============================================================================
# TESTS: CognitiveIndex
# =============================================================================

class TestCognitiveIndex:
    """Tests for aiion.memory.cognitive_index.CognitiveIndex."""

    def test_index_file_read(self, config_module, cognitive_index, temp_dir):
        """Registra archivo leído y verifica índice."""
        test_file = temp_dir / "test_module.py"
        test_file.write_text("def hello(): return 'world'\n")
        
        cognitive_index.record_read(str(test_file))
        
        indexed = cognitive_index.get_indexed_files()
        assert str(test_file) in indexed
        assert indexed[str(test_file)]['reads'] == 1
        assert indexed[str(test_file)]['writes'] == 0
    
    def test_index_file_write(self, config_module, cognitive_index, temp_dir):
        """Registra archivo escrito y verifica índice."""
        test_file = temp_dir / "output.txt"
        test_file.write_text("contenido")
        
        cognitive_index.record_write(str(test_file))
        
        indexed = cognitive_index.get_indexed_files()
        assert str(test_file) in indexed
        assert indexed[str(test_file)]['writes'] == 1
        assert indexed[str(test_file)]['reads'] == 0
    
    def test_index_multiple_operations(self, config_module, cognitive_index, temp_dir):
        """Múltiples lecturas/escrituras incrementan contadores."""
        test_file = temp_dir / "multi.py"
        test_file.write_text("# init\n")
        
        cognitive_index.record_read(str(test_file))
        cognitive_index.record_read(str(test_file))
        cognitive_index.record_write(str(test_file))
        
        indexed = cognitive_index.get_indexed_files()
        assert indexed[str(test_file)]['reads'] == 2
        assert indexed[str(test_file)]['writes'] == 1
    
    def test_get_recent_files(self, config_module, cognitive_index, temp_dir):
        """Obtiene archivos recientes ordenados por timestamp."""
        files = [temp_dir / f"file{i}.py" for i in range(3)]
        for f in files:
            f.write_text(f"# {f.name}\n")
        
        for f in files:
            cognitive_index.record_read(str(f))
            time.sleep(0.01)  # Asegurar timestamps diferentes
        
        recent = cognitive_index.get_recent_files(limit=2)
        assert len(recent) == 2
        # El más reciente debe ser el último
        assert recent[0] == str(files[-1])
    
    def test_clear_index(self, config_module, cognitive_index, temp_dir):
        """Limpia el índice completamente."""
        test_file = temp_dir / "clear_test.py"
        test_file.write_text("test")
        cognitive_index.record_read(str(test_file))
        
        cognitive_index.clear()
        
        assert cognitive_index.get_indexed_files() == {}
    
    def test_persistence_across_instances(self, config_module, temp_dir):
        """El índice persiste entre instancias (archivo JSON)."""
        from aiion.memory.cognitive_index import CognitiveIndex
        
        test_file = temp_dir / "persist.py"
        test_file.write_text("persist")
        
        idx1 = CognitiveIndex()
        idx1.record_read(str(test_file))
        
        # Nueva instancia debe cargar el índice existente
        idx2 = CognitiveIndex()
        indexed = idx2.get_indexed_files()
        
        assert str(test_file) in indexed
        assert indexed[str(test_file)]['reads'] == 1


# =============================================================================
# TESTS: RAMGuard
# =============================================================================

class TestRAMGuard:
    """Tests for aiion.memory.ram_guard.RAMGuard."""

    def test_start_stop(self, ram_guard):
        """Inicia y detiene el monitor sin errores."""
        ram_guard.start()
        time.sleep(0.1)
        ram_guard.stop()
        # No debe lanzar excepción
    
    def test_get_stats(self, ram_guard):
        """Obtiene estadísticas de memoria."""
        ram_guard.start()
        time.sleep(0.1)
        
        stats = ram_guard.get_stats()
        
        assert 'ram_percent' in stats
        assert 'ram_available_mb' in stats
        assert 'ram_total_mb' in stats
        assert 'swap_percent' in stats
        assert isinstance(stats['ram_percent'], float)
        assert 0 <= stats['ram_percent'] <= 100
        
        ram_guard.stop()
    
    def test_wake_lock_acquire_release(self, ram_guard):
        """Wake lock se adquiere y libera correctamente."""
        # En entorno sin termux, debe manejar graceful
        ram_guard.acquire_wake_lock()
        ram_guard.release_wake_lock()
        # No debe lanzar excepción
    
    def test_cleanup_zombies(self, ram_guard, mock_psutil):
        """Limpieza de procesos zombis (mock)."""
        mock_proc = MagicMock()
        mock_proc.status.return_value = 'zombie'
        mock_proc.pid = 99999
        mock_psutil.process_iter.return_value = [mock_proc]
        
        # No debe lanzar excepción aunque no pueda matar
        ram_guard.cleanup_zombies()
    
    def test_ram_trend(self, ram_guard):
        """Detecta tendencia de memoria."""
        ram_guard.start()
        time.sleep(0.2)
        
        trend = ram_guard.get_trend()
        assert trend in ['increasing', 'decreasing', 'stable']
        
        ram_guard.stop()
    
    def test_swap_alert(self, ram_guard, mock_psutil):
        """Alerta si swap está alto."""
        mock_psutil.swap_memory.return_value.percent = 95.0
        
        ram_guard.start()
        time.sleep(0.1)
        
        alert = ram_guard.check_swap_alert()
        assert alert is True
        
        ram_guard.stop()
    
    def test_low_memory_warning(self, ram_guard, mock_psutil):
        """Advertencia si memoria disponible es baja."""
        mock_psutil.virtual_memory.return_value.available = 50 * 1024 * 1024  # 50 MB
        mock_psutil.virtual_memory.return_value.percent = 95.0
        mock_psutil.virtual_memory.return_value.total = 4 * 1024 * 1024 * 1024
        
        ram_guard.start()
        time.sleep(0.1)
        
        warning = ram_guard.check_low_memory()
        assert warning is True
        
        ram_guard.stop()


# =============================================================================
# TESTS DE INTEGRACIÓN MEMORIA
# =============================================================================

class TestMemoryIntegration:
    """Tests de integración entre componentes de memoria."""

    def test_persistence_and_index_together(self, config_module, memory_persistence, cognitive_index, temp_dir):
        """Persistencia e índice trabajan juntos."""
        test_file = temp_dir / "integration_test.py"
        test_file.write_text("print('hello')\n")
        
        # Leer archivo -> indexar
        content = test_file.read_text()
        cognitive_index.record_read(str(test_file))
        
        # Recordar hecho sobre el archivo
        memory_persistence.remember(f"Archivo {test_file.name} contiene: {content[:20]}")
        
        # Verificar ambos
        assert str(test_file) in cognitive_index.get_indexed_files()
        assert test_file.name in memory_persistence.recall()
    
    def test_history_and_tfidf_consistency(self, config_module, memory_persistence):
        """Historial y búsqueda TF-IDF son consistentes."""
        conversations = [
            ("user", "Quiero aprender Python"),
            ("agent", "Python es excelente para principiantes"),
            ("user", "¿Y para ciencia de datos?"),
            ("agent", "Sí, pandas y numpy son estándar"),
        ]
        
        for role, msg in conversations:
            memory_persistence.append_history(role, msg)
        
        # Búsqueda debe encontrar ambos mensajes relevantes
        results = memory_persistence.history_search("Python")
        assert len(results) >= 1
        
        results = memory_persistence.history_search("pandas")
        assert len(results) >= 1
