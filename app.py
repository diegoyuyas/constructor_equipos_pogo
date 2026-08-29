"""
<<<<<<< HEAD
app.py - Interfaz principal Streamlit para Pokémon GO PvP Team Generator

Diseñada para ser usable desde el navegador del celular (Android/iPhone) sin instalar nada.

Features:
- Generador de equipos (core)
- Ranking filtrado por tipo
- Copas Personalizadas (Custom Cup Builder) - Fase 2 y 3

Para correr local:
    streamlit run app.py

Para desplegar:
    Sube a GitHub junto con pogo_data.sqlite, luego conecta en streamlit.io
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# Imports locales
from data_loader import (
    load_pokemon_df,
    load_moves_df,
    load_rankings,
    get_moves_dict,
    test_connection,
    is_sqlite_available,
    find_sqlite_file,
)
from moves import get_spanish_name, format_moveset_display
from team_builder import build_team, filter_ranking_by_type
from custom_cup import CupRules, generate_custom_cup_ranking

# Configuración de página (debe ser la primera llamada Streamlit)
st.set_page_config(
    page_title="PvP Team Generator - Pokémon GO",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS para mejorar visual en móvil
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stSelectbox, .stMultiSelect { font-size: 16px; } /* evita zoom en iPhone */
    .pokemon-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
        background: #fafafa;
    }
    .role-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 6px;
    }
    .role-Líder { background: #dbeafe; color: #1e40af; }
    .role-Switch { background: #dcfce7; color: #166534; }
    .role-Closer { background: #fee2e2; color: #991b1b; }
    .type-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 0.7rem;
        margin-right: 4px;
        background: #e5e7eb;
=======
app.py
------
Generador de Equipos PvP para Pokémon GO (Great / Ultra / Master League)

Cómo correrlo localmente:
    pip install -r requirements.txt
    streamlit run app.py

Luego abre la URL que te muestre (funciona igual en PC que en el navegador
del celular).

Fuente de datos: PvPoke (https://pvpoke.com), proyecto open-source, MIT License.
"""

import streamlit as st
from data_loader import LEAGUES, load_rankings, search_pokemon, get_pokemon_by_id
from team_builder import find_best_partners, build_suggested_team

st.set_page_config(
    page_title="Generador de Equipos PvP - Pokémon GO",
    page_icon="🛡️",
    layout="centered",
)

# ---------- Estilos rápidos ----------
st.markdown("""
<style>
    .role-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .role-lead { background-color: #FFE082; color: #7A5C00; }
    .role-switch { background-color: #A5D6A7; color: #1B5E20; }
    .role-closer { background-color: #EF9A9A; color: #7A0000; }
    .mon-card {
        border: 1px solid #333;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
        background-color: rgba(255,255,255,0.03);
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
    }
</style>
""", unsafe_allow_html=True)

<<<<<<< HEAD
# Cache de datos para no recargar en cada interacción
@st.cache_data(ttl=3600)
def cached_load_pokemon():
    return load_pokemon_df()

@st.cache_data(ttl=3600)
def cached_load_moves():
    return load_moves_df()

@st.cache_data(ttl=3600)
def cached_load_rankings(league, cup="all", category="overall"):
    return load_rankings(league, cup, category, limit=500)

@st.cache_data(ttl=3600)
def cached_moves_dict():
    return get_moves_dict()

def format_pokemon_label(pokemon_row):
    """Para selectbox: 'Pikachu (Eléctrico)'"""
    name = pokemon_row.get("name") or pokemon_row.get("pokemonId")
    t1 = pokemon_row.get("type1") or ""
    t2 = pokemon_row.get("type2")
    types = f"{t1}" + (f"/{t2}" if t2 and pd.notna(t2) else "")
    return f"{name} - {types}"

# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------
with st.sidebar:
    st.title("⚔️ PvP Team Gen")
    st.caption("Pokémon GO - Generador de equipos")

    # Test conexión
    ok, msg = test_connection()
    if ok:
        st.success(f"BD OK: {msg[:80]}...")
        if is_sqlite_available():
            st.info(f"SQLite: {find_sqlite_file().name}")
    else:
        st.error(f"Sin BD: {msg}")
        st.warning(
            "En local necesitas SQL Server LOCALHOST\\SQLEXPRESS con bd_pkm_pro. "
            "En la nube necesitas pogo_data.sqlite. "
            "Ejecuta export_to_sqlite.py en tu PC para generarlo."
        )

    st.divider()

    league_options = {
        "Great League (1500)": 1500,
        "Ultra League (2500)": 2500,
        "Master League (10000)": 10000,
        "Little Cup (500)": 500,
    }
    league_label = st.selectbox("Liga", list(league_options.keys()), index=0)
    league_value = league_options[league_label]

    st.divider()
    st.markdown("**¿Cómo usar?**")
    st.markdown(
        "1. Elige tu Pokémon ancla (tu favorito)\n"
        "2. Genera equipo\n"
        "3. Prueba el ranking por tipo y las copas custom"
    )

# ----------------------------------------------------------------------
# Cargar datos base
# ----------------------------------------------------------------------
try:
    pokemon_df = cached_load_pokemon()
    moves_df = cached_load_moves()
    moves_dict = cached_moves_dict()
    rankings_df = cached_load_rankings(league_value)
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

if pokemon_df.empty:
    st.error("Tabla Pokemon vacía. Verifica tu BD.")
    st.stop()

# ----------------------------------------------------------------------
# Tabs principales
# ----------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🧩 Generador de Equipos", "🔥 Ranking por Tipo", "🏆 Copas Personalizadas"])

