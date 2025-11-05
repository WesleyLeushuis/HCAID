def get_form_fields(mode:str):
    # Minimal: genoeg om voorspelling te maken (Good). In Bad voegen we onnodige velden toe.
    base = {
        "leeftijd": {"label": "Leeftijd", "type": "number", "min":18, "max":80},
        "inkomen": {"label": "Maandelijks netto inkomen (€)", "type": "number", "min":0},
        "spaardoel": {"label": "Spaardoel (€, kort/middel)", "type": "number", "min":0},
        "horizon_maanden": {"label": "Beleggingshorizon (maanden)", "type": "number", "min":1, "max":120},
        "risico_houding": {"label": "Risico-houding (0=laag,1=middel,2=hoog)", "type": "number", "min":0, "max":2},
        "ervaring": {"label": "Ervaring met beleggen (0/1)", "type": "number", "min":0, "max":1},
        "buffer_maanden": {"label": "Financiële buffer (maanden vaste lasten)", "type": "number", "min":0, "max":24}
    }
    if mode == "bad":
        base.update({
            "bsn": {"label":"BSN (onnodig)", "type":"text"},
            "telefoon": {"label":"Telefoonnummer (dwingend)", "type":"text"},
            "marketing_toestemming": {"label":"Marketing toestemming (vooraf aangevinkt)", "type":"checkbox", "checked": True},
        })
    return base
