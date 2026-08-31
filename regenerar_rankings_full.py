# Copia este archivo como regenerar_rankings_full.py en tu carpeta constructor_equipos_pogo

"""
regenerar_rankings_full.py - Ranking 100% independiente estilo PvPoke
Batalla TODOS vs TODOS (800+ Pokemon) en 3 escenarios (0-0,1-1,2-2)
"""
import argparse, time, itertools, json
from datetime import datetime
import pandas as pd
from data_loader import get_connection, _is_sqlite_conn
from battle_engine import find_optimal_iv_for_cp, create_battle_pokemon_from_db, simulate_battle

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

def load_moves_map(conn):
    moves_map = {}
    if _is_sqlite_conn(conn):
        fast_df = pd.read_sql_query("SELECT pokemonId, moveId FROM PokemonFastMoves", conn)
        charged_df = pd.read_sql_query("SELECT pokemonId, moveId FROM PokemonChargedMoves", conn)
    else:
        fast_df = pd.read_sql("SELECT pokemonId, moveId FROM PokemonFastMoves", conn)
        charged_df = pd.read_sql("SELECT pokemonId, moveId FROM PokemonChargedMoves", conn)
    for _, r in fast_df.iterrows():
        moves_map.setdefault(r["pokemonId"], {"fast":[],"charged":[]})
        moves_map[r["pokemonId"]]["fast"].append(r["moveId"])
    for _, r in charged_df.iterrows():
        moves_map.setdefault(r["pokemonId"], {"fast":[],"charged":[]})
        moves_map[r["pokemonId"]]["charged"].append(r["moveId"])
    return moves_map

def find_best_moveset_for_meta(pokemon_row, moves_dict, moves_map, cp_cap, sample_opponents, max_combos=35):
    pid = pokemon_row["pokemonId"]
    if pid not in moves_map: return None, [], 0, None
    fast_ids = moves_map[pid]["fast"]
    charged_ids = moves_map[pid]["charged"]
    if not fast_ids or not charged_ids: return None, [], 0, None
    combos = []
    for fast_id in fast_ids:
        for c1, c2 in itertools.combinations(charged_ids, 2):
            combos.append((fast_id, c1, c2))
    if len(combos) > max_combos: combos = combos[:max_combos]
    iv_config = find_optimal_iv_for_cp(int(pokemon_row["baseAtk"]), int(pokemon_row["baseDef"]), int(pokemon_row["baseSta"]), cp_cap=cp_cap)
    best_combo = None
    best_score = -1
    for fast_id, c1_id, c2_id in combos:
        fast_row = moves_dict.get(str(fast_id).upper())
        c1_row = moves_dict.get(str(c1_id).upper())
        c2_row = moves_dict.get(str(c2_id).upper()) if c2_id else None
        if not fast_row or not c1_row: continue
        charged_rows = [r for r in [c1_row, c2_row] if r]
        try:
            bp = create_battle_pokemon_from_db(pokemon_row.to_dict(), fast_row, charged_rows, iv_config)
        except: continue
        wins = total = 0
        for opp in sample_opponents[:15]:
            if opp.pokemonId == bp.pokemonId: continue
            for shields in [0,1,2]:
                try:
                    res = simulate_battle(bp, opp, shields_per_pokemon=shields)
                    if res.winner == bp.pokemonId: wins += 1
                    elif res.winner == "draw": wins += 0.5
                    total += 1
                except: total += 1
        winrate = wins / max(1,total)
        if winrate > best_score:
            best_score = winrate
            best_combo = (fast_row, charged_rows, winrate, iv_config)
    if best_combo: return best_combo
    return None, [], 0, iv_config

