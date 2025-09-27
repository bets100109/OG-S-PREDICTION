    import os, math, time, requests
    import streamlit as st
    import numpy as np
    import pandas as pd

    st.set_page_config(page_title="Football Predictor (API)", layout="centered")
    st.title("⚽ Football Predictor — API-Football Ready")
    st.write("This app fetches team data from API-Football (api-sports) if you supply a key in Streamlit Secrets. Otherwise use manual input.")

    # Read API key from Streamlit secrets or environment variable
    def get_api_key():
        # streamlit secrets accessible via st.secrets in Streamlit Cloud
        try:
            key = st.secrets["FOOTBALL_API_KEY"]
            if key:
                return key
        except Exception:
            pass
        # fallback to environment variable
        return os.environ.get("FOOTBALL_API_KEY", "")

    API_KEY = get_api_key()
    API_HOST = "https://v3.football.api-sports.io"
    HEADERS = {"x-apisports-key": API_KEY} if API_KEY else {}

    st.sidebar.markdown("""**Setup / Info**

- Add your API key in Streamlit Secrets as `FOOTBALL_API_KEY` for auto-fetch.
- If no key is present the app will run with **manual input** only.
""")

    # Utility: search teams by name (api)
    def search_teams(query, country=None):
        if not API_KEY:
            return []
        params = {"search": query}
        if country:
            params["country"] = country
        url = f"{API_HOST}/teams"
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json().get("response", [])
        teams = []
        for item in data:
            team = item.get("team") or item.get("venue") or {}
            teams.append({
                "id": item.get("team", {}).get("id"),
                "name": item.get("team", {}).get("name"),
                "country": item.get("team", {}).get("country")
            })
        return teams

    # Fetch last N fixtures for a team
    def fetch_last_fixtures(team_id, last=5):
        if not API_KEY:
            return []
        url = f"{API_HOST}/fixtures"
        params = {"team": team_id, "last": last}
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if r.status_code != 200:
            return []
        resp = r.json().get("response", [])
        fixtures = []
        for f in resp:
            score = f.get("score", {})
            full = score.get("fulltime") or score.get("halftime") or {}
            home = f.get("teams", {}).get("home", {})
            away = f.get("teams", {}).get("away", {})
            fixtures.append({
                "fixture_id": f.get("fixture", {}).get("id"),
                "date": f.get("fixture", {}).get("date"),
                "home_team": home.get("name"),
                "away_team": away.get("name"),
                "goals_home": score.get("fulltime", {}).get("home"),
                "goals_away": score.get("fulltime", {}).get("away"),
                "status": f.get("fixture", {}).get("status", {}).get("short")
            })
        return fixtures

    # Fetch head-to-head (H2H)
    def fetch_h2h(team_a, team_b, last=6):
        if not API_KEY:
            return []
        url = f"{API_HOST}/fixtures/headtohead"
        params = {"h2h": f"{team_a}-{team_b}", "last": last}
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if r.status_code != 200:
            return []
        resp = r.json().get("response", [])
        return resp

    # Simple rating extraction: estimate attack/defense from recent goals for/against per match
    def estimate_ratings_from_fixtures(fixtures, team_name):
        # compute goals scored and conceded
        gf = 0
        ga = 0
        played = 0
        for f in fixtures:
            if f.get("goals_home") is None or f.get("goals_away") is None:
                continue
            played += 1
            if f["home_team"] == team_name:
                gf += f["goals_home"]
                ga += f["goals_away"]
            else:
                gf += f["goals_away"]
                ga += f["goals_home"]
        if played == 0:
            return 1.5, 1.5
        avg_scored = gf / played
        avg_conceded = ga / played
        # attack rating higher if scoring more than average, defense rating lower if conceding less
        attack_rating = round(max(0.3, avg_scored), 2)
        defense_rating = round(max(0.3, avg_conceded), 2)
        return attack_rating, defense_rating

    # Prediction logic (your formula improved)
    def expected_goals_simple(team_attack, opp_defense, last5_form=None, missing_key=False, home=True):
        form_bonus = 0.1 * (sum(last5_form) if last5_form else 0)
        player_pen = -0.4 if missing_key else 0.0
        home_adv = 0.25 if home else 0.0
        base = 1.0 + (team_attack - opp_defense) * 0.7 + form_bonus + player_pen + home_adv
        return max(0.05, base)

    def simulate_poisson(lamA, lamB, n=500):
        import numpy as np
        scores = []
        for _ in range(n):
            a = np.random.poisson(lamA)
            b = np.random.poisson(lamB)
            scores.append((a,b))
        return scores

    def summarize_simulations(scores):
        from collections import Counter
        c = Counter()
        sc = Counter()
        for a,b in scores:
            sc[f"{a} - {b}"] += 1
            if a>b:
                c['home'] += 1
            elif a<b:
                c['away'] += 1
            else:
                c['draw'] += 1
        total = sum(c.values()) if sum(c.values())>0 else 1
        return c, sc, total

    # --- UI ---
    st.sidebar.header("Mode")
    mode = st.sidebar.selectbox("Mode", ["Manual input", "API search & predict (requires key)"])
    n_sim = st.sidebar.slider("Simulations", 200, 3000, 800, step=100)

    if mode == "Manual input":
        st.subheader("Manual input (no API key needed)")
        col1,col2 = st.columns(2)
        with col1:
            a_name = st.text_input("Team A name", "Team A")
            a_attack = st.number_input("Team A attack rating", 1.5, 0.1, 1.5)
            a_def = st.number_input("Team A defense rating", 1.2, 0.1, 1.2)
            a_last5 = st.text_input("Team A last5 (comma of 1/0/-1 e.g. 1,1,0,-1,1)", "1,1,0,-1,1")
            a_missing = st.checkbox("Team A missing key player")
        with col2:
            b_name = st.text_input("Team B name", "Team B")
            b_attack = st.number_input("Team B attack rating", 1.4, 0.1, 1.4)
            b_def = st.number_input("Team B defense rating", 1.3, 0.1, 1.3)
            b_last5 = st.text_input("Team B last5 (e.g. 0,1,0,-1,0)", "0,1,0,-1,0")
            b_missing = st.checkbox("Team B missing key player")
        if st.button("Predict"):
            # parse last5
            def parse_last5(s):
                try:
                    return [int(x.strip()) for x in str(s).split(",") if x.strip()!='']
                except:
                    return [0,0,0,0,0]
            la = parse_last5(a_last5)
            lb = parse_last5(b_last5)
            lamA = expected_goals_simple(a_attack, b_def, last5_form=la, missing_key=a_missing, home=True)
            lamB = expected_goals_simple(b_attack, a_def, last5_form=lb, missing_key=b_missing, home=False)
            scores = simulate_poisson(lamA, lamB, n=n_sim)
            c, sc, total = summarize_simulations(scores)
            st.metric("Predicted score (most likely)", sc.most_common(1)[0][0])
            st.write(f"Probabilities (%): {round(c['home']/total*100,1)}% | {round(c['draw']/total*100,1)}% | {round(c['away']/total*100,1)}%")
            top = sc.most_common(8)
            df = pd.DataFrame(top, columns=['Scoreline','Count'])
            df['Probability %'] = (df['Count']/n_sim*100).round(2)
            st.table(df)
    else:
        st.subheader("API search & predict")
        if not API_KEY:
            st.warning("No API key detected. Add FOOTBALL_API_KEY in Streamlit Secrets to enable API mode. Falling back to manual input.")
        st.write("Search for teams by name (API-Football). Example: 'Manchester United' or 'Real Madrid'.")
        q1 = st.text_input("Team A search", "")
        q2 = st.text_input("Team B search", "")
        season = st.text_input("Season (year) e.g. 2024", "2024")
        if st.button("Search & Predict"):
            if not API_KEY:
                st.error("No API key. Switch to Manual input or add the key in Streamlit Secrets.")
            else:
                ta = search_teams(q1)
                tb = search_teams(q2)
                if not ta or not tb:
                    st.error("Could not find teams. Try a different name or check your API key.")
                else:
                    # pick first matches
                    teamA = ta[0]
                    teamB = tb[0]
                    st.write(f"Selected: {teamA.get('name')}  VS  {teamB.get('name')}")
                    # fetch last fixtures (10) to estimate ratings and form
                    fa = fetch_last_fixtures(teamA['id'], last=10)
                    fb = fetch_last_fixtures(teamB['id'], last=10)
                    a_attack, a_def = estimate_ratings_from_fixtures(fa, teamA.get('name'))
                    b_attack, b_def = estimate_ratings_from_fixtures(fb, teamB.get('name'))
                    st.write(f"Estimated ratings — {teamA.get('name')}: attack={a_attack}, defense={a_def} | {teamB.get('name')}: attack={b_attack}, defense={b_def}")
                    # last5 form
                    def form_from_fixtures(fi, name):
                        arr = []
                        for f in fi[:5]:
                            if f.get('goals_home') is None or f.get('goals_away') is None:
                                continue
                            if f['home_team'] == name:
                                gf = f['goals_home']; ga = f['goals_away']
                            else:
                                gf = f['goals_away']; ga = f['goals_home']
                            if gf>ga: arr.append(1)
                            elif gf==ga: arr.append(0)
                            else: arr.append(-1)
                        return arr
                    la = form_from_fixtures(fa, teamA.get('name'))
                    lb = form_from_fixtures(fb, teamB.get('name'))
                    lamA = expected_goals_simple(a_attack, b_def, last5_form=la, missing_key=False, home=True)
                    lamB = expected_goals_simple(b_attack, a_def, last5_form=lb, missing_key=False, home=False)
                    scores = simulate_poisson(lamA, lamB, n=n_sim)
                    c, sc, total = summarize_simulations(scores)
                    st.metric("Most likely score", sc.most_common(1)[0][0])
                    st.write(f"Probabilities (%): Home {round(c['home']/total*100,1)}% | Draw {round(c['draw']/total*100,1)}% | Away {round(c['away']/total*100,1)}%")
                    top = sc.most_common(8)
                    df = pd.DataFrame(top, columns=['Scoreline','Count'])
                    df['Probability %'] = (df['Count']/n_sim*100).round(2)
                    st.table(df)
