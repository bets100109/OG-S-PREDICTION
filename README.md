# Football Predictor (API-Football-ready)

This package contains a Streamlit app that predicts football matches using your custom formula
and can fetch live data from **API-Football** (api-sports). The app reads the API key from Streamlit Secrets
or the environment variable `FOOTBALL_API_KEY`.

**Files included**
- main.py             : Streamlit app (API + manual fallback)
- requirements.txt    : Python dependencies
- README.md           : This file
- .streamlit/secrets.toml.example : Example secrets file (DO NOT add your real key here if public)

## Quick instructions
1. Extract the zip and push to GitHub or upload to Streamlit Cloud (https://share.streamlit.io/).
2. On Streamlit Cloud, go to **Settings → Secrets** and add:
   - `FOOTBALL_API_KEY` = <your-api-football-key>
3. Deploy the app. If you don't add a key, the app still runs in **manual input** mode.

## Notes
- The code uses API-Football v3 endpoints with header `x-apisports-key`.
- You will not share your API key in this repo; add it as a secret on Streamlit Cloud.