def regenerate_full_meta(conn, league_cp, top_n="all", cup="all", category="overall"):
    from data_loader import load_pokemon_df, get_moves_dict
    log(f"=== FULL META LIGA {league_cp} TOP={top_n} ===")
    pokemon_df = load_pokemon_df()
    moves_dict = get_moves_dict()
    moves_map = load_moves_map(conn)
    eligible = []
    for _, row in pokemon_df.iterrows():
        if row["pokemonId"] not in moves_map: continue
        try:
            iv = find_optimal_iv_for_cp(int(row["baseAtk"]), int(row["baseDef"]), int(row["baseSta"]), cp_cap=league_cp)
            if iv["cp"] <= league_cp: eligible.append(row)
        except: continue
    eligible_df = pd.DataFrame(eligible)
    eligible_df["statProduct"] = eligible_df["baseAtk"] * eligible_df["baseDef"] * eligible_df["baseSta"]
    eligible_df = eligible_df.sort_values(by="statProduct", ascending=False)
    if str(top_n).lower()!= "all": eligible_df = eligible_df.head(int(top_n))
    log(f"Elegibles: {len(eligible_df)}")
    sample_df = eligible_df.head(30)
    sample_bps = []
    for _, r in sample_df.iterrows():
        pid = r["pokemonId"]
        if pid not in moves_map: continue
        fast_id = moves_map[pid]["fast"][0] if moves_map[pid]["fast"] else None
        charged_ids = moves_map[pid]["charged"][:2]
        if not fast_id or not charged_ids: continue
        fast_row = moves_dict.get(str(fast_id).upper())
        charged_rows = [moves_dict.get(str(cid).upper()) for cid in charged_ids if moves_dict.get(str(cid).upper())]
        if not fast_row or not charged_rows: continue
        iv = find_optimal_iv_for_cp(int(r["baseAtk"]), int(r["baseDef"]), int(r["baseSta"]), cp_cap=league_cp)
        try:
            bp = create_battle_pokemon_from_db(r.to_dict(), fast_row, charged_rows, iv)
            sample_bps.append(bp)
        except: continue
    battle_pokes = []
    for _, row in eligible_df.iterrows():
        fast_row, charged_rows, wr, iv_config = find_best_moveset_for_meta(row, moves_dict, moves_map, league_cp, sample_bps, max_combos=35)
        if not fast_row: continue
        try:
            bp = create_battle_pokemon_from_db(row.to_dict(), fast_row, charged_rows, iv_config)
            bp._bestFast = fast_row.get("moveId")
            bp._bestCharged1 = charged_rows[0].get("moveId") if len(charged_rows)>0 else None
            bp._bestCharged2 = charged_rows[1].get("moveId") if len(charged_rows)>1 else None
            battle_pokes.append(bp)
        except: continue
    log(f"BattlePokemons: {len(battle_pokes)}")
    n = len(battle_pokes)
    total_battles = n*(n-1)//2 * 3
    log(f"Round robin {n} x {n-1}/2 x3 = {total_battles} combates")
    stats = {bp.pokemonId: {"wins0":0,"losses0":0,"draws0":0,"wins1":0,"losses1":0,"draws1":0,"wins2":0,"losses2":0,"draws2":0,"hp_sum":0,"bp":bp} for bp in battle_pokes}
    battle_count = 0
    start = time.time()
    for i in range(n):
        for j in range(i+1, n):
            p1 = battle_pokes[i]; p2 = battle_pokes[j]
            for shields in [0,1,2]:
                battle_count += 1
                if battle_count % 1000 == 0:
                    elapsed = time.time() - start
                    log(f" {battle_count}/{total_battles} ({battle_count/total_battles*100:.1f}%) {elapsed/60:.1f}min")
                try:
                    res = simulate_battle(p1, p2, shields_per_pokemon=shields)
                    if res.winner == p1.pokemonId:
                        if shields==0: stats[p1.pokemonId]["wins0"]+=1; stats[p2.pokemonId]["losses0"]+=1
                        elif shields==1: stats[p1.pokemonId]["wins1"]+=1; stats[p2.pokemonId]["losses1"]+=1
                        else: stats[p1.pokemonId]["wins2"]+=1; stats[p2.pokemonId]["losses2"]+=1
                        stats[p1.pokemonId]["hp_sum"]+=res.p1_hp_percent
                    elif res.winner == p2.pokemonId:
                        if shields==0: stats[p2.pokemonId]["wins0"]+=1; stats[p1.pokemonId]["losses0"]+=1
                        elif shields==1: stats[p2.pokemonId]["wins1"]+=1; stats[p1.pokemonId]["losses1"]+=1
                        else: stats[p2.pokemonId]["wins2"]+=1; stats[p1.pokemonId]["losses2"]+=1
                        stats[p2.pokemonId]["hp_sum"]+=res.p2_hp_percent
                    else:
                        if shields==0: stats[p1.pokemonId]["draws0"]+=1; stats[p2.pokemonId]["draws0"]+=1
                        elif shields==1: stats[p1.pokemonId]["draws1"]+=1; stats[p2.pokemonId]["draws1"]+=1
                        else: stats[p1.pokemonId]["draws2"]+=1; stats[p2.pokemonId]["draws2"]+=1
                except:
                    if shields==0: stats[p1.pokemonId]["draws0"]+=1; stats[p2.pokemonId]["draws0"]+=1
                    elif shields==1: stats[p1.pokemonId]["draws1"]+=1; stats[p2.pokemonId]["draws1"]+=1
                    else: stats[p1.pokemonId]["draws2"]+=1; stats[p2.pokemonId]["draws2"]+=1
    rows = []
    for pid, s in stats.items():
        bp = s["bp"]
        total0 = s["wins0"]+s["losses0"]+s["draws0"]; total1 = s["wins1"]+s["losses1"]+s["draws1"]; total2 = s["wins2"]+s["losses2"]+s["draws2"]
        wr0 = (s["wins0"]+0.5*s["draws0"])/max(1,total0); wr1 = (s["wins1"]+0.5*s["draws1"])/max(1,total1); wr2 = (s["wins2"]+0.5*s["draws2"])/max(1,total2)
        weighted = wr0*0.3 + wr1*0.4 + wr2*0.3
        avg_hp = s["hp_sum"]/max(1,s["wins0"]+s["wins1"]+s["wins2"])
        score = weighted*1000 + avg_hp*50
        detail = {"wr0":round(wr0,4),"wr1":round(wr1,4),"wr2":round(wr2,4),"weighted":round(weighted,4)}
        rows.append({"league":league_cp,"cup":cup,"category":category,"pokemonId":pid,"score":score,"bestFastMove":getattr(bp,"_bestFast",None),"bestChargedMove1":getattr(bp,"_bestCharged1",None),"bestChargedMove2":getattr(bp,"_bestCharged2",None),"scoreDetail":json.dumps(detail),"winRate":weighted})
    df = pd.DataFrame(rows).sort_values(by="score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index+1
    return df

def update_rankings_table(conn, new_df, league_cp, cup="all", category="overall"):
    if _is_sqlite_conn(conn):
        conn.execute("DELETE FROM Rankings WHERE league=? AND cup=? AND category=?", (league_cp, cup, category))
        conn.commit()
        for _, row in new_df.iterrows():
            conn.execute("INSERT INTO Rankings (league,cup,category,rank,pokemonId,score,bestFastMove,bestChargedMove1,bestChargedMove2,scoreDetail) VALUES (?,?,?,?,?,?,?,?,?,?)", (int(row["league"]), row["cup"], row["category"], int(row["rank"]), row["pokemonId"], float(row["score"]), row["bestFastMove"], row["bestChargedMove1"], row["bestChargedMove2"], row["scoreDetail"]))
        conn.commit()
    else:
        cur = conn.cursor()
        cur.execute("DELETE FROM Rankings WHERE league=? AND cup=? AND category=?", (league_cp, cup, category))
        conn.commit()
        for _, row in new_df.iterrows():
            cur.execute("INSERT INTO Rankings (league,cup,category,rank,pokemonId,score,bestFastMove,bestChargedMove1,bestChargedMove2,scoreDetail) VALUES (?,?,?,?,?,?,?,?,?,?)", (int(row["league"]), row["cup"], row["category"], int(row["rank"]), row["pokemonId"], float(row["score"]), row["bestFastMove"], row["bestChargedMove1"], row["bestChargedMove2"], row["scoreDetail"]))
        conn.commit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", type=str, default="1500")
    parser.add_argument("--top", type=str, default="all")
    args = parser.parse_args()
    leagues = [500,1500,2500,10000] if args.league=="all" else [int(args.league)]
    conn, db_type = get_connection()
    for league_cp in leagues:
        new_df = regenerate_full_meta(conn, league_cp, top_n=args.top)
        update_rankings_table(conn, new_df, league_cp)
    conn.close()

if __name__ == "__main__":
    main()