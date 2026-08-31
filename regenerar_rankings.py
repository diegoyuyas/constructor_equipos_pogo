"""
regenerar_rankings.py - Regenera la tabla Rankings después de cambiar Moves / Pokemon.

Flujo:
1. Guarda snapshot actual de Rankings en Rankings_Historico (para bitácora)
2. Lee Moves, Pokemon, PokemonFastMoves, PokemonChargedMoves actualizados
3. Para cada liga (500,1500,2500,10000):
   - Filtra Pokémon que pueden entrar (IVs óptimos dentro del CP)
   - Para cada Pokémon, busca el mejor moveset (todas las combinaciones fast x charged)
   - Hace todos vs todos con battle_engine.py y calcula winRate y score
   - Actualiza tabla Rankings

Uso:
    python regenerar_rankings.py --league 1500 --top 200
    python regenerar_rankings.py --league all --top 400 --cup all

Requisitos:
    pip install -r requirements-local.txt
    SQL Server corriendo

Nota de performance (importante para principiante):
- Top 200 = ~20k combates = 2-5 minutos
- Top 400 = ~80k combates = 8-15 minutos
- Todos (800+) = ~320k combates = 1-2 horas

Por defecto usa Top 200 para que puedas probar rápido.
"""

import argparse
import time
import itertools
from datetime import datetime
from pathlib import Path

import pandas as pd

from data_loader import get_connection, _is_sqlite_conn, load_pokemon_df, load_moves_df, get_moves_dict
from battle_engine import find_optimal_iv_for_cp, create_battle_pokemon_from_db, simulate_battle, calculate_cp
from custom_cup import filter_eligible_pokemon, CupRules  # reutilizamos filtro

# Para log bonito
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def backup_rankings_to_historico(conn, motivo="regeneracion automatica"):
    """Guarda snapshot actual de Rankings en Rankings_Historico"""
    log(f"Guardando backup de Rankings en Rankings_Historico... motivo: {motivo}")
    try:
        if _is_sqlite_conn(conn):
            conn.execute("""
                INSERT INTO Rankings_Historico (fecha, motivo, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail)
                SELECT datetime('now'), ?, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail
                FROM Rankings
            """, (motivo,))
            conn.commit()
        else:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO Rankings_Historico (fecha, motivo, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail)
                SELECT GETDATE(), ?, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail
                FROM Rankings
            """, motivo)
            conn.commit()
        log("Backup OK")
    except Exception as e:
        log(f"ADVERTENCIA: No se pudo hacer backup historico (tabla puede no existir aun): {e}")
        # Crear tabla si no existe (SQLite fallback simple)
        if _is_sqlite_conn(conn):
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS Rankings_Historico (
                        historicoId INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                        motivo TEXT,
                        league INTEGER,
                        cup TEXT,
                        category TEXT,
                        rank INTEGER,
                        pokemonId TEXT,
                        score REAL,
                        bestFastMove TEXT,
                        bestChargedMove1 TEXT,
                        bestChargedMove2 TEXT,
                        scoreDetail TEXT
                    )
                """)
                conn.commit()
                # Reintentar
                conn.execute("""
                    INSERT INTO Rankings_Historico (fecha, motivo, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail)
                    SELECT datetime('now'), ?, league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail
                    FROM Rankings
                """, (motivo,))
                conn.commit()
                log("Backup OK tras crear tabla")
            except Exception as e2:
                log(f"Error backup segundo intento: {e2}")

