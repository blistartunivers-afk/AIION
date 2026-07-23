"""tests/test_filesystem.py — Tests para aiion/tools/filesystem.py."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from aiion.tools.filesystem import (
    tool_read_file,
    tool_write_file,
    tool_replace,
    tool_run_shell_command,
    tool_list_directory,
    tool_glob,
    tool_grep_search,
    tool_web_fetch,
    tool_diff_files,
)


class TestReadFile:
    """Tests para tool_read_file."""

    def test_read_existing_file(self, temp_dir):
        """Lee un archivo existente."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Línea 1\nLínea 2\nLínea 3")
        
        result = tool_read_file(str(test_file))
        
        assert "test.txt" in result
        assert "3 líneas" in result
        assert "Línea 1" in result
        assert "Línea 2" in result
        assert "Línea 3" in result

    def test_read_nonexistent_file(self):
        """Archivo que no existe devuelve error."""
        result = tool_read_file("/ruta/que/no/existe.txt")
        assert "Error: No existe" in result

    def test_read_with_line_range(self, temp_dir):
        """Lee archivo con rango de líneas."""
        test_file = temp_dir / "range.txt"
        test_file.write_text("\n".join([f"Línea {i}" for i in range(1, 11)]))
        
        result = tool_read_file(str(test_file), start_line=3, end_line=5)
        
        assert "3 líneas" in result
        assert "Línea 3" in result
        assert "Línea 5" in result
        assert "Línea 1" not in result
        assert "Línea 10" not in result

    def test_read_empty_file(self, temp_dir):
        """Lee archivo vacío."""
        test_file = temp_dir / "empty.txt"
        test_file.write_text("")
        
        result = tool_read_file(str(test_file))
        assert "0 líneas" in result or "vacio" in result.lower()


class TestWriteFile:
    """Tests para tool_write_file."""

    def test_write_new_file(self, temp_dir):
        """Escribe archivo nuevo."""
        test_file = temp_dir / "new.txt"
        content = "Contenido de prueba"
        
        result = tool_write_file(str(test_file), content)
        
        assert "OK" in result
        assert test_file.exists()
        assert test_file.read_text() == content

    def test_write_creates_backup(self, temp_dir):
        """Escribir sobre archivo existente crea backup .bak."""
        test_file = temp_dir / "existing.txt"
        test_file.write_text("Original")
        
        result = tool_write_file(str(test_file), "Nuevo contenido")
        
        assert "OK" in result
        assert test_file.read_text() == "Nuevo contenido"
        backup = test_file.with_suffix(test_file.suffix + ".bak")
        assert backup.exists()
        assert backup.read_text() == "Original"

    def test_write_creates_parent_dirs(self, temp_dir):
        """Crea directorios padre si no existen."""
        test_file = temp_dir / "subdir" / "nested" / "file.txt"
        
        result = tool_write_file(str(test_file), "Contenido")
        
        assert "OK" in result
        assert test_file.exists()
        assert test_file.read_text() == "Contenido"


class TestReplace:
    """Tests para tool_replace."""

    def test_replace_success(self, temp_dir):
        """Reemplazo exitoso."""
        test_file = temp_dir / "replace.txt"
        test_file.write_text("Hola mundo\nHola universo")
        
        result = tool_replace(str(test_file), "mundo", "Python")
        
        assert "OK" in result
        assert test_file.read_text() == "Hola Python\nHola universo"
        backup = test_file.with_suffix(test_file.suffix + ".bak")
        assert backup.exists()
        assert backup.read_text() == "Hola mundo\nHola universo"

    def test_replace_not_found(self, temp_dir):
        """Texto no encontrado."""
        test_file = temp_dir / "notfound.txt"
        test_file.write_text("Contenido")
        
        result = tool_replace(str(test_file), "inexistente", "nuevo")
        
        assert "Error: Texto no encontrado" in result
        assert test_file.read_text() == "Contenido"  # Sin cambios

    def test_replace_multiple_occurrences(self, temp_dir):
        """Texto aparece múltiples veces - debe fallar."""
        test_file = temp_dir / "multi.txt"
        test_file.write_text("foo bar foo")
        
        result = tool_replace(str(test_file), "foo", "baz")
        
        assert "Error: Texto aparece 2 veces" in result
        assert test_file.read_text() == "foo bar foo"  # Sin cambios


