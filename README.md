# Organizer Agent para Descargas

Un agente de Python que organiza automaticamente tu carpeta de Descargas clasificando archivos por tipo: **Libros**, **Trabajo**, **Estudio_PM**, **Documentos Personales**, **Software**, y mas.

## Inicio rapido (5 minutos)

1. **Instala Python** desde https://python.org/downloads/ (marca "Add Python to PATH")
2. **Copia el archivo de configuracion de ejemplo** a tu archivo local:
   - Copia `config.example.json` y renombralo como `config.json`
3. **Edita `config.json`** y reemplaza `TU_USUARIO` con tu usuario real de Windows
4. **Prueba sin mover nada**: `python organizer.py --scan`
5. **Organiza de verdad**: `python organizer.py`

O simplemente haz doble clic en `organizar.bat` (despues de configurar tu usuario en el .bat y en config.json).

---

## Que hace?

Cuando descargas archivos, se acumulan todos mezclados. Este script los ordena automaticamente en carpetas:

```
Downloads/
├── Organized/
│   ├── Libros/
│   │   ├── Programacion/
│   │   ├── Negocios/
│   │   ├── Ficcion/
│   │   ├── Autoayuda/
│   │   └── Educacion/
│   ├── Trabajo/
│   │   ├── Contratos/
│   │   ├── Facturas/
│   │   ├── Presentaciones/
│   │   └── Reportes/
│   ├── Documentos_Personales/
│   │   ├── Identificacion/
│   │   ├── Salud/
│   │   ├── Servicios/
│   │   ├── Bancarios/
│   │   └── Escolares/
│   ├── Software/
│   │   ├── Sistemas_Operativos/
│   │   ├── Desarrollo/
│   │   ├── Oficina/
│   │   ├── Multimedia/
│   │   ├── Seguridad/
│   │   └── Utilidades/
│   ├── Multimedia/
│   │   ├── Peliculas/
│   │   ├── Series/
│   │   ├── Musica/
│   │   ├── Cursos_Video/
│   │   └── Podcasts/
│   ├── Imagenes/
│   │   ├── Screenshots/
│   │   ├── Fotos/
│   │   ├── Diseno/
│   │   └── Wallpapers/
│   ├── Comprimidos/
│   ├── Estudio_PM/
│   │   ├── Certificaciones/
│   │   ├── Metodologias_Agiles/
│   │   ├── Herramientas_PM/
│   │   ├── Plantillas/
│   │   └── Cursos_Video/
│   ├── Codigo_Fuente/
│   │   ├── Python/
│   │   ├── JavaScript/
│   │   ├── Web/
│   │   ├── Mobile/
│   │   └── Data/
│   └── Otros/
```

## Como clasifica?

El agente usa 5 metodos (en orden de prioridad):

0. **Deteccion de duplicados** (antes de clasificar)
   - Calcula el hash SHA-256 del archivo; si un archivo con contenido identico
     ya existe en Organized, lo manda a `Duplicados/` en vez de duplicarlo

1. **Palabras clave en el nombre** (mas importante)
   - Ejemplo: `reporte_q4_2024.docx` -> Trabajo/Reportes
   - Ejemplo: `python_crash_course.pdf` -> Libros/Programacion

2. **Analisis de contenido** (lee DENTRO del archivo)
   - Para PDF (requiere `pip install pypdf`), DOCX y archivos de texto
   - Ejemplo: `documento(3).pdf` cuyo contenido dice "estado de cuenta credito
     infonavit" -> Infonavit/Estados_de_Cuenta
   - Resuelve los archivos con nombres genericos (`scan_001.pdf`, `Descarga(4).pdf`)

3. **Extension del archivo**
   - Ejemplo: `.epub`, `.mobi` -> Libros
   - Ejemplo: `.exe`, `.msi` -> Software

4. **Tipo MIME** (fallback)

5. **IA con Ollama** (opcional, cuando los metodos anteriores fallan)
   - Envia el nombre del archivo Y un extracto del contenido a un LLM local
   - Requiere tener Ollama instalado y activarlo en `config.json`

Tambien puede aprender de tus correcciones!

## Instalacion

### Paso 1: Instalar Python

1. Ve a https://python.org/downloads/
2. Descarga la ultima version de Python (3.8 o superior)
3. Ejecuta el instalador
4. **IMPORTANTE:** Marca la casilla **"Add Python to PATH"** antes de dar clic en Install Now
5. Espera a que termine la instalacion

**Verificar instalacion:**
- Abre una terminal (CMD o PowerShell)
- Escribe: `python --version`
- Deberia mostrar algo como `Python 3.11.x`

Si dice "python no se reconoce", reinstala Python y asegurate de marcar "Add Python to PATH".

### Paso 2: Descargar este proyecto

