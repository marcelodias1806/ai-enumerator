from pathlib import Path

def test_dashboard_assets_exist():
    root=Path(__file__).resolve().parents[1]/"app"/"static"
    assert (root/"dashboard.html").exists()
    assert (root/"dashboard.css").exists()
    assert (root/"dashboard.js").exists()

def test_dashboard_has_core_sections():
    html=(Path(__file__).resolve().parents[1]/"app"/"static"/"dashboard.html").read_text()
    for section in ["overview","vendors","users","unknown","events"]:
        assert f'id="{section}"' in html