class TestRunShellCommand:
    """Tests para tool_run_shell_command."""

    def test_simple_command(self):
        """Comando simple echo."""
        result = tool_run_shell_command("echo 'hola mundo'")
        assert "hola mundo" in result
        assert "STDOUT" in result

    def test_command_with_stderr(self):
        """Comando que escribe a stderr."""
        result = tool_run_shell_command("echo 'error' >&2")
        assert "STDERR" in result
        assert "error" in result

    def test_command_exit_code(self):
        """Comando con código de salida no cero."""
        result = tool_run_shell_command("false")
        assert "Exit: 1" in result

    def test_timeout(self):
        """Timeout en comando largo."""
        result = tool_run_shell_command("sleep 10", timeout=1)
        assert "Error: Timeout" in result

    def test_nonexistent_command(self):
        """Comando que no existe."""
        result = tool_run_shell_command("comando_que_no_existe_xyz")
        # En Termux/Android 'sh' devuelve el error; aceptamos varios formatos
        assert (
            "not found" in result
            or "Exit: 127" in result
            or "Error" in result
        )


class TestListDirectory:
    """Tests para tool_list_directory."""

    def test_list_directory(self, temp_dir):
        """Lista directorio con archivos y subdirectorios."""
        (temp_dir / "file1.txt").write_text("contenido")
        (temp_dir / "file2.py").write_text("print('hola')")
        (temp_dir / "subdir").mkdir()
        
        result = tool_list_directory(str(temp_dir))
        
        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir" in result
        assert "📄" in result  # icono archivo
        assert "📁" in result  # icono directorio
        assert "B" in result  # tamaño en bytes

    def test_list_nonexistent(self):
        """Directorio que no existe."""
        result = tool_list_directory("/no/existe")
        assert "Error: No existe" in result

    def test_list_hidden_files(self, temp_dir):
        """Lista archivos ocultos con show_hidden=True."""
        (temp_dir / ".hidden").write_text("secreto")
        (temp_dir / "visible.txt").write_text("publico")
        
        result = tool_list_directory(str(temp_dir), show_hidden=True)
        assert ".hidden" in result
        assert "visible.txt" in result
        
        result_no_hidden = tool_list_directory(str(temp_dir), show_hidden=False)
        assert ".hidden" not in result_no_hidden
        assert "visible.txt" in result_no_hidden

    def test_empty_directory(self, temp_dir):
        """Directorio vacío."""
        result = tool_list_directory(str(temp_dir))
        assert "vacío" in result.lower() or "0 entradas" in result


class TestGlob:
    """Tests para tool_glob."""

    def test_glob_pattern(self, temp_dir):
        """Busca archivos con patrón glob."""
        (temp_dir / "test1.py").write_text("#1")
        (temp_dir / "test2.py").write_text("#2")
        (temp_dir / "other.txt").write_text("txt")
        
        result = tool_glob("*.py", str(temp_dir))
        
        assert "2 archivos" in result
        assert "test1.py" in result
        assert "test2.py" in result
        assert "other.txt" not in result

    def test_glob_no_matches(self, temp_dir):
        """Sin coincidencias."""
        result = tool_glob("*.xyz", str(temp_dir))
        assert "Sin resultados" in result

    def test_glob_recursive(self, temp_dir):
        """Glob recursivo con **."""
        (temp_dir / "sub" / "deep.py").parent.mkdir(parents=True)
        (temp_dir / "sub" / "deep.py").write_text("deep")
        (temp_dir / "root.py").write_text("root")
        
        result = tool_glob("**/*.py", str(temp_dir))
        assert "2 archivos" in result
        assert "root.py" in result
        assert "deep.py" in result