- Descarga el ZIP o clona el repositorio
- Extrae los archivos en una carpeta, por ejemplo: `C:\Users\TU_USUARIO\downloads-organizer`

### Paso 3: Crear tu archivo de configuracion

1. Copia el archivo de ejemplo `config.example.json` y renombralo como `config.json`
2. Obten tu nombre de usuario de Windows (abre CMD o PowerShell y escribe: `echo %USERNAME%`)
3. Abre el archivo `config.json` con cualquier editor de texto (Notepad, VS Code, etc.)
4. Busca las lineas con `TU_USUARIO` y reemplazalo con tu nombre de usuario real:
   ```json
   "source_folders": [
     "C:/Users/TU_USUARIO/Downloads",
     "C:/Users/TU_USUARIO/Documents"
   ],
   "target_base_folder": "C:/Users/TU_USUARIO/Downloads/Organized"
   ```
   Puedes vigilar una o varias carpetas (Descargas, Documentos, Escritorio...).
   Solo se mueven los **archivos sueltos** en la raiz de cada carpeta; las
   subcarpetas (proyectos, etc.) no se tocan. El formato viejo con
   `"source_folder"` (una sola carpeta, string) sigue funcionando.

   > **Recomendacion:** pon `target_base_folder` en `Documents/Organized`, no
   > en Downloads. Documents lo respalda OneDrive por defecto en Windows 11 y
   > Downloads es zona de transito que cualquiera limpia sin pensar.
5. Guarda el archivo

> **Importante:** El archivo `config.json` es local y NO se sube a GitHub (esta en `.gitignore`). Esto protege tus rutas personales y cualquier API key que configures. Si necesitas compartir tu configuracion, usa `config.example.json` como plantilla.

**Nota:** Usa slashes `/` en lugar de backslashes `\` en las rutas.

### Paso 4: (Opcional) Personalizar categorias

El archivo `config.json` ya viene con categorias predefinidas. Puedes:
- Agregar mas palabras clave a cualquier categoria
- Crear nuevas categorias
- Modificar las existentes
- Agregar o quitar subcategorias

Ejemplo: Si trabajas en algo especifico, agrega palabras clave a "Trabajo":
```json
"Trabajo": {
  "keywords": ["reporte", "proyecto", ... , "mi_empresa", "nombre_cliente"]
}
```

## Uso

### Ejecutar desde terminal

1. Abre CMD o PowerShell
2. Navega a la carpeta del proyecto:
   ```bash
   cd C:\Users\TU_USUARIO\downloads-organizer
   ```
3. Ejecuta uno de los siguientes comandos:

### Modo normal (mueve los archivos)
```bash
python organizer.py
```
Este comando lee tu carpeta de Descargas y mueve los archivos a las subcarpetas correspondientes dentro de `Organized/`.

### Modo preview (recomendado la primera vez)
```bash
python organizer.py --scan
```
**No mueve ningun archivo**, solo muestra en pantalla que haria. Usalo la primera vez para verificar que la clasificacion sea correcta.

### Deshacer ultimos movimientos
```bash
python organizer.py --undo 5
```
Devuelve los ultimos 5 archivos movidos de vuelta a tu carpeta de Descargas. Cambia `5` por el numero que necesites.

### Buscar un archivo organizado (para no perder el hilo!)
```bash
python organizer.py --find "estado cuenta"
python organizer.py --find "recibo cfe"
```
Busca en el indice (nombre, nombre original, categoria y razon de clasificacion)
y te dice exactamente en que carpeta quedo cada archivo y cuando se organizo.

### Reporte de actividad
```bash
python organizer.py --report
python organizer.py --report --report-days 30
```
Muestra: total organizado, actividad reciente, cuantos archivos cayeron en "Otros"
(senal de que faltan reglas), duplicados detectados y clasificaciones de baja
confianza que conviene revisar.

### Limpiar duplicados acumulados (los famosos (1), (2))
```bash
python organizer.py --dedupe --scan     # preview: solo muestra, no mueve
python organizer.py --dedupe            # ejecuta
python organizer.py --dedupe --dedupe-sources   # incluye tambien Downloads/Documents
```
Escanea todo Organized, agrupa por contenido (SHA-256, no por nombre), conserva
una copia por grupo (prefiere la indexada, luego la mas antigua, luego el nombre
mas corto) y mueve el resto a `Duplicados/`. **Nunca borra nada** — revisas esa
carpeta y la vacias tu cuando estes seguro. Detecta tambien duplicados con
nombres distintos en carpetas distintas.

Para los duplicados que van llegando dia a dia, la opcion `duplicate_action`
en config controla que hacer: `"folder"` (default, van a Duplicados/) o
`"skip"` (se quedan donde estan, solo se reporta).

### Modo revision interactiva
```bash
python organizer.py --review
```
Los archivos con confianza baja (< 0.5) te preguntan antes de moverse: Enter
acepta la sugerencia, un numero elige otra categoria (y el agente aprende), `s` lo salta.

### Modo vigilancia (organiza solo, en tiempo real)
```bash
python organizer.py --watch
```
Se queda corriendo y organiza los archivos nuevos en cuanto terminan de
descargarse (espera a que el tamano se estabilice). Ctrl+C para detener.

### Ensenar al agente (cuando se equivoca)
```bash
python organizer.py --correct "archivo_mal_clasificado.pdf" "Trabajo"
```
El agente aprende que archivos similares van en esa categoria **y ademas mueve
el archivo** a la carpeta correcta.

### Ejecutar con doble clic (mas facil)

Si no quieres usar la terminal, puedes usar el archivo `organizar.bat`:

1. Abre `organizar.bat` con un editor de texto
2. Cambia `TU_USUARIO` por tu nombre de usuario real en la ruta
3. Guarda el archivo
4. Haz doble clic en `organizar.bat` y se ejecutara automaticamente

## Como funciona internamente

```
Descargas/
  archivo_1.pdf
  archivo_2.docx
  ...
     |
     v
  [organizer.py]
     |
      +-- Lee nombre del archivo
      |     +-- Busca palabras clave -> Categoria
      |     +-- Si no, usa extension -> Categoria
      |     +-- Si no, tipo MIME -> Categoria
      |     +-- Si no y LLM activado, consulta Ollama -> Categoria
      |     +-- Si no, "Otros"
     |
     +-- Crea carpetas si no existen
     |
     +-- Mueve archivo a carpeta destino
     |     +-- Si ya existe, renombra con fecha
     |
     +-- Guarda historial (para undo)