# ---------------------- TAB 1: Generador ----------------------
with tab1:
    st.header(f"Generador de Equipos - {league_label}")
    st.caption("Elige un Pokémon ancla y te recomiendo 2 compañeros que cubren sus debilidades + alternativas.")

    # Selector de ancla: buscar por nombre
    # Crear lista ordenada por nombre
    pokemon_df_sorted = pokemon_df.sort_values(by="name").copy()
    # Filtrar solo los que están en el ranking actual para que el algoritmo funcione
    ranking_ids = set(rankings_df["pokemonId"].tolist())
    pokemon_in_rank = pokemon_df_sorted[pokemon_df_sorted["pokemonId"].isin(ranking_ids)]

    if pokemon_in_rank.empty:
        st.warning("No hay Pokémon del ranking en esta liga. Prueba otra liga.")
        anchor_options = pokemon_df_sorted
    else:
        anchor_options = pokemon_in_rank

    # Búsqueda con texto
    search_term = st.text_input("Buscar Pokémon ancla", placeholder="Ej: Azumarill, Skarmory, Medicham...")

    if search_term:
        filtered = anchor_options[anchor_options["name"].str.contains(search_term, case=False, na=False)]
    else:
        filtered = anchor_options.head(100)

    if filtered.empty:
        st.warning("No se encontró ningún Pokémon con ese nombre.")
        selected_pokemon_id = None
    else:
        # Selectbox con formato bonito
        options_dict = {f"{row['name']} ({row['pokemonId']})": row["pokemonId"] for _, row in filtered.iterrows()}
        selected_label = st.selectbox("Elige tu ancla", list(options_dict.keys()))
        selected_pokemon_id = options_dict[selected_label]

    col_btn1, col_btn2 = st.columns([1,2])
    with col_btn1:
        gen_btn = st.button("🚀 Generar Equipo", type="primary", use_container_width=True)
    with col_btn2:
        st.caption(f"Meta cargado: Top {len(rankings_df)} Pokémon de {league_label}")

    if gen_btn and selected_pokemon_id:
        with st.spinner("Analizando amenazas y sinergias..."):
            try:
                result = build_team(
                    anchor_id=selected_pokemon_id,
                    league=league_value,
                    rankings_df=rankings_df,
                    pokemon_df=pokemon_df,
                    moves_dict=moves_dict,
                    top_n_candidates=150,
                    num_alternatives=8,
                )
            except Exception as e:
                st.error(f"Error generando equipo: {e}")
                result = None

        if result:
            anchor = result["anchor"]
            threats = result["threats"]
            team = result["team"]
            alts = result["alternatives"]

            # Mostrar ancla
            st.subheader(f"Ancla: {anchor['name']}")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Rank", anchor.get("rank"))
            with c2:
                st.metric("Score", f"{anchor.get('score'):.1f}" if anchor.get("score") else "-")
            with c3:
                st.markdown(f"<span class='role-badge role-{anchor.get('role')}'>{anchor.get('role')}</span>", unsafe_allow_html=True)

            # Moves en español
            fast_es = get_spanish_name(anchor.get("bestFastMove"), moves_dict.get(str(anchor.get("bestFastMove")).upper(), {}).get("name"), moves_dict.get(str(anchor.get("bestFastMove")).upper(), {}).get("nameEs"))
            c1_es = get_spanish_name(anchor.get("bestChargedMove1"), moves_dict.get(str(anchor.get("bestChargedMove1")).upper(), {}).get("name"), moves_dict.get(str(anchor.get("bestChargedMove1")).upper(), {}).get("nameEs"))
            c2_es = get_spanish_name(anchor.get("bestChargedMove2"), moves_dict.get(str(anchor.get("bestChargedMove2")).upper(), {}).get("name"), moves_dict.get(str(anchor.get("bestChargedMove2")).upper(), {}).get("nameEs"))
            st.markdown(f"**Moves recomendados:** {fast_es} + {c1_es} / {c2_es}")

            st.markdown(f"**Amenazas a cubrir ({len(threats)}):** {', '.join(threats[:10])}")

            st.divider()
            st.subheader("✅ Equipo recomendado (Ancla + 2)")

            # Mostrar equipo
            for idx, member in enumerate(team, start=1):
                with st.container(border=True):
                    col_a, col_b = st.columns([2,1])
                    with col_a:
                        st.markdown(f"**{idx}. {member['name']}** <span class='role-badge role-{member['role']}'>{member['role']}</span> <span class='type-badge'>{member['type1']}</span>{'<span class=type-badge>'+member['type2']+'</span>' if member.get('type2') and pd.notna(member['type2']) else ''}", unsafe_allow_html=True)
                        # Moves
                        moves_display = format_moveset_display(
                            member.get("bestFastMove"),
                            [member.get("bestChargedMove1"), member.get("bestChargedMove2")],
                            moves_dict
                        )
                        st.caption(f"Moves: {moves_display}")
                    with col_b:
                        st.metric("Sinergia", f"{member['synergy']:.0f}")
                        st.caption(f"Cubre {member['covered']}/{len(threats)} amenazas")

            st.subheader("🔄 Alternativas")
            # Tabla de alternativas
            if alts:
                alt_data = []
                for a in alts:
                    moves_disp = format_moveset_display(a.get("bestFastMove"), [a.get("bestChargedMove1"), a.get("bestChargedMove2")], moves_dict)
                    alt_data.append({
                        "Pokémon": a["name"],
                        "Rol": a["role"],
                        "Cubre": f"{a['covered']}/{len(threats)}",
                        "Sinergia": int(a["synergy"]),
                        "Moves (ES)": moves_disp,
                        "Tipo": f"{a.get('type1')}/{a.get('type2')}" if a.get("type2") and pd.notna(a.get('type2')) else a.get("type1"),
                    })
                st.dataframe(pd.DataFrame(alt_data), use_container_width=True, hide_index=True)
            else:
                st.info("No hay alternativas adicionales.")