def load_pokemon_moves_map(conn):
    """Carga diccionario pokemonId -> {fast:[moveIds], charged:[moveIds]}
    Si no existen las tablas PokemonFastMoves/ChargedMoves (caso de sqlite viejo),
    hace fallback usando la tabla Rankings (best moves) o avisa cómo arreglarlo.
    """
    log("Cargando mapa de movimientos por Pokémon...")
    moves_map = {}

    try:
        if _is_sqlite_conn(conn):
            fast_df = pd.read_sql_query("SELECT pokemonId, moveId FROM PokemonFastMoves", conn)
            charged_df = pd.read_sql_query("SELECT pokemonId, moveId FROM PokemonChargedMoves", conn)
        else:
            fast_df = pd.read_sql("SELECT pokemonId, moveId FROM PokemonFastMoves", conn)
            charged_df = pd.read_sql("SELECT pokemonId, moveId FROM PokemonChargedMoves", conn)

        for _, row in fast_df.iterrows():
            pid = row["pokemonId"]
            if pid not in moves_map:
                moves_map[pid] = {"fast": [], "charged": []}
            moves_map[pid]["fast"].append(row["moveId"])

        for _, row in charged_df.iterrows():
            pid = row["pokemonId"]
            if pid not in moves_map:
                moves_map[pid] = {"fast": [], "charged": []}
            moves_map[pid]["charged"].append(row["moveId"])

        log(f"Mapa cargado desde tablas N:M: {len(moves_map)} Pokémon con movimientos")
        return moves_map

    except Exception as e:
        log(f"ADVERTENCIA: No se encontraron tablas PokemonFastMoves/ChargedMoves: {e}")
        log("Intentando fallback: usar best moves de la tabla Rankings...")

        # Fallback: usar Rankings para armar mapa
        try:
            if _is_sqlite_conn(conn):
                rank_df = pd.read_sql_query("SELECT pokemonId, bestFastMove, bestChargedMove1, bestChargedMove2 FROM Rankings GROUP BY pokemonId", conn)
            else:
                rank_df = pd.read_sql("SELECT pokemonId, bestFastMove, bestChargedMove1, bestChargedMove2 FROM Rankings GROUP BY pokemonId, bestFastMove, bestChargedMove1, bestChargedMove2", conn)

            for _, row in rank_df.iterrows():
                pid = row["pokemonId"]
                if pid not in moves_map:
                    moves_map[pid] = {"fast": [], "charged": []}
                if row["bestFastMove"] and row["bestFastMove"] not in moves_map[pid]["fast"]:
                    moves_map[pid]["fast"].append(row["bestFastMove"])
                for c in [row["bestChargedMove1"], row["bestChargedMove2"]]:
                    if c and c not in moves_map[pid]["charged"]:
                        moves_map[pid]["charged"].append(c)

            if moves_map:
                log(f"Fallback OK: mapa creado desde Rankings con {len(moves_map)} Pokémon")
                log("RECOMENDACION: Para tener todos los movimientos posibles (no solo los mejores),")
                log("  1. Borra o renombra pogo_data.sqlite para forzar conexion a SQL Server")
                log("  2. Verifica que en SQL Server existan PokemonFastMoves y PokemonChargedMoves")
                log("  3. Ejecuta python export_to_sqlite.py para regenerar el sqlite completo")
                return moves_map
            else:
                raise ValueError("Rankings vacio, no se puede hacer fallback")

        except Exception as e2:
            log(f"ERROR CRITICO: No hay tablas N:M y tampoco se pudo usar Rankings: {e2}")
            log("")
            log("SOLUCION RAPIDA:")
            log("  1. Si estas usando pogo_data.sqlite, borralo o renombralo a backup:")
            log("     ren pogo_data.sqlite pogo_data_old.sqlite")
            log("  2. Asegurate que SQL Server LOCALHOST\\SQLEXPRESS tenga las tablas PokemonFastMoves y PokemonChargedMoves")
            log("     En SSMS: SELECT COUNT(*) FROM PokemonFastMoves")
            log("  3. Si no existen, ejecuta tu script de poblado original de PvPoke")
            log("  4. Luego ejecuta: python export_to_sqlite.py")
            log("  5. Vuelve a ejecutar: python regenerar_rankings.py --league 1500 --top 200")
            raise