```

## Ejemplos de clasificacion

| Archivo | Detecta por | Va a |
|---------|-------------|------|
| `pmp_exam_prep.pdf` | keyword "pmp" | Estudio_PM/Certificaciones |
| `scrum_master_guide.pdf` | keyword "scrum" | Estudio_PM/Metodologias_Agiles |
| `jira_workflow_template.xlsx` | keyword "jira" | Estudio_PM/Herramientas_PM |
| `clean_code.pdf` | keyword "code" + ext .pdf | Libros/Programacion |
| `recibo_luz_enero.pdf` | keyword "recibo luz" | Documentos_Personales/Servicios |
| `setup_visual_studio.exe` | keyword "visual studio" | Software/Desarrollo |
| `avatar.png` | keyword "avatar" | Imagenes |
| `data_analysis.py` | ext .py | Codigo_Fuente/Python |
| `documento_sin_nombre.txt` | ext .txt -> no match -> default | Otros/Texto_Plano |

## Aprendizaje

El agente mejora cuando le corriges:

1. Corre el organizador
2. Ves que `mi_proyecto_python.pdf` fue a "Otros" en vez de "Libros/Programacion"
3. Corre:
   ```bash
   python organizer.py --correct "mi_proyecto_python.pdf" "Libros"
   ```
4. El agente agrega "python" y "proyecto" como palabras clave de "Libros"
5. La proxima vez, archivos similares iran a Libros

## Configuracion avanzada

### Ignorar ciertos archivos
En `config.json`:
```json
"rules": {
  "ignore_patterns": ["*.tmp", "*.crdownload"],
  "ignore_folders": ["Organized", "temp"]
}
```

### Subcarpetas por mes
```json
"options": {
  "create_month_subfolders": true
}
```
Crea: `Libros/2025-01/`, `Libros/2025-02/`, etc.

### Dry run (nunca mueve nada)
```json
"options": {
  "dry_run": true
}
```

### Clasificacion con IA (Ollama)

Cuando palabras clave, extension y MIME no logran clasificar un archivo, puedes usar un LLM local con Ollama:

**Requisitos:**
1. Instala Ollama desde https://ollama.com
2. Descarga un modelo: `ollama pull mistral`
3. En `config.json` activa:
```json
"options": {
  "use_llm_for_ambiguous": true,
  "llm_provider": "ollama",
  "llm_model": "mistral:latest",
  "llm_ollama_url": "http://localhost:11434"
}
```
4. El agente enviara los nombres de archivo a Ollama y usara su respuesta para clasificar

**Proveedores soportados:**
- `"ollama"` - local, gratuito, sin API key. Corre cualquier modelo de Ollama,
  incluyendo DeepSeek: `ollama pull deepseek-r1:8b` y pon ese nombre en `llm_model`.
  Los modelos razonadores (deepseek-r1, qwq) funcionan: el agente les limpia el
  bloque `<think>` automaticamente.
- `"openai"` - cualquier API compatible con OpenAI (requiere `pip install openai`
  y API key). Para DeepSeek en la nube:
  ```json
  "llm_provider": "openai",
  "llm_model": "deepseek-chat",
  "llm_base_url": "https://api.deepseek.com",
  "llm_api_key": "sk-..."
  ```
  Con `llm_base_url` vacio usa OpenAI normal. Tambien sirve para Groq, Together, etc.

**Modelos recomendados (Ollama local):**
- `mistral:latest` (~4.4 GB) - mejor balance velocidad/calidad
- `deepseek-r1:8b` (~5 GB) - razonador, mas preciso en casos ambiguos pero mas lento
- `phi3:latest` (~2.2 GB) - mas ligero
- `tinyllama:latest` (~637 MB) - el mas rapido pero menos preciso

## Automatizar (opcional)

### Windows: Ejecutar cada vez que enciendes la PC

1. Presiona `Win + R`, escribe `shell:startup` y dale Enter
2. Crea un acceso directo al archivo `organizar.bat` en esa carpeta
3. Ahora se ejecuta cada vez que inicias sesion

### Windows: Programar tarea cada hora

1. Busca "Programador de tareas" en el menu de inicio y abre la app
2. En el panel derecho, clic en **"Crear tarea basica..."**
3. Ponle nombre: "Organizar Descargas"
4. Trigger: Elige la frecuencia (diaria, al iniciar sesion, etc.)
5. Accion: **"Iniciar un programa"**
6. Programa: `python`
7. Argumentos: `organizer.py`
8. Iniciar en: `C:\Users\TU_USUARIO\downloads-organizer`
9. Finaliza el asistente

### Ejecutar manualmente cuando quieras

- **Opcion A:** Haz doble clic en `organizar.bat` (si ya configuraste tu usuario)
- **Opcion B:** Abre terminal y corre `python organizer.py`

## Historial

El agente guarda todo lo que hace en `organizer_history.json`. Puedes revisarlo para ver:
- Que archivo movio
- A donde lo movio
- Por que lo clasifico asi
- Cuando lo hizo

> **Importante:** `organizer_history.json` es local y NO se sube a GitHub (esta en `.gitignore`). Contiene rutas personales de tu PC. Para referencia del formato, consulta `organizer_history.example.json`.

## Categoria especial: Estudio de Project Management (PM)

Si estudias PM diariamente (como tus 2 horas diarias), el agente ya detecta automaticamente:

**Palabras clave detectadas:**
- Certificaciones: `pmp`, `capm`, `prince2`, `pmi`
- Metodologias: `agile`, `scrum`, `kanban`, `lean`, `safe`
- Herramientas: `jira`, `ms project`, `asana`, `trello`, `notion`
- Conceptos: `cronograma`, `wbs`, `roadmap`, `stakeholder`, `earned value`, `burn down`
- Documentos: `charter`, `rfp`, `sow`, `acta constitutiva`, `linea base`

**Subcarpetas automaticas:**
- `Estudio_PM/Certificaciones/` - Para material de PMP, CAPM, PRINCE2
- `Estudio_PM/Metodologias_Agiles/` - Scrum, Kanban, SAFe
- `Estudio_PM/Herramientas_PM/` - Jira, MS Project, etc.
- `Estudio_PM/Plantillas/` - Templates, checklists, formatos
- `Estudio_PM/Cursos_Video/` - Cursos, webinars, masterclass

**Consejo:** Si descargas mucho material de PM, manten esta carpeta sincronizada con tu app de notas (Notion, Obsidian) para tener todo a la mano durante tu estudio.

## Notas importantes

- **Nunca borra archivos**, solo los mueve
- **Si hay duplicados**, renombra con fecha/hora
- **Si no sabe donde poner algo**, lo pone en "Otros"
- **Revisa "Otros" de vez en cuando** para mejorar las reglas
- **Haz backup** la primera vez si tienes archivos importantes en Descargas

## Requisitos

- Python 3.8 o superior
- Windows, Mac o Linux
- **No necesitas instalar nada con pip** para el uso basico - funciona con la libreria estandar
- Recomendado: `pip install pypdf` para que el analisis de contenido lea PDFs
  (DOCX y archivos de texto funcionan sin instalar nada)

## Licencia

MIT - Usalo, modificalo, compartilo.

## Solucion de problemas

### "python" no se reconoce como comando
- Reinstala Python y asegurate de marcar **"Add Python to PATH"**
- O usa `py` en lugar de `python`: `py organizer.py`

### Los archivos no se mueven
- Verifica que `config.json` tenga las rutas correctas con tu nombre de usuario real
- Usa slashes `/` no backslashes `\` en las rutas
- Ejecuta primero con `--scan` para ver que detecta

### Error de permisos
- Ejecuta la terminal como Administrador
- O verifica que tengas acceso a la carpeta de Descargas

### Quiero probar sin mover nada
- Usa `python organizer.py --scan` (solo muestra, no mueve)
- O en `config.json` pon `"dry_run": true` en la seccion `options`
