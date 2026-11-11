import json
from pathlib import Path
from app.delay_service import delay_codes


def test_fra_dictionary_complete():
    glossary=delay_codes()
    definitions=glossary["definitions"]
    assert len(definitions)==42
    assert all(len(k)==3 and len(v["label"])>3 and v["explanation"] for k,v in definitions.items())
    assert definitions["FTI"]["label"]=="Freight train interference"
    assert definitions["NOD"]["official_responsibility"]=="Third party"
    assert definitions["TCD"]["official_responsibility"]=="Host railroad"
    assert glossary["source_url"].startswith("https://railroads.fra.dot.gov/")

def test_glossary_embedded_in_delay_api():
    src=Path(__file__).parents[1]/"app/delay_service.py"
    assert "'delay_code_dictionary': delay_codes()" in src.read_text()