def find_best_moveset_for_pokemon(pokemon_row, moves_dict, moves_map, cp_cap, top_opponents_battle_pokes, max_combos_to_test=30):
    """
    Encuentra el mejor moveset para un Pokémon probando combinaciones.
    Para no probar 100 combos contra 200 oponentes (muy lento), hacemos 2 fases:
    Fase A: probar todos los combos contra 10 oponentes muestra para sacar top 3 combos
    Fase B: probar top 3 combos contra todos los oponentes muestra (top_opponents) y elegir ganador

    Retorna (fast_row, [charged1_row, charged2_row], winRate)
    """
    pid = pokemon_row["pokemonId"]
    if pid not in moves_map:
        return None, [], 0

    fast_ids = moves_map[pid]["fast"]
    charged_ids = moves_map[pid]["charged"]

    if not fast_ids or not charged_ids:
        return None, [], 0

    # Generar todas las combinaciones posibles: 1 fast + 2 charged (sin repetir)
    # Si tiene muchos charged, limitar a 2 primeros para performance inicial
    # Para ser exhaustivo: probar fast x (combinaciones de 2 charged de lista)
    combos = []
    for fast_id in fast_ids:
        # Combinaciones de 2 cargados
        for c1, c2 in itertools.combinations(charged_ids, 2):
            combos.append((fast_id, c1, c2))
        # También 1 solo cargado si solo tiene 1
        if len(charged_ids) == 1:
            combos.append((fast_ids[0], charged_ids[0], None))

    # Si hay demasiados combos, limitar a primeros N (los más meta normalmente vienen primero)
    if len(combos) > max_combos_to_test:
        combos = combos[:max_combos_to_test]

    if not combos:
        return None, [], 0

    # Fase A: probar contra 10 oponentes aleatorios del top para filtrar
    sample_opponents = top_opponents_battle_pokes[:10] if len(top_opponents_battle_pokes) >= 10 else top_opponents_battle_pokes

    best_combo = None
    best_winrate = -1

    # Para cada combo, crear BattlePokemon y simular vs sample
    iv_config = find_optimal_iv_for_cp(
        base_atk=int(pokemon_row["baseAtk"]),
        base_def=int(pokemon_row["baseDef"]),
        base_sta=int(pokemon_row["baseSta"]),
        cp_cap=cp_cap
    )

    for fast_id, c1_id, c2_id in combos:
        fast_row = moves_dict.get(str(fast_id).upper())
        c1_row = moves_dict.get(str(c1_id).upper()) if c1_id else None
        c2_row = moves_dict.get(str(c2_id).upper()) if c2_id else None

        if not fast_row or not c1_row:
            continue

        charged_rows = [r for r in [c1_row, c2_row] if r]

        try:
            bp = create_battle_pokemon_from_db(
                pokemon_row=pokemon_row.to_dict(),
                fast_move_row=fast_row,
                charged_move_rows=charged_rows,
                iv_config=iv_config
            )
        except Exception:
            continue

        wins = 0
        total = 0
        for opp in sample_opponents:
            if opp.pokemonId == bp.pokemonId:
                continue
            try:
                res = simulate_battle(bp, opp, shields_per_pokemon=1)
                if res.winner == bp.pokemonId:
                    wins += 1
                elif res.winner == "draw":
                    wins += 0.5
                total += 1
            except Exception:
                pass

        winrate = wins / max(1, total)
        if winrate > best_winrate:
            best_winrate = winrate
            best_combo = (fast_row, charged_rows, winrate, iv_config)

    if best_combo:
        return best_combo[0], best_combo[1], best_combo[2], best_combo[3]

    # Fallback: primer combo
    fast_id, c1_id, c2_id = combos[0]
    fast_row = moves_dict.get(str(fast_id).upper())
    c1_row = moves_dict.get(str(c1_id).upper()) if c1_id else None
    c2_row = moves_dict.get(str(c2_id).upper()) if c2_id else None
    charged_rows = [r for r in [c1_row, c2_row] if r]
    return fast_row, charged_rows, 0, iv_config

