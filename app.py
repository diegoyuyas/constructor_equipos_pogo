"""
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
    }
</style>
""", unsafe_allow_html=True)

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
)
