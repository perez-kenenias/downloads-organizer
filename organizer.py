import os
import shutil
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import mimetypes

@dataclass
class ClassificationResult:
    filename: str
    source_path: str
    target_folder: str
    category: str
    method: str  # 'extension', 'keyword', 'llm', 'default'
    confidence: float  # 0.0 to 1.0
    reason: str
    timestamp: str

class FileClassifier:
    """Classifies files based on rules, keywords, and content analysis."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.history: List[ClassificationResult] = []
        self._load_history()
        
    def _load_config(self, path: str) -> dict:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> dict:
        return {
            "source_folder": str(Path.home() / "Downloads"),
            "target_base_folder": str(Path.home() / "Downloads" / "Organized"),
            "categories": {
                "Libros": {
                    "extensions": [".pdf", ".epub", ".mobi", ".azw3", ".djvu", ".fb2"],
                    "keywords": ["libro", "book", "ebook", "novela", "autor", "editorial", "capitulo", "chapter", "bestseller", "saga", "trilogia"],
                    "mime_types": ["application/pdf", "application/epub+zip"],
                    "subcategories": {
                        "Programacion": [".py", ".js", ".java", ".cpp", "programming", "python", "javascript", "coding", "desarrollo"],
                        "Negocios": ["negocio", "business", "marketing", "finanzas", "emprendimiento", "ventas"],
                        "Ficcion": ["novela", "ficcion", "fantasia", "ciencia ficcion", "thriller", "romance"],
                        "Autoayuda": ["autoayuda", "productividad", "habitos", "motivacion", "crecimiento personal"]
                    }
                },
                "Trabajo": {
                    "extensions": [".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods"],
                    "keywords": ["reporte", "report", "reunion", "meeting", "proyecto", "project", "cliente", "client", "propuesta", "proposal", "cotizacion", "invoice", "factura", "presentacion"],
                    "mime_types": ["application/vnd.openxmlformats-officedocument"],
                    "subcategories": {}
                },
                "Infonavit": {
                    "extensions": [".pdf", ".docx", ".xlsx"],
                    "keywords": ["infonavit", "credito", "hipotecario", "cofinavit", "puntos", "subcuenta", "retiro", "vivienda", "avaluo", "notaria", "escrituras", "fovissste", "solicitud"],
                    "mime_types": [],
                    "subcategories": {}
                },
                "Documentos_Personales": {
                    "extensions": [".pdf", ".jpg", ".jpeg", ".png", ".docx"],
                    "keywords": ["ine", "curp", "rfc", "pasaporte", "licencia", "acta", "nacimiento", "constancia", "comprobante", "domicilio", "recibo", "nomina", "estado de cuenta", "banco", "factura personal", "receta medica", "analisis", "laboratorio"],
                    "mime_types": [],
                    "subcategories": {}
                },
                "Software": {
                    "extensions": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".appimage", ".jar", ".zip", ".tar.gz", ".tgz", ".bz2", ".7z", ".rar"],
                    "keywords": ["setup", "installer", "install", "portable", "crack", "patch", "keygen", "software", "programa", "app", "application", "driver", "controlador"],
                    "mime_types": ["application/x-msdownload", "application/x-executable"],
                    "subcategories": {
                        "Sistemas_Operativos": ["windows", "linux", "ubuntu", "debian", "iso", "macos"],
                        "Herramientas": ["tool", "herramienta", "utilidad", "utility", "editor", "ide"],
                        "Drivers": ["driver", "controlador", "firmware", "bios"]
                    }
                },
                "Multimedia": {
                    "extensions": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
                    "keywords": ["video", "audio", "musica", "movie", "pelicula", "cancion", "song", "album", "podcast", "tutorial", "curso"],
                    "mime_types": ["video/", "audio/"],
                    "subcategories": {
                        "Videos": [".mp4", ".avi", ".mkv", ".mov"],
                        "Musica": [".mp3", ".wav", ".flac", ".aac"],
                        "Cursos": ["curso", "tutorial", "course", "lesson", "clase"]
                    }
                },
                "Imagenes": {
                    "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".psd", ".ai", ".sketch", ".fig"],
                    "keywords": ["imagen", "image", "foto", "photo", "screenshot", "captura", "wallpaper", "fondo", "icono", "logo", "diseño", "design"],
                    "mime_types": ["image/"],
                    "subcategories": {
                        "Screenshots": ["screenshot", "captura", "screencapture", "snip"],
                        "Fotos": ["foto", "photo", "pic", "image", "img"],
                        "Diseño": ["design", "diseño", "logo", "banner", "mockup", "wireframe"]
                    }
                },
                "Comprimidos": {
                    "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
                    "keywords": ["compressed", "compressed file", "backup", "respaldo"],
                    "mime_types": ["application/zip", "application/x-rar"],
                    "subcategories": {}
                },
                "Codigo_Fuente": {
                    "extensions": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".r", ".sql", ".sh", ".bat", ".ps1"],
                    "keywords": ["code", "source", "script", "github", "repo", "repository"],
                    "mime_types": ["text/x-python", "text/javascript", "text/html"],
                    "subcategories": {}
                }
            },
            "rules": {
                "ignore_patterns": ["*.tmp", "*.crdownload", "*.part", ".DS_Store", "Thumbs.db"],
                "ignore_folders": ["Organized", "temp", "tmp"],
                "min_file_size_bytes": 1,
                "max_file_size_mb": 2000
            },
            "options": {
                "create_month_subfolders": False,
                "dry_run": False,
                "use_llm_for_ambiguous": False,
                "llm_api_key": "",
                "auto_organize_on_startup": False,
                "backup_before_move": False
            }
        }
    
    def _load_history(self):
        history_path = "organizer_history.json"
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = [ClassificationResult(**item) for item in data]
            except:
                self.history = []
    
    def _save_history(self):
        with open("organizer_history.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.history], f, indent=2, ensure_ascii=False)
    
    def classify_file(self, filepath: str) -> ClassificationResult:
        """Classify a single file and return the result."""
        filename = os.path.basename(filepath)
        name_lower = filename.lower()
        ext = os.path.splitext(filename)[1].lower()
        
        # Check ignore rules
        if self._should_ignore(filename, filepath):
            return ClassificationResult(
                filename=filename,
                source_path=filepath,
                target_folder="",
                category="IGNORED",
                method="ignore",
                confidence=1.0,
                reason="File matches ignore pattern",
                timestamp=datetime.now().isoformat()
            )
        
        # Try keyword matching first (highest priority - user intent)
        category, confidence, reason = self._match_by_keywords(name_lower)
        if category:
            method = "keyword"
        else:
            # Try extension matching
            category, confidence, reason = self._match_by_extension(ext, name_lower)
            if category:
                method = "extension"
            else:
                # Try mime type
                category, confidence, reason = self._match_by_mime_type(filepath)
                if category:
                    method = "mime"
                else:
                    # Default fallback
                    category = "Otros"
                    confidence = 0.3
                    reason = "No matching category found"
                    method = "default"
        
        # Determine target folder
        target_folder = self._build_target_path(category, filename)
        
        result = ClassificationResult(
            filename=filename,
            source_path=filepath,
            target_folder=target_folder,
            category=category,
            method=method,
            confidence=confidence,
            reason=reason,
            timestamp=datetime.now().isoformat()
        )
        
        return result
    
    def _should_ignore(self, filename: str, filepath: str) -> bool:
        rules = self.config.get("rules", {})
        
        # Check ignore patterns
        for pattern in rules.get("ignore_patterns", []):
            if self._match_pattern(filename, pattern):
                return True
        
        # Check ignore folders
        for folder in rules.get("ignore_folders", []):
            if folder in filepath.split(os.sep):
                return True
        
        # Check file size
        try:
            size = os.path.getsize(filepath)
            min_size = rules.get("min_file_size_bytes", 1)
            max_size = rules.get("max_file_size_mb", 2000) * 1024 * 1024
            if size < min_size or size > max_size:
                return True
        except:
            pass
        
        return False
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """Simple glob-like matching."""
        import fnmatch
        return fnmatch.fnmatch(filename.lower(), pattern.lower())
    
    def _match_by_keywords(self, name_lower: str) -> Tuple[Optional[str], float, str]:
        """Match file by keywords in filename. Highest priority."""
        categories = self.config.get("categories", {})
        
        best_category = None
        best_score = 0
        best_keywords = []
        
        for cat_name, cat_config in categories.items():
            keywords = cat_config.get("keywords", [])
            score = 0
            matched = []
            
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in name_lower:
                    # Full word match scores higher
                    if f" {kw_lower} " in f" {name_lower} " or \
                       name_lower.startswith(kw_lower + " ") or \
                       name_lower.endswith(" " + kw_lower) or \
                       name_lower == kw_lower:
                        score += 3
                    else:
                        score += 1
                    matched.append(kw)
            
            if score > best_score:
                best_score = score
                best_category = cat_name
                best_keywords = matched
        
        if best_category and best_score >= 2:
            confidence = min(0.5 + (best_score * 0.1), 0.95)
            return best_category, confidence, f"Matched keywords: {', '.join(best_keywords[:3])}"
        
        return None, 0, ""
    
    def _match_by_extension(self, ext: str, name_lower: str) -> Tuple[Optional[str], float, str]:
        """Match file by extension."""
        categories = self.config.get("categories", {})
        
        for cat_name, cat_config in categories.items():
            extensions = cat_config.get("extensions", [])
            if ext in extensions:
                # Check if subcategory matches
                subcats = cat_config.get("subcategories", {})
                for sub_name, sub_rules in subcats.items():
                    for rule in sub_rules:
                        if rule.startswith(".") and rule == ext:
                            continue
                        if rule.lower() in name_lower:
                            return f"{cat_name}/{sub_name}", 0.8, f"Extension {ext} + subcategory keyword"
                
                return cat_name, 0.6, f"Extension match: {ext}"
        
        return None, 0, ""
    
    def _match_by_mime_type(self, filepath: str) -> Tuple[Optional[str], float, str]:
        """Match by MIME type."""
        mime_type, _ = mimetypes.guess_type(filepath)
        if not mime_type:
            return None, 0, ""
        
        categories = self.config.get("categories", {})
        for cat_name, cat_config in categories.items():
            mime_prefixes = cat_config.get("mime_types", [])
            for prefix in mime_prefixes:
                if mime_type.startswith(prefix):
                    return cat_name, 0.5, f"MIME type: {mime_type}"
        
        return None, 0, ""
    
    def _build_target_path(self, category: str, filename: str) -> str:
        """Build the target folder path."""
        base = self.config.get("target_base_folder", "")
        
        # Handle subcategories (Category/Subcategory)
        if "/" in category:
            parts = category.split("/")
            target = os.path.join(base, parts[0], parts[1])
        else:
            target = os.path.join(base, category)
        
        # Add month subfolder if configured
        if self.config.get("options", {}).get("create_month_subfolders", False):
            month_folder = datetime.now().strftime("%Y-%m")
            target = os.path.join(target, month_folder)
        
        return target
    
    def organize(self) -> List[ClassificationResult]:
        """Organize all files in the source folder."""
        source = self.config.get("source_folder", "")
        if not os.path.exists(source):
            print(f"Source folder not found: {source}")
            return []
        
        results = []
        files = [f for f in os.listdir(source) if os.path.isfile(os.path.join(source, f))]
        
        print(f"Found {len(files)} files to organize in: {source}")
        
        for filename in files:
            filepath = os.path.join(source, filename)
            result = self.classify_file(filepath)
            
            if result.category == "IGNORED":
                print(f"  [IGNORED] {filename} - {result.reason}")
                continue
            
            # Execute move
            if not self.config.get("options", {}).get("dry_run", False):
                success = self._move_file(result)
                if success:
                    print(f"  [MOVED] {filename} -> {result.category} ({result.method}, confidence: {result.confidence:.2f})")
                else:
                    print(f"  [ERROR] Failed to move {filename}")
                    result.reason += " (MOVE FAILED)"
            else:
                print(f"  [DRY RUN] {filename} -> {result.category} ({result.method}, confidence: {result.confidence:.2f})")
            
            results.append(result)
            self.history.append(result)
        
        self._save_history()
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _move_file(self, result: ClassificationResult) -> bool:
        """Move file to target folder, handling conflicts."""
        try:
            target_dir = result.target_folder
            os.makedirs(target_dir, exist_ok=True)
            
            target_path = os.path.join(target_dir, result.filename)
            
            # Handle duplicate filenames
            if os.path.exists(target_path):
                name, ext = os.path.splitext(result.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"{name}_{timestamp}{ext}"
                target_path = os.path.join(target_dir, new_name)
                print(f"    [RENAME] Duplicate found, renamed to: {new_name}")
            
            shutil.move(result.source_path, target_path)
            return True
        except Exception as e:
            print(f"    [ERROR] {e}")
            return False
    
    def _print_summary(self, results: List[ClassificationResult]):
        """Print a nice summary of what was done."""
        if not results:
            print("\nNo files were organized.")
            return
        
        print("\n" + "="*60)
        print("ORGANIZATION SUMMARY")
        print("="*60)
        
        # Count by category
        categories: Dict[str, int] = {}
        methods: Dict[str, int] = {}
        
        for r in results:
            cat = r.category.split("/")[0]  # Top-level category
            categories[cat] = categories.get(cat, 0) + 1
            methods[r.method] = methods.get(r.method, 0) + 1
        
        print("\nBy Category:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count} files")
        
        print("\nBy Method:")
        method_names = {
            "keyword": "Keyword matching",
            "extension": "File extension",
            "mime": "MIME type",
            "default": "Default fallback",
            "llm": "AI classification"
        }
        for method, count in sorted(methods.items(), key=lambda x: -x[1]):
            print(f"  {method_names.get(method, method)}: {count} files")
        
        print(f"\nTotal files organized: {len(results)}")
        print("="*60)
    
    def correct_classification(self, filename: str, correct_category: str):
        """Learn from user correction."""
        # Find the file in history
        for result in self.history:
            if result.filename == filename:
                print(f"Learning: '{filename}' should be '{correct_category}' (was: {result.category})")
                
                # Add the filename keyword to the correct category
                categories = self.config.get("categories", {})
                if correct_category in categories:
                    # Extract meaningful keywords from filename
                    name_without_ext = os.path.splitext(filename)[0]
                    words = [w for w in name_without_ext.replace("_", " ").replace("-", " ").split() 
                            if len(w) > 3]
                    
                    for word in words[:3]:
                        word_lower = word.lower()
                        if word_lower not in categories[correct_category].get("keywords", []):
                            categories[correct_category]["keywords"].append(word_lower)
                            print(f"  Added keyword '{word_lower}' to '{correct_category}'")
                    
                    # Save updated config
                    self._save_config()
                break
    
    def _save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print("Configuration saved to config.json")
    
    def undo_last(self, count: int = 1):
        """Undo the last N moves by checking history."""
        moved = [r for r in reversed(self.history) if r.category != "IGNORED" and r.target_folder]
        to_undo = moved[:count]
        
        for result in to_undo:
            source = result.source_path
            target_dir = result.target_folder
            target = os.path.join(target_dir, result.filename)
            
            if os.path.exists(target) and not os.path.exists(source):
                try:
                    shutil.move(target, source)
                    print(f"[UNDO] Restored: {result.filename} -> Downloads")
                except Exception as e:
                    print(f"[UNDO FAILED] {result.filename}: {e}")
            else:
                print(f"[UNDO SKIP] Cannot undo {result.filename} (file not found or already exists)")
    
    def scan_only(self) -> List[ClassificationResult]:
        """Scan files without moving them (preview mode)."""
        original_dry_run = self.config.get("options", {}).get("dry_run", False)
        self.config["options"]["dry_run"] = True
        results = self.organize()
        self.config["options"]["dry_run"] = original_dry_run
        return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Downloads Organizer Agent")
    parser.add_argument("--scan", action="store_true", help="Preview what would be moved without moving anything")
    parser.add_argument("--undo", type=int, default=0, help="Undo last N moves")
    parser.add_argument("--correct", nargs=2, metavar=("FILE", "CATEGORY"), help="Teach the agent: --correct 'file.pdf' 'Libros'")
    
    args = parser.parse_args()
    
    agent = FileClassifier()
    
    if args.undo > 0:
        agent.undo_last(args.undo)
    elif args.correct:
        agent.correct_classification(args.correct[0], args.correct[1])
    elif args.scan:
        print("SCAN MODE (no files will be moved)")
        agent.scan_only()
    else:
        agent.organize()
