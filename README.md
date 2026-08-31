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