# ---------------------- TAB 2: Ranking por Tipo ----------------------
with tab2:
    st.header(f"Ranking filtrado por tipo - {league_label}")
    st.caption("Mismo enfoque que PvPoke.com: reutiliza el rating ya calculado contra el meta abierto.")

    all_types = ["NORMAL","FIRE","WATER","ELECTRIC","GRASS","ICE","FIGHTING","POISON","GROUND","FLYING","PSYCHIC","BUG","ROCK","GHOST","DRAGON","DARK","STEEL","FAIRY"]
    selected_types = st.multiselect("Filtra por tipo(s)", all_types, default=["FIRE"] if "FIRE" in all_types else [])

    limit = st.slider("Cuántos mostrar", 10, 200, 50)

    if st.button("Filtrar ranking"):
        with st.spinner("Filtrando..."):
            filtered_df = filter_ranking_by_type(rankings_df, pokemon_df, selected_types, limit=limit)

        if filtered_df.empty:
            st.warning("Ningún Pokémon coincide con ese filtro.")
        else:
            # Enriquecer con nombres en español de moves
            display_rows = []
            for _, row in filtered_df.iterrows():
                pid = row["pokemonId"]
                moves_disp = format_moveset_display(row.get("bestFastMove"), [row.get("bestChargedMove1"), row.get("bestChargedMove2")], moves_dict)
                display_rows.append({
                    "Rank": row.get("rank"),
                    "Pokémon": row.get("name") or pid,
                    "Score": f"{row.get('score'):.1f}" if row.get("score") else "-",
                    "Tipos": f"{row.get('type1')}/{row.get('type2')}" if row.get("type2") and pd.notna(row.get("type2")) else row.get("type1"),
                    "Moves (ES)": moves_disp,
                })
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

            st.download_button(
                "Descargar CSV",
                filtered_df.to_csv(index=False).encode("utf-8"),
                file_name=f"ranking_{'_'.join(selected_types)}_{league_value}.csv",
                mime="text/csv",
            )