class TestGrepSearch:
    """Tests para tool_grep_search."""

    def test_grep_found(self, temp_dir):
        """Encuentra patrón en archivo."""
        test_file = temp_dir / "search.txt"
        test_file.write_text("Línea 1: hola\nLínea 2: mundo\nLínea 3: hola de nuevo")
        
        result = tool_grep_search("hola", str(test_file))
        
        assert "Resultados" in result
        assert "hola" in result
        assert "Línea 1" in result
        assert "Línea 3" in result

    def test_grep_not_found(self, temp_dir):
        """Patrón no encontrado."""
        test_file = temp_dir / "empty.txt"
        test_file.write_text("nada aquí")
        
        result = tool_grep_search("xyz123", str(test_file))
        assert "Sin coincidencias" in result

    def test_grep_recursive(self, temp_dir):
        """Búsqueda recursiva en directorio."""
        (temp_dir / "a.txt").write_text("target")
        (temp_dir / "sub" / "b.txt").parent.mkdir()
        (temp_dir / "sub" / "b.txt").write_text("target también")
        (temp_dir / "c.txt").write_text("otro")
        
        result = tool_grep_search("target", str(temp_dir), recursive=True)
        assert "a.txt" in result
        assert "b.txt" in result
        assert "c.txt" not in result


class TestWebFetch:
    """Tests para tool_web_fetch."""

    @patch("urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen, temp_dir):
        """Fetch exitoso de URL."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html><body>Hola mundo</body></html>"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        result = tool_web_fetch("http://example.com")
        
        assert "Hola mundo" in result
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_fetch_strips_html(self, mock_urlopen):
        """Elimina tags HTML, scripts y styles."""
        html = """<html><head><style>body{color:red}</style><script>alert(1)</script></head>
        <body><h1>Título</h1><p>Contenido</p></body></html>"""
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        result = tool_web_fetch("http://example.com")
        
        assert "Título" in result
        assert "Contenido" in result
        assert "<style>" not in result
        assert "<script>" not in result
        assert "<h1>" not in result
        assert "<p>" not in result

    @patch("urllib.request.urlopen")
    def test_fetch_truncates(self, mock_urlopen):
        """Trunca contenido largo."""
        long_content = "A" * 5000
        mock_response = MagicMock()
        mock_response.read.return_value = long_content.encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        result = tool_web_fetch("http://example.com", max_chars=100)
        
        assert len(result) <= 120  # 100 + "...[truncado]" + posible newline
        assert "[truncado]" in result

    @patch("urllib.request.urlopen")
    def test_fetch_error(self, mock_urlopen):
        """Error de red."""
        mock_urlopen.side_effect = Exception("Connection refused")
        
        result = tool_web_fetch("http://example.com")
        assert "Error" in result


class TestDiffFiles:
    """Tests para tool_diff_files."""

    def test_diff_with_backup(self, temp_dir):
        """Diff contra backup automático."""
        test_file = temp_dir / "diff_test.txt"
        test_file.write_text("Línea 1\nLínea 2\nLínea 3")
        # Simular backup
        backup = test_file.with_suffix(test_file.suffix + ".bak")
        backup.write_text("Línea 1\nLínea 2 original\nLínea 3")
        
        result = tool_diff_files(str(test_file))
        
        assert "Diff" in result
        assert "Línea 2 original" in result or "-" in result
        assert "Línea 2" in result

    def test_diff_explicit_files(self, temp_dir):
        """Diff entre dos archivos explícitos."""
        file_a = temp_dir / "a.txt"
        file_b = temp_dir / "b.txt"
        file_a.write_text("A\nB\nC")
        file_b.write_text("A\nB modificada\nC")
        
        result = tool_diff_files(str(file_a), str(file_b))
        
        assert "Diff" in result
        assert "B modificada" in result or "-" in result

    def test_diff_identical(self, temp_dir):
        """Archivos idénticos."""
        file_a = temp_dir / "a.txt"
        file_b = temp_dir / "b.txt"
        file_a.write_text("Igual")
        file_b.write_text("Igual")
        
        result = tool_diff_files(str(file_a), str(file_b))
        assert "idénticos" in result.lower()
