#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           ANALIZADOR DE PROYECTOS  -  wiz.py                ║
║   Coloca este archivo en la raíz de cualquier proyecto       ║
║   y ejecuta:  python wiz.py                                  ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import ast
import json
import subprocess
import importlib
import traceback
import re
from pathlib import Path
from datetime import datetime


# ─── Colores para terminal ────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"

def ok(msg):    print(f"  {C.GREEN}✔{C.RESET}  {msg}")
def warn(msg):  print(f"  {C.YELLOW}⚠{C.RESET}  {msg}")
def err(msg):   print(f"  {C.RED}✘{C.RESET}  {msg}")
def info(msg):  print(f"  {C.CYAN}ℹ{C.RESET}  {msg}")
def head(msg):  print(f"\n{C.BOLD}{C.MAGENTA}{'─'*60}\n  {msg}\n{'─'*60}{C.RESET}")


# ─── Extensiones a analizar ───────────────────────────────────────────────────
PYTHON_EXTS  = {".py"}
WEB_EXTS     = {".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".vue"}
DATA_EXTS    = {".json", ".yaml", ".yml", ".toml", ".env", ".ini", ".cfg"}
DOC_EXTS     = {".md", ".txt", ".rst"}
SKIP_DIRS    = {".git", "__pycache__", "node_modules", ".venv", "venv",
                "env", ".env", "dist", "build", ".mypy_cache", ".pytest_cache",
                ".tox", "coverage", ".idea", ".vscode"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. ESTRUCTURA DEL PROYECTO
# ══════════════════════════════════════════════════════════════════════════════
class ProjectStructure:

    def __init__(self, root: Path):
        self.root = root
        self.files: dict[str, list[Path]] = {
            "python": [], "web": [], "data": [], "docs": [], "other": []
        }
        self.total_lines = 0
        self.total_size  = 0

    def scan(self):
        for path in self.root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            self.total_size += path.stat().st_size
            if ext in PYTHON_EXTS:
                self.files["python"].append(path)
            elif ext in WEB_EXTS:
                self.files["web"].append(path)
            elif ext in DATA_EXTS:
                self.files["data"].append(path)
            elif ext in DOC_EXTS:
                self.files["docs"].append(path)
            else:
                self.files["other"].append(path)

    def report(self):
        head("📁  ESTRUCTURA DEL PROYECTO")
        total = sum(len(v) for v in self.files.values())
        info(f"Raíz: {C.BOLD}{self.root}{C.RESET}")
        info(f"Total de archivos: {C.BOLD}{total}{C.RESET}")
        info(f"Tamaño total: {C.BOLD}{self.total_size / 1024:.1f} KB{C.RESET}")
        print()
        labels = {
            "python": "🐍 Python",
            "web":    "🌐 Web (JS/TS/HTML/CSS)",
            "data":   "🗂  Configuración/Datos",
            "docs":   "📄 Documentación",
            "other":  "📦 Otros",
        }
        for key, paths in self.files.items():
            if paths:
                print(f"  {labels[key]:30s} {C.BOLD}{len(paths):>4}{C.RESET} archivo(s)")
                for p in sorted(paths)[:5]:
                    print(f"    {C.DIM}{p.relative_to(self.root)}{C.RESET}")
                if len(paths) > 5:
                    print(f"    {C.DIM}... y {len(paths)-5} más{C.RESET}")

        # detectar tipo de proyecto
        self._detect_project_type()

    def _detect_project_type(self):
        print()
        detected = []
        root_files = {f.name for f in self.root.iterdir() if f.is_file()}

        if "manage.py" in root_files:        detected.append("Django")
        if "app.py" in root_files or \
           "wsgi.py" in root_files:          detected.append("Flask / WSGI")
        if "main.py" in root_files and \
           "fastapi" in self._read_req():    detected.append("FastAPI")
        if "package.json" in root_files:     detected.append("Node.js / JavaScript")
        if "Dockerfile" in root_files:       detected.append("Docker")
        if "docker-compose.yml" in root_files \
           or "docker-compose.yaml" in root_files:
                                             detected.append("Docker Compose")
        if "pyproject.toml" in root_files \
           or "setup.py" in root_files:      detected.append("Paquete Python")
        if ".github" in {d.name for d in self.root.iterdir() if d.is_dir()}:
                                             detected.append("GitHub Actions / CI")

        if detected:
            info(f"Tipo de proyecto detectado: {C.BOLD}{', '.join(detected)}{C.RESET}")
        else:
            warn("No se pudo detectar el tipo de proyecto automáticamente.")

    def _read_req(self) -> str:
        for name in ("requirements.txt", "pyproject.toml", "setup.py"):
            p = self.root / name
            if p.exists():
                return p.read_text(errors="ignore").lower()
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# 2. ANÁLISIS DE SINTAXIS PYTHON (AST)
# ══════════════════════════════════════════════════════════════════════════════
class PythonAnalyzer:

    def __init__(self, files: list[Path], root: Path):
        self.files  = files
        self.root   = root
        self.errors: list[tuple[Path, str]] = []
        self.stats  = {
            "total_lines":   0,
            "functions":     0,
            "classes":       0,
            "imports":       0,
            "todos":         0,
            "long_lines":    0,
            "complex_funcs": [],
        }

    def analyze(self):
        for path in self.files:
            self._analyze_file(path)

    def _analyze_file(self, path: Path):
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.errors.append((path, f"No se pudo leer: {e}"))
            return

        lines = source.splitlines()
        self.stats["total_lines"] += len(lines)

        # Líneas largas (> 120 chars)
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                self.stats["long_lines"] += 1

        # TODOs / FIXMEs
        for line in lines:
            if re.search(r"\b(TODO|FIXME|HACK|XXX|BUG)\b", line, re.I):
                self.stats["todos"] += 1

        # Sintaxis AST
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            self.errors.append((path, f"SyntaxError línea {e.lineno}: {e.msg}"))
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.stats["functions"] += 1
                # complejidad simple: contar ifs/fors/whiles/try
                complexity = sum(
                    1 for n in ast.walk(node)
                    if isinstance(n, (ast.If, ast.For, ast.While,
                                      ast.Try, ast.ExceptHandler,
                                      ast.comprehension))
                )
                if complexity > 8:
                    self.stats["complex_funcs"].append(
                        (path.relative_to(self.root), node.name,
                         getattr(node, "lineno", "?"), complexity)
                    )
            elif isinstance(node, ast.ClassDef):
                self.stats["classes"] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self.stats["imports"] += 1

    def report(self):
        head("🐍  ANÁLISIS PYTHON")

        ok(f"Archivos Python: {len(self.files)}")
        info(f"Líneas de código: {C.BOLD}{self.stats['total_lines']:,}{C.RESET}")
        info(f"Funciones:  {self.stats['functions']}   |  "
             f"Clases: {self.stats['classes']}   |  "
             f"Imports: {self.stats['imports']}")

        # Errores de sintaxis
        if self.errors:
            print()
            for path, msg in self.errors:
                err(f"{path.relative_to(self.root) if path.is_absolute() else path}: {msg}")
        else:
            ok("Sin errores de sintaxis detectados ✨")

        # Líneas largas
        if self.stats["long_lines"]:
            warn(f"{self.stats['long_lines']} línea(s) superan 120 caracteres (considera refactorizar)")

        # TODOs
        if self.stats["todos"]:
            warn(f"{self.stats['todos']} comentario(s) TODO/FIXME/HACK pendiente(s)")

        # Funciones complejas
        if self.stats["complex_funcs"]:
            print()
            warn("Funciones con alta complejidad ciclomática (> 8):")
            for fpath, fname, lineno, score in sorted(
                    self.stats["complex_funcs"], key=lambda x: -x[3])[:10]:
                print(f"    {C.RED}●{C.RESET} {fpath}:{lineno}  "
                      f"{C.BOLD}{fname}(){C.RESET}  complejidad={C.RED}{score}{C.RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. DEPENDENCIAS
# ══════════════════════════════════════════════════════════════════════════════
class DependencyChecker:

    def __init__(self, root: Path):
        self.root = root
        self.req_files: list[Path] = []
        self.missing: list[str]    = []
        self.packages: list[str]   = []

    def check(self):
        # Buscar archivos de dependencias
        for name in ("requirements.txt", "requirements-dev.txt",
                     "requirements-test.txt"):
            p = self.root / name
            if p.exists():
                self.req_files.append(p)

        for req_file in self.req_files:
            self._parse_requirements(req_file)

    def _parse_requirements(self, path: Path):
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Quitar extras como package[extra]>=1.0
            pkg = re.split(r"[>=<!;\[\s]", line)[0].strip()
            if pkg:
                self.packages.append(pkg)
                # Intentar importar (nombre normalizado)
                import_name = pkg.lower().replace("-", "_").replace(".", "_")
                try:
                    importlib.import_module(import_name)
                except ImportError:
                    self.missing.append(pkg)
                except Exception:
                    pass  # Otros errores no son "falta instalar"

    def report(self):
        head("📦  DEPENDENCIAS")

        if not self.req_files:
            warn("No se encontró requirements.txt")
            # ¿Hay pyproject.toml o setup.py?
            for alt in ("pyproject.toml", "setup.py", "Pipfile"):
                if (self.root / alt).exists():
                    info(f"Se encontró {alt} (análisis manual recomendado)")
            return

        for rf in self.req_files:
            ok(f"Encontrado: {rf.name}  ({len(self.packages)} paquetes)")

        if self.missing:
            print()
            warn(f"{len(self.missing)} paquete(s) NO están instalados en el entorno actual:")
            for pkg in self.missing:
                err(f"    pip install {pkg}")
        else:
            ok("Todos los paquetes están instalados ✨")


# ══════════════════════════════════════════════════════════════════════════════
# 4. SEGURIDAD (análisis básico)
# ══════════════════════════════════════════════════════════════════════════════
class SecurityScanner:

    PATTERNS = {
        "Contraseña/clave en código": re.compile(
            r'(password|passwd|secret|api_key|token|private_key)\s*=\s*["\'][^"\']{4,}',
            re.I),
        "eval() peligroso": re.compile(r'\beval\s*\('),
        "exec() peligroso": re.compile(r'\bexec\s*\('),
        "SQL sin parametrizar": re.compile(
            r'(execute|cursor\.execute)\s*\(\s*["\'].*%(s|d)', re.I),
        "subprocess con shell=True": re.compile(
            r'subprocess\.(run|call|Popen).*shell\s*=\s*True'),
        "pickle.loads (riesgo deserialización)": re.compile(r'pickle\.loads?\('),
        "print de datos sensibles": re.compile(
            r'print\s*\(.*?(password|token|secret|key)', re.I),
        "assert usado para seguridad": re.compile(r'\bassert\b.*\bauth'),
    }

    def __init__(self, files: list[Path], root: Path):
        self.files    = files
        self.root     = root
        self.findings: list[tuple[str, Path, int, str]] = []

    def scan(self):
        for path in self.files:
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                for label, pattern in self.PATTERNS.items():
                    if pattern.search(line):
                        self.findings.append((label, path, i, line.strip()[:80]))

    def report(self):
        head("🔒  SEGURIDAD")
        if not self.findings:
            ok("No se detectaron problemas de seguridad obvios ✨")
            return

        warn(f"Se encontraron {len(self.findings)} posible(s) problema(s):")
        for label, path, lineno, snippet in self.findings:
            rel = path.relative_to(self.root)
            print(f"\n  {C.RED}⚑{C.RESET}  {C.BOLD}{label}{C.RESET}")
            print(f"     Archivo: {rel}:{lineno}")
            print(f"     {C.DIM}{snippet}{C.RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. ARCHIVOS DE CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════
class ConfigChecker:

    GOOD_FILES = [
        (".gitignore",       "Control de versiones"),
        ("README.md",        "Documentación principal"),
        ("requirements.txt", "Dependencias Python"),
        (".env.example",     "Ejemplo de variables de entorno"),
        ("LICENSE",          "Licencia del proyecto"),
    ]

    BAD_FILES = [
        ".env",
        "*.pem", "*.key", "*.p12",
        "config.secret.*",
    ]

    def __init__(self, root: Path):
        self.root = root

    def check(self):
        pass  # todo en report()

    def report(self):
        head("⚙️   CONFIGURACIÓN DEL PROYECTO")

        root_names = {f.name for f in self.root.iterdir() if f.is_file()}

        for filename, desc in self.GOOD_FILES:
            if filename in root_names:
                ok(f"{filename:25s} — {desc}")
            else:
                warn(f"{filename:25s} — {desc} {C.DIM}(no encontrado){C.RESET}")

        # .env expuesto
        if ".env" in root_names:
            err(".env encontrado en raíz. Asegúrate de que esté en .gitignore")

        # .gitignore incluye __pycache__ y .env?
        gi = self.root / ".gitignore"
        if gi.exists():
            content = gi.read_text(errors="ignore")
            for entry in ("__pycache__", ".env", "*.pyc", "node_modules"):
                if entry not in content:
                    warn(f".gitignore no incluye '{entry}'")


# ══════════════════════════════════════════════════════════════════════════════
# 6. TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestFinder:

    def __init__(self, root: Path):
        self.root = root

    def report(self):
        head("🧪  TESTS")
        test_files = list(self.root.rglob("test_*.py")) + \
                     list(self.root.rglob("*_test.py"))
        # excluir dirs
        test_files = [f for f in test_files
                      if not any(d in SKIP_DIRS for d in f.parts)]

        if not test_files:
            warn("No se encontraron archivos de tests (test_*.py / *_test.py)")
            return

        ok(f"Archivos de test encontrados: {len(test_files)}")
        for tf in sorted(test_files)[:8]:
            print(f"    {C.DIM}{tf.relative_to(self.root)}{C.RESET}")

        # ¿Intentar correr pytest?
        if _cmd_exists("pytest"):
            info("Ejecutando pytest --tb=short -q ...")
            result = subprocess.run(
                ["pytest", "--tb=short", "-q", "--no-header"],
                capture_output=True, text=True, cwd=str(self.root)
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                ok("pytest pasó sin errores")
            else:
                err("pytest reportó fallos:")
            # Mostrar últimas 20 líneas
            for line in output.splitlines()[-20:]:
                print(f"    {line}")
        else:
            warn("pytest no está instalado. Instálalo con: pip install pytest")


# ══════════════════════════════════════════════════════════════════════════════
# 7. LINTER (flake8 / pylint)
# ══════════════════════════════════════════════════════════════════════════════
class LinterRunner:

    def __init__(self, root: Path):
        self.root = root

    def report(self):
        head("🔍  LINTING")

        if _cmd_exists("flake8"):
            info("Corriendo flake8 ...")
            result = subprocess.run(
                ["flake8", "--max-line-length=120",
                 "--count", "--statistics",
                 "--exclude=" + ",".join(SKIP_DIRS),
                 "."],
                capture_output=True, text=True, cwd=str(self.root)
            )
            output = (result.stdout + result.stderr).strip()
            if not output:
                ok("flake8: sin errores ✨")
            else:
                lines = output.splitlines()
                for line in lines[:30]:
                    if re.match(r".+:\d+:\d+: [EW]", line):
                        code = line.split(":")[3].strip()[:1] if ":" in line else "?"
                        if code == "E":
                            err(line)
                        else:
                            warn(line)
                    else:
                        print(f"    {line}")
                if len(lines) > 30:
                    info(f"... y {len(lines)-30} líneas más. Ejecuta flake8 para ver todo.")
        elif _cmd_exists("pylint"):
            info("flake8 no encontrado. Corriendo pylint ...")
            py_files = [str(f) for f in self.root.rglob("*.py")
                        if not any(d in SKIP_DIRS for d in f.parts)][:20]
            if py_files:
                result = subprocess.run(
                    ["pylint", "--score=no"] + py_files,
                    capture_output=True, text=True, cwd=str(self.root)
                )
                for line in (result.stdout + result.stderr).splitlines()[:30]:
                    print(f"    {line}")
        else:
            warn("Ningún linter encontrado. Instala uno:")
            info("    pip install flake8")
            info("    pip install pylint")


# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════════════
def _cmd_exists(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None


def _banner():
    print(f"""{C.BOLD}{C.CYAN}
╔══════════════════════════════════════════════════════════════╗
║          🔬  WIZ  —  ANALIZADOR DE PROYECTOS PYTHON          ║
║              github.com/tu-usuario/wiz                       ║
╚══════════════════════════════════════════════════════════════╝{C.RESET}
  {C.DIM}Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.RESET}
""")


def _summary(errors_total: int, warns_total: int):
    head("📊  RESUMEN FINAL")
    if errors_total == 0 and warns_total == 0:
        print(f"  {C.GREEN}{C.BOLD}✨  ¡Proyecto en excelente estado!{C.RESET}")
    elif errors_total == 0:
        print(f"  {C.YELLOW}{C.BOLD}⚠  {warns_total} advertencia(s) — revisa los detalles arriba.{C.RESET}")
    else:
        print(f"  {C.RED}{C.BOLD}✘  {errors_total} error(es)  |  {warns_total} advertencia(s) — corrección recomendada.{C.RESET}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
def main():
    _banner()

    # Directorio raíz = donde está este script
    root = Path(__file__).parent.resolve()

    # 1. Estructura
    structure = ProjectStructure(root)
    structure.scan()
    structure.report()

    py_files = structure.files["python"]

    # 2. Python AST
    py_analyzer = PythonAnalyzer(py_files, root)
    py_analyzer.analyze()
    py_analyzer.report()

    # 3. Dependencias
    deps = DependencyChecker(root)
    deps.check()
    deps.report()

    # 4. Seguridad
    security = SecurityScanner(py_files, root)
    security.scan()
    security.report()

    # 5. Configuración
    config = ConfigChecker(root)
    config.check()
    config.report()

    # 6. Tests
    tests = TestFinder(root)
    tests.report()

    # 7. Linter
    linter = LinterRunner(root)
    linter.report()

    # Resumen
    errors = len(py_analyzer.errors) + len(security.findings) + len(deps.missing)
    warns  = (py_analyzer.stats["todos"] +
              (1 if py_analyzer.stats["long_lines"] else 0) +
              len(py_analyzer.stats["complex_funcs"]))
    _summary(errors, warns)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}  Análisis cancelado.{C.RESET}\n")
        sys.exit(0)
    except Exception:
        print(f"\n{C.RED}Error inesperado en el analizador:{C.RESET}")
        traceback.print_exc()
        sys.exit(1)
