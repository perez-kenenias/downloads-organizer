import os
import re
import shutil
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import mimetypes
from llm_classifier import LLMClassifier
from indexer import FileIndex
import content_extractor

@dataclass
class ClassificationResult:
    filename: str
    source_path: str
    target_folder: str
    category: str
    method: str  # 'extension', 'keyword', 'content', 'llm', 'duplicate', 'default'
    confidence: float  # 0.0 to 1.0
    reason: str
    timestamp: str
    final_path: str = ""  # actual path after move (handles renames)

class FileClassifier:
    """Classifies files based on rules, keywords, and content analysis."""

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._clean_keywords()
        self.history: List[ClassificationResult] = []
        self._load_history()
        self.llm = LLMClassifier(self.config.get("options", {}))
        self.index = FileIndex()
        imported = self.index.import_history()
        if imported:
            print(f"[INDEX] Imported {imported} records from organizer_history.json into search index")

    def _load_config(self, path: str) -> dict:
        config = self._default_config()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Fill in any option keys added in newer versions
            for key, value in self._default_config()["options"].items():
                config.setdefault("options", {}).setdefault(key, value)
        return config

    def _clean_keywords(self):
        """Trim stray whitespace in keywords (a ' Spotify' never matches anything)."""
        for cat in self.config.get("categories", {}).values():
            cat["keywords"] = [k.strip() for k in cat.get("keywords", []) if k.strip()]
            for sub, rules in cat.get("subcategories", {}).items():
                cat["subcategories"][sub] = [r.strip() for r in rules if r.strip()]

    def _source_folders(self) -> List[str]:
        """Support both legacy 'source_folder' (string) and 'source_folders' (list)."""
        folders = self.config.get("source_folders")
        if isinstance(folders, list) and folders:
            return folders
        single = self.config.get("source_folder", "")
        return [single] if single else []

    def _default_config(self) -> dict:
        return {
            "source_folders": [str(Path.home() / "Downloads")],
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
                "Documentos_Personales": {
                    "extensions": [".pdf", ".jpg", ".jpeg", ".png", ".docx"],
                    "keywords": ["ine", "curp", "rfc", "pasaporte", "licencia", "acta", "nacimiento", "constancia", "comprobante", "domicilio", "recibo", "nomina", "estado de cuenta", "banco", "factura personal", "receta medica", "analisis", "laboratorio"],
                    "mime_types": [],
                    "subcategories": {}
                },
                "Software": {
                    "extensions": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".appimage", ".jar"],
                    "keywords": ["setup", "installer", "install", "portable", "software", "programa", "app", "application", "driver", "controlador"],
                    "mime_types": ["application/x-msdownload", "application/x-executable"],
                    "subcategories": {}
                },
                "Multimedia": {
                    "extensions": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".mp3", ".wav", ".flac", ".aac", ".ogg"],
                    "keywords": ["video", "audio", "musica", "movie", "pelicula", "cancion", "song", "album", "podcast", "tutorial", "curso"],
                    "mime_types": ["video/", "audio/"],
                    "subcategories": {}
                },
                "Imagenes": {
                    "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
                    "keywords": ["imagen", "image", "foto", "photo", "screenshot", "captura", "wallpaper"],
                    "mime_types": ["image/"],
                    "subcategories": {}
                },
                "Comprimidos": {
                    "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
                    "keywords": ["backup", "respaldo"],
                    "mime_types": ["application/zip", "application/x-rar"],
                    "subcategories": {}
                },
                "Codigo_Fuente": {
                    "extensions": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".php", ".sql", ".sh", ".bat", ".ps1"],
                    "keywords": ["code", "source", "script", "github", "repo"],
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
                "llm_provider": "ollama",
                "llm_model": "llama3.2",
                "llm_ollama_url": "http://localhost:11434",
                "llm_api_key": "",
                "auto_organize_on_startup": False,
                "backup_before_move": False,
                "use_content_analysis": True,
                "detect_duplicates": True,
                "duplicate_action": "folder",
                "duplicates_folder": "Duplicados",
                "hash_max_mb": 500,
                "smart_rename": False,
                "review_threshold": 0.5,
                "watch_interval_seconds": 30
            }
        }

    def _load_history(self):
        history_path = "organizer_history.json"
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = [ClassificationResult(**item) for item in data]
            except (json.JSONDecodeError, TypeError, OSError):
                self.history = []

    def _save_history(self):
        with open("organizer_history.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.history], f, indent=2, ensure_ascii=False)

    def _hash_file(self, filepath: str, force: bool = False) -> str:
        """SHA-256 of the file, empty string if too big or unreadable.
        force=True hashes even when detect_duplicates is off (used by --dedupe)."""
        options = self.config.get("options", {})
        if not force and not options.get("detect_duplicates", True):
            return ""
        max_bytes = options.get("hash_max_mb", 500) * 1024 * 1024
        try:
            if os.path.getsize(filepath) > max_bytes:
                return ""
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return ""

    def classify_file(self, filepath: str, file_hash: str = "") -> ClassificationResult:
        """Classify a single file and return the result."""
        filename = os.path.basename(filepath)
        # Normalize separators so 'estado_de-cuenta(2).pdf' matches keywords as words
        name_lower = re.sub(r"[_\-.()\[\]]+", " ", filename.lower())
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

        # Duplicate detection: identical content already organized somewhere?
        if file_hash:
            existing = self.index.find_by_hash(file_hash)
            if existing:
                dup_folder = os.path.join(
                    self.config.get("target_base_folder", ""),
                    self.config.get("options", {}).get("duplicates_folder", "Duplicados")
                )
                return ClassificationResult(
                    filename=filename,
                    source_path=filepath,
                    target_folder=dup_folder,
                    category="Duplicados",
                    method="duplicate",
                    confidence=1.0,
                    reason=f"Identical content already at: {existing['final_path']}",
                    timestamp=datetime.now().isoformat()
                )

        content = None

        # 1. Keywords in filename (highest priority - user intent)
        category, confidence, reason = self._match_by_keywords(name_lower)
        if category:
            method = "keyword"
        else:
            # 2. Content analysis (more precise than extension for generic names)
            category, confidence, reason, content = self._match_by_content(filepath)
            if category:
                method = "content"
            else:
                # 3. Extension matching
                category, confidence, reason = self._match_by_extension(ext, name_lower)
                if category:
                    method = "extension"
                else:
                    # 4. MIME type
                    category, confidence, reason = self._match_by_mime_type(filepath)
                    if category:
                        method = "mime"
                    else:
                        # 5. LLM classification (if enabled), with content when available
                        category, confidence, reason = self._match_by_llm(name_lower, content)
                        if category:
                            method = "llm"
                        else:
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
        except OSError:
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
            # Try to refine into a subcategory
            refined = self._match_subcategory(best_category, name_lower)
            return refined or best_category, confidence, f"Matched keywords: {', '.join(best_keywords[:3])}"

        return None, 0, ""

    def _match_subcategory(self, cat_name: str, text_lower: str) -> Optional[str]:
        """Return 'Category/Subcategory' if a subcategory rule matches the text."""
        subcats = self.config.get("categories", {}).get(cat_name, {}).get("subcategories", {})
        for sub_name, sub_rules in subcats.items():
            for rule in sub_rules:
                if rule.startswith("."):
                    continue
                if rule.lower() in text_lower:
                    return f"{cat_name}/{sub_name}"
        return None

    def _match_by_content(self, filepath: str) -> Tuple[Optional[str], float, str, Optional[str]]:
        """
        Extract text from inside the file (PDF/DOCX/plain text) and match
        category keywords against it. Solves 'documento(3).pdf' style names.
        Returns (category, confidence, reason, extracted_content).
        """
        if not self.config.get("options", {}).get("use_content_analysis", True):
            return None, 0, "", None

        content = content_extractor.extract_text(filepath)
        if not content:
            return None, 0, "", None

        content_lower = content.lower()
        categories = self.config.get("categories", {})

        best_category = None
        best_score = 0
        best_keywords: List[str] = []

        for cat_name, cat_config in categories.items():
            score = 0
            matched = []
            for kw in cat_config.get("keywords", []):
                kw_lower = kw.lower()
                # Whole-word occurrences only; content text is long and noisy
                hits = len(re.findall(r"(?<!\w)" + re.escape(kw_lower) + r"(?!\w)", content_lower))
                if hits:
                    score += min(hits, 3)  # cap so one repeated word doesn't dominate
                    matched.append(kw)
            if score > best_score:
                best_score = score
                best_category = cat_name
                best_keywords = matched

        # Content matching needs a stronger signal than filename matching
        if best_category and best_score >= 3:
            confidence = min(0.55 + (best_score * 0.05), 0.9)
            refined = self._match_subcategory(best_category, content_lower)
            reason = f"Content keywords: {', '.join(best_keywords[:4])}"
            return refined or best_category, confidence, reason, content

        return None, 0, "", content

    def _match_by_extension(self, ext: str, name_lower: str) -> Tuple[Optional[str], float, str]:
        """
        Match file by extension. Several categories can claim the same extension
        (.pdf, .zip); resolution is deterministic: a category whose subcategory
        keywords also match wins, otherwise the first match in config order.
        """
        categories = self.config.get("categories", {})
        first_match: Optional[str] = None

        for cat_name, cat_config in categories.items():
            extensions = cat_config.get("extensions", [])
            if ext not in extensions:
                continue
            if first_match is None:
                first_match = cat_name
            refined = self._match_subcategory(cat_name, name_lower)
            if refined:
                return refined, 0.8, f"Extension {ext} + subcategory keyword"

        if first_match:
            return first_match, 0.6, f"Extension match: {ext}"
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

    def _match_by_llm(self, filename: str, content: Optional[str] = None) -> Tuple[Optional[str], float, str]:
        """Match using LLM (Ollama or OpenAI) for ambiguous files."""
        options = self.config.get("options", {})
        if not options.get("use_llm_for_ambiguous", False):
            return None, 0, ""

        categories = self.config.get("categories", {})
        category_list = list(categories.keys())
        if not category_list:
            return None, 0, ""

        return self.llm.classify(filename, category_list, content_snippet=content)

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

    def _smart_name(self, filepath: str, filename: str) -> str:
        """Normalize filename: date prefix + sanitized name. Finding files later
        depends on the name as much as on the folder."""
        name, ext = os.path.splitext(filename)
        # Use file modification date (closer to 'when I got this' than today)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        except OSError:
            mtime = datetime.now()
        date_prefix = mtime.strftime("%Y-%m-%d")
        if re.match(r"^\d{4}-\d{2}-\d{2}", name):
            return filename  # already dated
        clean = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE)
        clean = re.sub(r"[\s]+", "_", clean).strip("_")
        clean = re.sub(r"_\(\d+\)$", "", clean)  # drop trailing (1), (2)
        if not clean:
            clean = "archivo"
        return f"{date_prefix}_{clean}{ext}"

    def organize(self, interactive: bool = False) -> List[ClassificationResult]:
        """Organize all files in every source folder."""
        results = []
        for source in self._source_folders():
            if not os.path.exists(source):
                print(f"Source folder not found: {source}")
                continue
            results.extend(self._organize_folder(source, interactive))

        self._save_history()
        self._print_summary(results)
        return results

    def _organize_folder(self, source: str, interactive: bool = False) -> List[ClassificationResult]:
        results = []
        target_base = os.path.abspath(self.config.get("target_base_folder", ""))
        files = [f for f in os.listdir(source) if os.path.isfile(os.path.join(source, f))]

        print(f"\nFound {len(files)} files to organize in: {source}")

        dry_run = self.config.get("options", {}).get("dry_run", False)
        review_threshold = self.config.get("options", {}).get("review_threshold", 0.5)

        for filename in files:
            filepath = os.path.join(source, filename)
            file_hash = self._hash_file(filepath)
            result = self.classify_file(filepath, file_hash)

            if result.category == "IGNORED":
                print(f"  [IGNORED] {filename} - {result.reason}")
                continue

            # duplicate_action 'skip': report the duplicate but leave it in place
            if result.method == "duplicate" and \
               self.config.get("options", {}).get("duplicate_action", "folder") == "skip":
                print(f"  [DUP SKIP] {filename} - {result.reason}")
                continue

            # Never move a file onto itself / inside the Organized tree
            if os.path.abspath(os.path.dirname(filepath)).startswith(target_base):
                continue

            # Interactive review for low-confidence classifications
            if interactive and result.confidence < review_threshold:
                decision = self._review_prompt(result)
                if decision == "skip":
                    print(f"  [SKIPPED] {filename}")
                    continue

            # Execute move
            if not dry_run:
                final_path = self._move_file(result)
                if final_path:
                    result.final_path = final_path
                    self.index.add(
                        filename=os.path.basename(final_path),
                        original_name=filename,
                        source_path=filepath,
                        final_path=final_path,
                        category=result.category,
                        method=result.method,
                        confidence=result.confidence,
                        reason=result.reason,
                        sha256=file_hash,
                        size_bytes=self._safe_size(final_path),
                    )
                    print(f"  [MOVED] {filename} -> {result.category} ({result.method}, confidence: {result.confidence:.2f})")
                else:
                    print(f"  [ERROR] Failed to move {filename}")
                    result.reason += " (MOVE FAILED)"
            else:
                print(f"  [DRY RUN] {filename} -> {result.category} ({result.method}, confidence: {result.confidence:.2f})")

            results.append(result)
            if not dry_run:
                # dry-run results must not pollute history/undo/index
                self.history.append(result)

        return results

    def _safe_size(self, path: str) -> int:
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def _review_prompt(self, result: ClassificationResult) -> str:
        """Ask the user to confirm a low-confidence classification.
        Returns 'accept', 'skip', or 'accept' after re-targeting."""
        categories = list(self.config.get("categories", {}).keys())
        print(f"\n  [REVIEW] {result.filename}")
        print(f"           Suggested: {result.category} (confidence {result.confidence:.2f}, {result.reason})")
        for i, cat in enumerate(categories, 1):
            print(f"           {i}. {cat}")
        answer = input("           Enter = accept | number = choose category | s = skip: ").strip().lower()
        if answer == "s":
            return "skip"
        if answer.isdigit() and 1 <= int(answer) <= len(categories):
            chosen = categories[int(answer) - 1]
            if chosen != result.category.split("/")[0]:
                self._learn_keywords(result.filename, chosen)
            result.category = chosen
            result.target_folder = self._build_target_path(chosen, result.filename)
            result.method = "user"
            result.confidence = 1.0
            result.reason = "User choice in review mode"
        return "accept"

    def _move_file(self, result: ClassificationResult) -> Optional[str]:
        """Move file to target folder, handling conflicts. Returns final path or None."""
        try:
            target_dir = result.target_folder
            os.makedirs(target_dir, exist_ok=True)

            filename = result.filename
            if self.config.get("options", {}).get("smart_rename", False):
                filename = self._smart_name(result.source_path, filename)
                if filename != result.filename:
                    print(f"    [RENAME] {result.filename} -> {filename}")

            target_path = os.path.join(target_dir, filename)

            # Handle duplicate filenames
            if os.path.exists(target_path):
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"{name}_{timestamp}{ext}"
                target_path = os.path.join(target_dir, new_name)
                print(f"    [RENAME] Duplicate found, renamed to: {new_name}")

            shutil.move(result.source_path, target_path)
            return target_path
        except Exception as e:
            print(f"    [ERROR] {e}")
            return None

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
            "content": "Content analysis",
            "extension": "File extension",
            "mime": "MIME type",
            "default": "Default fallback",
            "llm": "AI classification",
            "duplicate": "Duplicate detection",
            "user": "User review"
        }
        for method, count in sorted(methods.items(), key=lambda x: -x[1]):
            print(f"  {method_names.get(method, method)}: {count} files")

        print(f"\nTotal files organized: {len(results)}")
        print("="*60)

    def _learn_keywords(self, filename: str, correct_category: str):
        """Add meaningful words from a filename as keywords of a category."""
        categories = self.config.get("categories", {})
        if correct_category not in categories:
            print(f"Unknown category: {correct_category}")
            return
        name_without_ext = os.path.splitext(filename)[0]
        words = [w for w in name_without_ext.replace("_", " ").replace("-", " ").split()
                 if len(w) > 3]
        for word in words[:3]:
            word_lower = word.lower()
            if word_lower not in categories[correct_category].get("keywords", []):
                categories[correct_category]["keywords"].append(word_lower)
                print(f"  Added keyword '{word_lower}' to '{correct_category}'")
        self._save_config()

    def correct_classification(self, filename: str, correct_category: str):
        """Learn from user correction AND move the file to the right folder."""
        for result in reversed(self.history):
            if result.filename == filename or os.path.basename(result.final_path or "") == filename:
                print(f"Learning: '{filename}' should be '{correct_category}' (was: {result.category})")
                self._learn_keywords(filename, correct_category)

                # Actually relocate the file (previously it only learned)
                current_path = result.final_path or os.path.join(result.target_folder, result.filename)
                if os.path.exists(current_path):
                    new_dir = self._build_target_path(correct_category, filename)
                    os.makedirs(new_dir, exist_ok=True)
                    new_path = os.path.join(new_dir, os.path.basename(current_path))
                    if os.path.exists(new_path):
                        name, ext = os.path.splitext(os.path.basename(current_path))
                        new_path = os.path.join(new_dir, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                    try:
                        shutil.move(current_path, new_path)
                        print(f"  Moved: {current_path} -> {new_path}")
                        self.index.remove_by_final_path(current_path)
                        self.index.add(
                            filename=os.path.basename(new_path),
                            original_name=result.filename,
                            source_path=result.source_path,
                            final_path=new_path,
                            category=correct_category,
                            method="user",
                            confidence=1.0,
                            reason="Corrected by user",
                            size_bytes=self._safe_size(new_path),
                        )
                        result.category = correct_category
                        result.target_folder = new_dir
                        result.final_path = new_path
                        self._save_history()
                    except Exception as e:
                        print(f"  [ERROR] Could not move file: {e}")
                else:
                    print(f"  File not found on disk, only keywords were learned: {current_path}")
                return
        print(f"'{filename}' not found in history. Keywords learned anyway.")
        self._learn_keywords(filename, correct_category)

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
            # Use the real final path (handles files renamed on collision)
            target = result.final_path or os.path.join(result.target_folder, result.filename)

            if os.path.exists(target) and not os.path.exists(source):
                try:
                    shutil.move(target, source)
                    self.index.remove_by_final_path(target)
                    print(f"[UNDO] Restored: {result.filename} -> {os.path.dirname(source)}")
                except Exception as e:
                    print(f"[UNDO FAILED] {result.filename}: {e}")
            else:
                print(f"[UNDO SKIP] Cannot undo {result.filename} (file not found or already exists)")

    def find(self, query: str):
        """Search the index for organized files: --find 'estado cuenta'."""
        rows = self.index.search(query)
        if not rows:
            print(f"No results for: '{query}'")
            print("Tip: search matches filename, category and classification reason.")
            return
        print(f"\n{len(rows)} result(s) for '{query}':\n")
        for row in rows:
            exists = "OK" if row["final_path"] and os.path.exists(row["final_path"]) else "MISSING"
            date = (row["moved_at"] or "")[:10]
            print(f"  [{exists}] {row['filename']}")
            print(f"        Category: {row['category']}  |  Organized: {date}")
            print(f"        Path: {row['final_path']}")
            if row["original_name"] and row["original_name"] != row["filename"]:
                print(f"        Original name: {row['original_name']}")
            print()

    def report(self, days: int = 7):
        """Print activity report: --report."""
        data = self.index.report(days)
        gb = data["total_bytes"] / (1024 ** 3)
        print("\n" + "=" * 60)
        print("ORGANIZER REPORT")
        print("=" * 60)
        print(f"\nTotal organized files: {data['total_files']} ({gb:.2f} GB)")
        print(f"Organized in last {data['days']} days: {data['recent_files']}")
        print(f"Files in 'Otros' (need better rules): {data['otros_count']}")
        print(f"Duplicate content groups detected: {data['duplicate_groups']}")

        if data["recent_by_category"]:
            print(f"\nLast {data['days']} days by category:")
            for row in data["recent_by_category"]:
                print(f"  {row['category']}: {row['c']}")

        print("\nAll time by category:")
        for row in data["by_category"][:15]:
            size_mb = row["s"] / (1024 ** 2)
            print(f"  {row['category']}: {row['c']} files ({size_mb:.0f} MB)")

        if data["low_confidence"]:
            print("\nRecent low-confidence classifications (review these):")
            for row in data["low_confidence"]:
                print(f"  {row['filename']} -> {row['category']} ({row['confidence']:.2f})")
        print("=" * 60)

    def dedupe(self, preview: bool = False, include_sources: bool = False):
        """
        Scan the whole Organized tree (and optionally the source folders),
        group files by SHA-256, keep one copy per group and move the rest to
        Duplicados/. Cleans up the historical backlog of file(1), file(2) copies.
        Nothing is ever deleted.
        """
        base = self.config.get("target_base_folder", "")
        if not os.path.isdir(base):
            print(f"Target folder not found: {base}")
            return
        dup_dir = os.path.join(
            base, self.config.get("options", {}).get("duplicates_folder", "Duplicados")
        )
        roots = [base]
        if include_sources:
            roots += [f for f in self._source_folders() if os.path.isdir(f)]

        print("Scanning for duplicate content" + (" (PREVIEW, nothing will move)" if preview else "") + "...")
        groups: Dict[str, List[str]] = {}
        seen = set()
        scanned = 0
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                # Duplicados/ itself is excluded: already triaged
                if os.path.abspath(dirpath).startswith(os.path.abspath(dup_dir)):
                    continue
                for fn in filenames:
                    path = os.path.join(dirpath, fn)
                    ap = os.path.abspath(path)
                    if ap in seen or not os.path.isfile(path):
                        continue
                    seen.add(ap)
                    h = self._hash_file(path, force=True)
                    scanned += 1
                    if h:
                        groups.setdefault(h, []).append(path)

        dup_groups = {h: fs for h, fs in groups.items() if len(fs) > 1}
        print(f"Scanned {scanned} files. Duplicate groups found: {len(dup_groups)}")
        if not dup_groups:
            return

        moved = 0
        for files in dup_groups.values():
            keeper = self._pick_keeper(files)
            print(f"\n  KEEP: {keeper}")
            for f in files:
                if f == keeper:
                    continue
                if preview:
                    print(f"  would move -> Duplicados: {f}")
                    continue
                os.makedirs(dup_dir, exist_ok=True)
                target = os.path.join(dup_dir, os.path.basename(f))
                if os.path.exists(target):
                    name, ext = os.path.splitext(os.path.basename(f))
                    target = os.path.join(dup_dir, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                try:
                    shutil.move(f, target)
                    self.index.update_final_path(f, target)
                    moved += 1
                    print(f"  moved -> {target}")
                except Exception as e:
                    print(f"  [ERROR] {f}: {e}")

        if not preview:
            print(f"\nMoved {moved} duplicate file(s) to: {dup_dir}")
            print("Review that folder and empty it manually when you're sure.")

    def _pick_keeper(self, files: List[str]) -> str:
        """Which copy of a duplicate group survives: prefer a copy the index
        knows about, then the oldest (usually the original download), then
        the shortest name (file.pdf over file(2).pdf)."""
        indexed = [f for f in files if self.index.get_by_final_path(f)]
        pool = indexed or files
        def sort_key(p: str):
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                mtime = float("inf")
            return (mtime, len(os.path.basename(p)))
        return min(pool, key=sort_key)

    def watch(self):
        """Watch source folders and organize new files as they appear.
        A file is processed only when its size is stable between two scans
        (i.e., the download finished). Ctrl+C to stop."""
        interval = self.config.get("options", {}).get("watch_interval_seconds", 30)
        folders = [f for f in self._source_folders() if os.path.exists(f)]
        if not folders:
            print("No valid source folders to watch.")
            return
        print(f"Watching (every {interval}s): {', '.join(folders)}")
        print("Press Ctrl+C to stop.\n")

        previous_sizes: Dict[str, int] = {}
        try:
            while True:
                current_sizes: Dict[str, int] = {}
                stable_found = False
                for folder in folders:
                    try:
                        entries = os.listdir(folder)
                    except OSError:
                        continue
                    for name in entries:
                        path = os.path.join(folder, name)
                        if not os.path.isfile(path):
                            continue
                        size = self._safe_size(path)
                        current_sizes[path] = size
                        if previous_sizes.get(path) == size:
                            stable_found = True
                if stable_found and previous_sizes:
                    self.organize()
                previous_sizes = current_sizes
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nWatch stopped.")

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
    parser.add_argument("--correct", nargs=2, metavar=("FILE", "CATEGORY"), help="Teach the agent AND move the file: --correct 'file.pdf' 'Libros'")
    parser.add_argument("--find", type=str, metavar="QUERY", help="Search organized files: --find 'estado cuenta'")
    parser.add_argument("--report", action="store_true", help="Show activity report and stats")
    parser.add_argument("--report-days", type=int, default=7, help="Days window for --report (default 7)")
    parser.add_argument("--review", action="store_true", help="Organize interactively: confirm low-confidence files")
    parser.add_argument("--watch", action="store_true", help="Keep running and organize new files automatically")
    parser.add_argument("--dedupe", action="store_true", help="Find duplicate content across Organized and move copies to Duplicados/ (combine with --scan to preview)")
    parser.add_argument("--dedupe-sources", action="store_true", help="With --dedupe: also scan the source folders (Downloads, Documents)")

    args = parser.parse_args()

    agent = FileClassifier()

    if args.dedupe:
        agent.dedupe(preview=args.scan, include_sources=args.dedupe_sources)
    elif args.undo > 0:
        agent.undo_last(args.undo)
    elif args.correct:
        agent.correct_classification(args.correct[0], args.correct[1])
    elif args.find:
        agent.find(args.find)
    elif args.report:
        agent.report(args.report_days)
    elif args.watch:
        agent.watch()
    elif args.scan:
        print("SCAN MODE (no files will be moved)")
        agent.scan_only()
    elif args.review:
        print("REVIEW MODE (low-confidence files will ask for confirmation)")
        agent.organize(interactive=True)
    else:
        agent.organize()
