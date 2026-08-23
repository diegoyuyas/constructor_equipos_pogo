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