def regenerate_for_league(conn, league_cp, top_n, cup="all", category="overall"):
    log(f"=== Regenerando liga {league_cp} (Top {top_n}) ===")

    # Cargar datos frescos
    pokemon_df = load_pokemon_df()
    moves_dict = get_moves_dict()
    moves_map = load_pokemon_moves_map(conn)

    # Filtrar elegibles: todos los que pueden entrar en CP cap (sin filtro de tipos)
    # Usamos CupRules sin restricciones
    rules = CupRules(allowed_types=[], allow_shadow=False, banned_pokemon_ids=[], cp_cap=league_cp)
    eligible_df = filter_eligible_pokemon(pokemon_df, rules)
    log(f"Elegibles totales para CP {league_cp}: {len(eligible_df)}")

    # Si top_n, quedarnos con los mejores por base stat product o por ranking previo si existe
    # Para no hacer 800 vs 800, limitamos a top_n por score previo si existe, si no por stat product
    try:
        if _is_sqlite_conn(conn):
            prev_rank = pd.read_sql_query("SELECT pokemonId, score FROM Rankings WHERE league=? AND cup=? AND category=? ORDER BY score DESC", conn, params=(league_cp, cup, category))
        else:
            prev_rank = pd.read_sql(f"SELECT TOP {top_n*2} pokemonId, score FROM Rankings WHERE league={league_cp} AND cup='{cup}' AND category='{category}' ORDER BY score DESC", conn)

        if not prev_rank.empty:
            keep_ids = prev_rank.head(top_n)["pokemonId"].tolist()
            eligible_df = eligible_df[eligible_df["pokemonId"].isin(keep_ids)]
            log(f"Limitado a Top {top_n} por ranking previo: quedan {len(eligible_df)}")
        else:
            # Fallback por producto de stats
            eligible_df["statProduct"] = eligible_df["baseAtk"] * eligible_df["baseDef"] * eligible_df["baseSta"]
            eligible_df = eligible_df.sort_values(by="statProduct", ascending=False).head(top_n)
    except Exception as e:
        log(f"No hay ranking previo, usando stat product: {e}")
        eligible_df["statProduct"] = eligible_df["baseAtk"] * eligible_df["baseDef"] * eligible_df["baseSta"]
        eligible_df = eligible_df.sort_values(by="statProduct", ascending=False).head(top_n)

    # Crear BattlePokemons con mejor moveset encontrado (2 fases)
    battle_pokes = []
    log(f"Buscando mejor moveset para {len(eligible_df)} Pokémon (esto tarda)...")

    # Primero crear una lista de oponentes dummy para la fase de búsqueda de moveset (usaremos los primeros 20 como muestra)
    # Para no hacer doble loop, primero creamos battle pokes con moves por defecto, luego refinamos
    # Simplificación: crear battle pokes con primer moveset, usarlos como muestra
    temp_battle_pokes = []
    for _, prow in eligible_df.iterrows():
        pid = prow["pokemonId"]
        if pid not in moves_map:
            continue
        fast_ids = moves_map[pid]["fast"]
        charged_ids = moves_map[pid]["charged"]
        if not fast_ids or not charged_ids:
            continue
        iv_config = find_optimal_iv_for_cp(int(prow["baseAtk"]), int(prow["baseDef"]), int(prow["baseSta"]), cp_cap=league_cp)
        fast_row = moves_dict.get(str(fast_ids[0]).upper())
        c_rows = [moves_dict.get(str(cid).upper()) for cid in charged_ids[:2] if moves_dict.get(str(cid).upper())]
        if not fast_row or not c_rows:
            continue
        try:
            bp = create_battle_pokemon_from_db(prow.to_dict(), fast_row, c_rows, iv_config)
            temp_battle_pokes.append(bp)
        except Exception:
            pass

    # Ahora para cada Pokémon, encontrar su mejor moveset vs esa muestra
    for idx, (_, prow) in enumerate(eligible_df.iterrows()):
        if idx % 20 == 0:
            log(f"  Moveset {idx}/{len(eligible_df)}: {prow['name']}")

        fast_row, charged_rows, winrate, iv_config = find_best_moveset_for_pokemon(
            pokemon_row=prow,
            moves_dict=moves_dict,
            moves_map=moves_map,
            cp_cap=league_cp,
            top_opponents_battle_pokes=temp_battle_pokes,
            max_combos_to_test=20
        )

        if not fast_row:
            continue

        try:
            bp = create_battle_pokemon_from_db(prow.to_dict(), fast_row, charged_rows, iv_config)
            # Guardar info extra para luego guardar en Rankings
            bp._bestFast = fast_row["moveId"]
            bp._bestCharged1 = charged_rows[0]["moveId"] if len(charged_rows) > 0 else None
            bp._bestCharged2 = charged_rows[1]["moveId"] if len(charged_rows) > 1 else None
            bp._iv_config = iv_config
            battle_pokes.append(bp)
        except Exception as e:
            log(f"    Error creando {prow['pokemonId']}: {e}")

    log(f"BattlePokemons finales: {len(battle_pokes)}")

    # Round robin todos vs todos
    log(f"Iniciando round robin {len(battle_pokes)} x {len(battle_pokes)-1} / 2 combates...")
    n = len(battle_pokes)
    stats = {bp.pokemonId: {"wins":0, "losses":0, "draws":0, "hp_sum":0, "bp":bp} for bp in battle_pokes}

    total_battles = n*(n-1)//2
    battle_count = 0
    start_time = time.time()

    for i in range(n):
        for j in range(i+1, n):
            battle_count += 1
            if battle_count % 500 == 0:
                elapsed = time.time() - start_time
                log(f"  Combates {battle_count}/{total_battles} ({battle_count/total_battles*100:.1f}%) - {elapsed/60:.1f} min")

            p1 = battle_pokes[i]
            p2 = battle_pokes[j]
            try:
                res = simulate_battle(p1, p2, shields_per_pokemon=1)
                if res.winner == p1.pokemonId:
                    stats[p1.pokemonId]["wins"] += 1
                    stats[p2.pokemonId]["losses"] += 1
                    stats[p1.pokemonId]["hp_sum"] += res.p1_hp_percent
                elif res.winner == p2.pokemonId:
                    stats[p2.pokemonId]["wins"] += 1
                    stats[p1.pokemonId]["losses"] += 1
                    stats[p2.pokemonId]["hp_sum"] += res.p2_hp_percent
                else:
                    stats[p1.pokemonId]["draws"] += 1
                    stats[p2.pokemonId]["draws"] += 1
            except Exception:
                stats[p1.pokemonId]["draws"] += 1
                stats[p2.pokemonId]["draws"] += 1

    # Calcular score final
    rows = []
    for pid, s in stats.items():
        bp = s["bp"]
        total = s["wins"]+s["losses"]+s["draws"]
        winrate = (s["wins"] + 0.5*s["draws"])/max(1,total)
        avg_hp = s["hp_sum"]/max(1,s["wins"]) if s["wins"]>0 else 0
        score = winrate*1000 + avg_hp*20

        rows.append({
            "league": league_cp,
            "cup": cup,
            "category": category,
            "pokemonId": pid,
            "score": score,
            "bestFastMove": getattr(bp, "_bestFast", bp.fastMove.moveId if bp.fastMove else None),
            "bestChargedMove1": getattr(bp, "_bestCharged1", bp.chargedMoves[0].moveId if len(bp.chargedMoves)>0 else None),
            "bestChargedMove2": getattr(bp, "_bestCharged2", bp.chargedMoves[1].moveId if len(bp.chargedMoves)>1 else None),
            "scoreDetail": None,  # Podríamos guardar JSON con wins/losses, pero por ahora None
            "winRate": winrate,
            "wins": s["wins"],
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(by="score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    log(f"Ranking generado: {len(df)} filas. Top 5:")
    for _, r in df.head(5).iterrows():
        log(f"  #{r['rank']} {r['pokemonId']} score={r['score']:.0f} winRate={r['winRate']*100:.1f}%")

    return df

def update_rankings_table(conn, new_ranking_df, league_cp, cup="all", category="overall"):
    log(f"Actualizando tabla Rankings para liga {league_cp}...")

    if _is_sqlite_conn(conn):
        # Borrar viejos de esa liga/cup/category
        conn.execute("DELETE FROM Rankings WHERE league=? AND cup=? AND category=?", (league_cp, cup, category))
        conn.commit()

        # Insertar nuevos
        for _, row in new_ranking_df.iterrows():
            conn.execute("""
                INSERT INTO Rankings (league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["league"]), row["cup"], row["category"], int(row["rank"]), row["pokemonId"],
                float(row["score"]), row["bestFastMove"], row["bestChargedMove1"], row["bestChargedMove2"], row["scoreDetail"]
            ))
        conn.commit()
    else:
        cur = conn.cursor()
        cur.execute("DELETE FROM Rankings WHERE league=? AND cup=? AND category=?", (league_cp, cup, category))
        conn.commit()
        for _, row in new_ranking_df.iterrows():
            cur.execute("""
                INSERT INTO Rankings (league, cup, category, rank, pokemonId, score, bestFastMove, bestChargedMove1, bestChargedMove2, scoreDetail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["league"]), row["cup"], row["category"], int(row["rank"]), row["pokemonId"],
                float(row["score"]), row["bestFastMove"], row["bestChargedMove1"], row["bestChargedMove2"], row["scoreDetail"]
            ))
        conn.commit()

    log(f"Tabla Rankings actualizada para liga {league_cp}")

def main():
    parser = argparse.ArgumentParser(description="Regenera Rankings tras cambiar Moves/Pokemon")
    parser.add_argument("--league", type=str, default="1500", help="1500,2500,10000,500 o all")
    parser.add_argument("--top", type=int, default=200, help="Top N Pokémon a incluir (200 rapido, 400 completo)")
    parser.add_argument("--cup", type=str, default="all", help="Nombre de copa (all por defecto)")
    parser.add_argument("--category", type=str, default="overall", help="overall, leads, etc.")
    args = parser.parse_args()

    leagues = []
    if args.league == "all":
        leagues = [500, 1500, 2500, 10000]
    else:
        leagues = [int(args.league)]

    log(f"Iniciando regeneración para ligas: {leagues}, Top {args.top}")

    # Conexión
    try:
        from data_loader import get_connection
        conn, db_type = get_connection()
        log(f"Conectado a {db_type}")
    except Exception as e:
        log(f"ERROR conexión BD: {e}")
        return

    try:
        # 1. Backup
        backup_rankings_to_historico(conn, motivo=f"antes de regenerar ligas {leagues} top {args.top}")

        # 2. Para cada liga
        for league_cp in leagues:
            new_df = regenerate_for_league(conn, league_cp, top_n=args.top, cup=args.cup, category=args.category)
            update_rankings_table(conn, new_df, league_cp, cup=args.cup, category=args.category)

        log("¡Todas las ligas regeneradas con éxito!")

        # 3. Exportar a SQLite si estás en SQL Server para que puedas subir a la nube
        if db_type == "sqlserver":
            log("Estás en SQL Server, recuerda ejecutar export_to_sqlite.py y hacer push para actualizar la nube")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