# ---------------------- TAB 3: Copas Personalizadas ----------------------
with tab3:
    st.header("🏆 Copas Personalizadas (Custom Cup Builder)")
    st.markdown(
        """
        **¡Nueva feature en construcción!** Define tus propias reglas de copa y genera un ranking real
        simulando combates 1v1 entre todos los Pokémon elegibles.

        Esto es similar a la herramienta [Custom Rankings de PvPoke](https://pvpoke.com/custom-rankings/)
        pero simplificada para que corra en la nube gratis.
        """
    )

    st.info(
        "⚠️ **Nota de performance:** Para copas con >150 Pokémon elegibles, limitamos automáticamente a los 150 mejores "
        "por score del ranking estándar para que no se cuelgue Streamlit Cloud (gratis). "
        "Si tu copa es muy grande, considera filtrar más por tipos."
    )

    # Formulario de reglas
    with st.form("cup_rules_form"):
        st.subheader("Define tu copa")

        col1, col2 = st.columns(2)
        with col1:
            league_for_cup = st.selectbox(
                "Tope de CP (Liga)",
                [500, 1500, 2500, 10000],
                format_func=lambda x: {500:"Little Cup (500)",1500:"Great League (1500)",2500:"Ultra League (2500)",10000:"Master League (sin límite)"}[x],
                index=1,
            )
            allow_shadow = st.checkbox("Permitir Pokémon Shadow", value=False)
            exclude_sec_type = st.selectbox("Excluir tipo secundario (opcional)", ["(ninguno)"] + all_types, index=0)
            exclude_sec_type_val = None if exclude_sec_type == "(ninguno)" else exclude_sec_type

        with col2:
            allowed_types_cup = st.multiselect("Tipos permitidos (vacío = todos)", all_types, default=[])
            banned_input = st.text_area("Baneados (IDs separados por coma)", placeholder="Ej: venusaur, charizard, azumarill")
            use_optimal_moveset = st.checkbox("Buscar moveset óptimo para esta copa (más lento pero más preciso)", value=False)

        submitted = st.form_submit_button("🏁 Generar Ranking de Copa Custom", type="primary")

    if submitted:
        # Parsear baneados
        banned_list = []
        if banned_input and banned_input.strip():
            banned_list = [x.strip().lower() for x in banned_input.split(",") if x.strip()]

        rules = CupRules(
            allowed_types=allowed_types_cup,
            allow_shadow=allow_shadow,
            banned_pokemon_ids=banned_list,
            exclude_secondary_type=exclude_sec_type_val,
            cp_cap=league_for_cup,
            league_name={500:"Little Cup",1500:"Great League",2500:"Ultra League",10000:"Master League"}[league_for_cup],
        )

        st.write("Reglas:", rules.__dict__)

        # Cargar ranking correspondiente a ese CP cap para moves
        cup_rankings = cached_load_rankings(league_for_cup)

        # Barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(current, total, message):
            pct = int((current / max(1, total)) * 100)
            progress_bar.progress(min(100, pct))
            status_text.text(message)

        try:
            with st.spinner(f"Generando ranking custom para {rules.league_name}... Esto puede tomar 30-120 segundos..."):
                custom_ranking_df = generate_custom_cup_ranking(
                    pokemon_df=pokemon_df,
                    rankings_df=cup_rankings,
                    moves_dict=moves_dict,
                    rules=rules,
                    use_optimal_moveset=use_optimal_moveset,
                    progress_callback=progress_callback,
                )

            progress_bar.progress(100)
            status_text.text("¡Ranking completo!")

            st.success(f"Ranking generado: {len(custom_ranking_df)} Pokémon elegibles")

            # Mostrar resultado
            display_custom = []
            for _, row in custom_ranking_df.iterrows():
                moves_disp = f"{row.get('fastMove','')} + {', '.join(row.get('chargedMoves',[]))}"
                # Traducir a ES
                fast_es = get_spanish_name(row.get("fastMove"), moves_dict.get(str(row.get("fastMove")).upper(), {}).get("name"), moves_dict.get(str(row.get("fastMove")).upper(), {}).get("nameEs"))
                charged_es_list = []
                for cm in row.get("chargedMoves",[]):
                    ce = get_spanish_name(cm, moves_dict.get(str(cm).upper(), {}).get("name"), moves_dict.get(str(cm).upper(), {}).get("nameEs"))
                    charged_es_list.append(ce)
                moves_es_disp = f"{fast_es} + {' / '.join(charged_es_list)}"

                display_custom.append({
                    "Rank": row.get("rank"),
                    "Pokémon": row.get("name"),
                    "WinRate": f"{row.get('winRate',0)*100:.1f}%",
                    "Score": f"{row.get('score',0):.0f}",
                    "CP": row.get("cp"),
                    "Nivel": row.get("level"),
                    "IVs": f"{row.get('ivAtk')}/{row.get('ivDef')}/{row.get('ivSta')}",
                    "Moves (ES)": moves_es_disp,
                })

            st.dataframe(pd.DataFrame(display_custom), use_container_width=True, hide_index=True)

            st.download_button(
                "Descargar ranking custom CSV",
                custom_ranking_df.to_csv(index=False).encode("utf-8"),
                file_name=f"custom_cup_{league_for_cup}_{'_'.join(allowed_types_cup) if allowed_types_cup else 'all'}.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"Error generando copa custom: {e}")
            st.exception(e)

# Footer
st.divider()
st.caption(
    "Datos base de PvPoke (MIT License) + nombres oficiales en español vía PokeAPI (pokeapi.co). "
    "Motor de combate es aproximación, no réplica exacta de PvPoke. "
    "Hecho con ❤️ para la comunidad PvP de Pokémon GO."
=======
ROLE_CLASS = {
    "Líder (Lead)": "role-lead",
    "Cambio seguro (Switch)": "role-switch",
    "Cerrador (Closer)": "role-closer",
}


def role_badge(role: str) -> str:
    css_class = ROLE_CLASS.get(role, "role-switch")
    return f'<span class="role-badge {css_class}">{role}</span>'


def render_moveset(moveset: dict):
    st.markdown(f"**Movimiento rápido:** {moveset['fast']}")
    st.markdown(f"**Movimientos cargados:** {' + '.join(moveset['charged'])}")


def render_member_card(member, title_prefix=""):
    st.markdown(f"""
    <div class="mon-card">
        {role_badge(member.role)}
        <h4 style="margin:4px 0;">{title_prefix}{member.species_name}</h4>
        <p style="margin:2px 0; opacity:0.8;">Rating general: {member.rating:.0f}/1000 &nbsp;|&nbsp; Puntaje de sinergia: {member.synergy_score:.1f}</p>
    </div>
    """, unsafe_allow_html=True)
    render_moveset(member.moveset)
    if member.covers:
        st.caption(f"✅ Cubre bien a: {', '.join(member.covers)}")
    st.markdown("---")


# ---------- Encabezado ----------
st.title("🛡️ Generador de Equipos PvP")
st.caption("Great League · Ultra League · Master League — datos en vivo de PvPoke")

# ---------- Selector de liga ----------
league_key = st.radio(
    "Elige la liga:",
    options=list(LEAGUES.keys()),
    format_func=lambda k: LEAGUES[k]["name"],
    horizontal=True,
)

with st.spinner("Cargando el meta actual de PvPoke..."):
    try:
        rankings = load_rankings(league_key)
    except Exception as e:
        st.error(str(e))
        st.stop()

st.success(f"{len(rankings)} Pokémon cargados para {LEAGUES[league_key]['name']} (CP máx. {LEAGUES[league_key]['cp']})")

# ---------- Buscador de Pokémon ----------
st.subheader("1. Elige tu Pokémon base")
query = st.text_input("Busca un Pokémon (ej. 'Altaria', 'Azumarill'...)", "")

selected_id = None
if query:
    results = search_pokemon(rankings, query)
    if not results:
        st.warning("No se encontraron Pokémon con ese nombre en esta liga.")
    else:
        options = {f"{m['speciesName']}  (rating {m.get('rating', 0):.0f})": m["speciesId"] for m in results}
        chosen_label = st.selectbox("Resultados:", list(options.keys()))
        selected_id = options[chosen_label]

# ---------- Resultado ----------
if selected_id:
    anchor, partners = find_best_partners(rankings, selected_id, top_pool=60, num_results=8)

    if anchor is None:
        st.error("No se pudo encontrar ese Pokémon en los datos.")
    else:
        st.subheader("2. Tu Pokémon base")
        st.markdown(f"""
        <div class="mon-card">
            <h3 style="margin:4px 0;">⭐ {anchor['speciesName']}</h3>
            <p style="margin:2px 0; opacity:0.8;">Rating general: {anchor.get('rating', 0):.0f}/1000</p>
        </div>
        """, unsafe_allow_html=True)
        render_moveset(__import__("moves").format_moveset(anchor.get("moveset", [])))

        threats = [c["opponent"] for c in anchor.get("counters", [])]
        if threats:
            st.caption(f"⚠️ Sus principales amenazas (quién le gana): {', '.join(threats)}")

        st.markdown("---")

        team, alternatives = build_suggested_team(anchor, partners)

        st.subheader("3. Los 2 mejores compañeros para tu equipo")
        for slot in team[1:]:  # el slot 0 es el ancla, ya mostrada arriba
            render_member_card(slot["member"])

        if alternatives:
            st.subheader("4. Otras alternativas")
            st.caption("Buenas opciones adicionales, por si prefieres variar el equipo.")
            for alt in alternatives:
                render_member_card(alt)

        st.info(
            "💡 **Cómo se calculó esto:** primero identificamos qué Pokémon amenazan más a tu "
            "elección (columna 'counters' de PvPoke). Luego buscamos, entre los mejores del meta, "
            "cuáles tienen mejores enfrentamientos contra esas mismas amenazas — es decir, "
            "Pokémon que 'cubren' los puntos débiles de tu ancla. Los roles (Líder / Cambio seguro / "
            "Cerrador) se calculan comparando el rating general, la bulk (defensa × vida) y el ataque "
            "de cada Pokémon contra el resto del meta de esta liga."
        )
else:
    st.info("👆 Escribe el nombre de un Pokémon para empezar a armar tu equipo.")

st.markdown("---")
st.caption(
    "Datos de PvP cortesía de [PvPoke.com](https://pvpoke.com) (proyecto open-source, MIT License). "
    "Esta app no está afiliada a Niantic ni a The Pokémon Company."
>>>>>>> b43a432fc423e999abc1c8d5266343cd992574e1
)
