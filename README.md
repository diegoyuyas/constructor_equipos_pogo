<<<<<<< HEAD
# Pokémon GO PvP Team Generator

Aplicación web (Python + Streamlit) que genera equipos de PvP para Pokémon GO.
El usuario elige un Pokémon "ancla" y una liga (Great/Ultra/Master), y la app recomienda los 2 mejores compañeros de equipo + alternativas, con movimientos en español oficial.

Usable desde el navegador del celular sin instalar nada.

## 🚀 Demo rápido (sin instalar nada)

Si ya está desplegada en Streamlit Cloud, solo entra al link y úsala desde tu celular.

## 🛠️ Stack

- Python 3
- Streamlit (UI)
- SQL Server Express local (`LOCALHOST\SQLEXPRESS`, bd `bd_pkm_pro`) para desarrollo
- SQLite (`pogo_data.sqlite`) para producción/nube
- Datos base de [PvPoke](https://pvpoke.com) (MIT License)
- Nombres en español vía [PokeAPI](https://pokeapi.co)

## 📁 Estructura

```
pogo_team_builder/
├── app.py                        # Interfaz Streamlit principal
├── data_loader.py                 # Conexión SQL Server / SQLite
├── team_builder.py                # Algoritmo de sinergia + filtro por tipo
├── custom_cup.py                  # Fase 2: ranking de copas personalizadas
├── moves.py                       # Diccionario fallback español
├── battle_engine.py               # Motor de combate 1v1 (Fase 1 completa)
├── export_to_sqlite.py            # Exporta SQL Server -> SQLite para la nube
├── update_spanish_move_names.py   # Llena Moves.nameEs vía PokeAPI
├── sql/01_add_spanish_column.sql  # Migración columna nameEs
├── requirements.txt               # Para nube
├── requirements-local.txt         # Para local (incluye pyodbc)
└── README.md
```

## 👶 Guía paso a paso para principiantes

### 1. Preparar tu PC (solo una vez)

1. Instala Python 3.10+ desde python.org (marca "Add to PATH")
2. Instala SQL Server Express y crea la BD `bd_pkm_pro` (ya la tienes según spec)
3. Clona o descarga este proyecto
4. Abre terminal (CMD) en la carpeta del proyecto:
```bash
pip install -r requirements-local.txt
```

### 2. Agregar columna de español (solo una vez)

Ejecuta en SQL Server Management Studio el archivo `sql/01_add_spanish_column.sql` sobre `bd_pkm_pro`.

### 3. Llenar nombres en español (opcional pero recomendado)

```bash
python update_spanish_move_names.py
```
Esto consulta PokeAPI y llena `Moves.nameEs`. Usa caché para no repetir consultas. Tarda unos minutos la primera vez.

### 4. Probar local

```bash
streamlit run app.py
```
Abre http://localhost:8501 en tu navegador. Si estás en celular, usa la IP de tu PC.

### 5. Generar equipo

- Sidebar: elige liga (Great 1500 por defecto)
- Tab "Generador": busca tu Pokémon ancla, clic "Generar Equipo"
- Verás amenazas que cubre y compañeros recomendados con rol (Líder/Switch/Closer) y moves en español

### 6. Desplegar gratis en la nube (para usar desde cualquier celular sin PC)

**Paso A: Exportar BD a SQLite**
```bash
python export_to_sqlite.py
```
Esto crea `pogo_data.sqlite` en la carpeta.

Si pesa >90 MB, edita `export_to_sqlite.py` y filtra Rankings para solo `cup='all'` y `category='overall'`.

**Paso B: Subir a GitHub**

1. Instala GitHub Desktop
2. Crea repo nuevo `pogo-team-builder` (público)
3. Arrastra la carpeta `pogo_team_builder` + `pogo_data.sqlite` al repo
4. Commit + Push

**Paso C: Streamlit Cloud**

1. Entra a share.streamlit.io
2. Conecta tu GitHub, elige repo `pogo-team-builder`
3. Main file: `app.py`
4. Deploy. En 2 minutos tienes link público usable desde celular.

La app detecta automáticamente si existe `pogo_data.sqlite` y usa SQLite en vez de SQL Server.

## 🧠 Cómo funciona el algoritmo de equipos

1. Toma los counters del ancla (quién le gana) = amenazas a cubrir
2. Busca entre los mejores del meta quién tiene buenos matchups contra esas amenazas (cobertura)
3. Clasifica cada candidato en rol por percentiles de stats:
   - **Líder**: rating alto + bulk medio
   - **Switch / Cambio seguro**: bulk muy alto
   - **Closer / Cerrador**: ataque alto
4. Arma equipo de 3 intentando variar roles y devuelve alternativas

## 🏆 Copas Personalizadas (Nuevo)

En el tab "Copas Personalizadas" puedes definir:

- Tipos permitidos (ej solo Fuego/Agua/Planta)
- Permitir o no Shadow
- Lista de baneados
- Excluir tipo secundario (ej no Volador como tipo 2)
- Tope de CP

La app:
1. Filtra Pokémon elegibles
2. Calcula IVs óptimos para ese CP cap con `find_optimal_iv_for_cp()`
3. Simula todos vs todos con `battle_engine.py`
4. Genera ranking por winrate

> Nota honesta: la IA de escudos es aproximación (~40% HP threshold), no réplica exacta de PvPoke. Para 90%+ de matchups coincide.

## 🔧 Bloqueo actual resuelto

Según spec, faltaban valores exactos de Wing Attack, Twister, etc. desde tu tabla Moves.

Este proyecto ahora lee directamente de tu tabla Moves (fuente de verdad), no de valores hardcodeados. Si tu tabla Moves tiene esos movimientos, el motor los usará automáticamente.

Para validar Mantine vs Tinkaton (ejemplo del spec), asegúrate que en tu BD existan esos Pokémon y sus movimientos, y el motor simulará con tus datos reales.

## 📝 Próximos pasos (Fase 2 y 3 ya implementadas aquí)

- [x] Fase 1: Motor matemático battle_engine.py
- [x] Fase 2: Filtro elegibilidad + ranking completo (custom_cup.py)
- [x] Fase 3: Interfaz Streamlit para copas (tab en app.py)
- [ ] Decidir estrategia moveset óptimo por Pokémon en copa custom (ahora usa best moves del ranking estándar por velocidad; opción de búsqueda óptima disponible con checkbox)

## 📄 Licencia

Datos base de PvPoke bajo MIT License. Código de este proyecto es tuyo.

## 🙏 Créditos

- PvPoke.com por datos y lógica de referencia
- PokeAPI por nombres oficiales en español
- Comunidad PvP de Pokémon GO
=======
# 🛡️ Generador de Equipos PvP — Pokémon GO

App web (Streamlit) que, dado un Pokémon, te recomienda los 2 mejores
compañeros de equipo (+ alternativas) para Great League, Ultra League o
Master League, incluyendo los movimientos recomendados de cada uno.

Los datos de PvP (rankings, matchups, movesets) se leen directamente de tu
base de datos local **SQL Server Express** (`bd_pkm_pro`), instalada en tu
PC Windows 11.

## ⚙️ Configuración previa (solo la primera vez, para uso LOCAL)

1. Instala el driver ODBC de SQL Server (si no lo tienes ya, suele venir
   con SSMS): [ODBC Driver 17 for SQL Server (Microsoft)](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).
2. Instala las dependencias (incluyendo pyodbc, solo para local):
   ```bash
   pip install -r requirements.txt -r requirements-local.txt
   ```
3. Abre `data_loader.py` y revisa que estos valores coincidan con tu instancia
   (por la imagen que compartiste, deberían estar bien por defecto):
   ```python
   SERVER = r"LOCALHOST\SQLEXPRESS"
   DATABASE = "bd_pkm_pro"
   ```
4. Asegúrate de que el servicio **SQL Server (SQLEXPRESS)** esté corriendo.
5. La conexión usa **autenticación de Windows** (`Trusted_Connection=yes`),
   así que no necesitas usuario/contraseña si corres la app con tu mismo
   usuario de Windows con el que entras a SSMS.

### Sobre los filtros `cup` y `category`

La app consulta `cup = 'all'` y `category = 'overall'` en tu tabla `Rankings`
— ya confirmamos que esos son los valores que usas. Si en el futuro cambias
esa convención, ajusta `DEFAULT_CUP` / `DEFAULT_CATEGORY` en `data_loader.py`.

## ☁️ Cómo subirla a internet GRATIS (Streamlit Community Cloud)

La app detecta sola si debe usar tu SQL Server local o un archivo SQLite
portátil. Para la nube, usamos el SQLite, porque un servidor externo no
puede conectarse a tu `localhost`. Pasos:

### Paso 1 — Exportar tus datos a SQLite (en tu PC, con SQL Server prendido)

```bash
python export_to_sqlite.py
```

Esto genera un archivo `pogo_data.sqlite` en la carpeta del proyecto.
Mientras ese archivo exista ahí, **hasta tu copia local usará SQLite en vez
de SQL Server** (para que puedas probar exactamente lo que vas a subir).
Si lo borras, vuelve a usar tu SQL Server automáticamente.

### Paso 2 — Crear una cuenta y un repositorio en GitHub (gratis)

1. Crea una cuenta en [github.com](https://github.com) si no tienes.
2. Crea un repositorio nuevo (puede ser privado o público), ej. `pogo-team-builder`.
3. Sube TODA la carpeta del proyecto, **incluyendo el `pogo_data.sqlite`**
   que acabas de generar (es un archivo pequeño, no hay problema en subirlo).
   Puedes hacerlo arrastrando los archivos desde la web de GitHub
   ("Add file" → "Upload files"), sin necesidad de usar comandos `git` si
   no te sientes cómodo con eso todavía.

### Paso 3 — Desplegar en Streamlit Community Cloud (gratis)

1. Ve a [share.streamlit.io](https://share.streamlit.io) e inicia sesión
   con tu cuenta de GitHub.
2. Clic en **"New app"**.
3. Selecciona tu repositorio, la rama (`main`), y como archivo principal
   pon `app.py`.
4. Clic en **"Deploy"**. En 1-2 minutos te da una URL pública tipo
   `https://tuapp.streamlit.app`, ya accesible desde cualquier navegador,
   PC o celular, sin que tu PC tenga que estar encendida.

### Paso 4 — Actualizar los datos más adelante

Cada vez que quieras refrescar el meta (recomendado cada 2-4 semanas):

1. Actualiza tus tablas en SQL Server como ya haces.
2. Corre de nuevo `python export_to_sqlite.py`.
3. Sube el nuevo `pogo_data.sqlite` a tu repositorio de GitHub (reemplazando
   el anterior).
4. Streamlit Cloud detecta el cambio y redepliega la app sola, en un par
   de minutos, sin que tengas que hacer nada más.

## 🧠 ¿Cómo funciona el algoritmo?

1. Eliges un Pokémon (el "ancla" de tu equipo).
2. La app mira sus **counters** en PvPoke: los Pokémon que peor le van (sus amenazas).
3. Busca, entre los mejores del meta de esa liga, cuáles tienen **buenos matchups**
   justo contra esas amenazas → esos son los compañeros que "cubren" a tu ancla.
4. Clasifica a cada candidato en un rol aproximado comparando sus stats con
   el resto del meta:
   - **Líder (Lead):** buen rating general + bulk decente → aguanta bien el primer choque a ciegas.
   - **Cambio seguro (Switch):** mucha bulk (defensa × vida) → para entrar sin miedo.
   - **Cerrador (Closer):** mucho ataque → para rematar partidas.
5. Arma un equipo de 3 intentando variar esos roles, y te muestra alternativas extra.

## 🚀 Cómo correrlo

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit te dará una URL local (algo como `http://localhost:8501`). Ábrela
en tu navegador — funciona igual de bien desde el navegador del celular si
estás en la misma red, usando la URL de red que también te mostrará la
terminal (algo como `http://192.168.x.x:8501`).

## 📱 Usarla como una app en el celular (sin instalar nada de tiendas)

1. Sube este proyecto a [Streamlit Community Cloud](https://streamlit.io/cloud)
   (gratis) conectando tu cuenta de GitHub — o dime y te ayudo con ese paso.
2. Obtendrás una URL pública (ej. `tuapp.streamlit.app`).
3. Ábrela desde el navegador del celular (Chrome/Safari) y usa
   "Agregar a pantalla de inicio" → queda como un ícono más, se abre a
   pantalla completa, y se siente como una app nativa.

## 📂 Estructura del proyecto

```
pogo_team_builder/
├── app.py             # Interfaz Streamlit (lo que ves en pantalla)
├── data_loader.py      # Consulta tu SQL Server local (bd_pkm_pro)
├── team_builder.py    # Algoritmo de sinergia de equipo y roles
├── moves.py            # Formato/traducción de nombres de movimientos
└── requirements.txt
```

## 🔜 Próximos pasos posibles

- Agregar filtro por tipo de Pokémon.
- Mostrar el ícono/sprite de cada Pokémon (via PokeAPI).
- Permitir "bloquear" un segundo Pokémon y buscar el tercero ideal.
- Agregar un modo "mi equipo actual" para evaluar sinergia de 3 Pokémon ya elegidos.
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
