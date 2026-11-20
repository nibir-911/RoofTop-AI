# Rooftop Garden Planner (MVP demo)

Plan a rooftop garden from photos of the railing + side lengths. Supports a **two-level roof** (e.g. 5th floor + a 6th-floor
stair-house block in one corner, ~10 ft higher, with a small outer stair), a **marker tool** (brush / lasso / polygon / rectangle / circle)
to mark sun, shade, blocked and walkway zones on a 2 ft grid, sun-path based shade suggestions, three layout options, a bill of
materials and an interactive **3D impression** with a sun-time slider.

## Run on your Mac
```bash
cd garden_app_v2
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Click **Try the demo roof** in the sidebar for a one-minute tour (no photos needed).

## Host for the hackathon (Streamlit Community Cloud, free)
1. Put this folder in a GitHub repo (`app.py` at the top level; `requirements.txt` is already minimal).
2. Go to share.streamlit.io, sign in with GitHub, **New app**, pick the repo, main file `app.py`, Deploy.
3. Open the link and press **Try the demo roof** to check it works. Share that link with the reviewer.
4. Backup: record a 2-minute screen video of the demo flow in case Wi-Fi fails.
Alternative: `streamlit run app.py` locally and `cloudflared tunnel --url http://localhost:8501` for a temporary public link.

## Notes for the reviewer
- Privacy: photos stay in the browser session; nothing is stored on a server. *Save project* downloads a JSON.
- Plant data (`data/plants.csv`), prices (`data/materials.csv`) and load limits are **placeholders** needing agronomist /
  structural-engineer review. The 3D view is an illustrative impression, not an exact model.
- Upper-roof planting requires the outer stair; stair/door landings are kept clear automatically.
- Optional plant sprites: generate offline on a GPU machine (`tools/make_sprites.py`, see `data/sprites/README.txt`); the app works without them.

## Tests
`pip install -r requirements-dev.txt && python -m pytest -q tests`
