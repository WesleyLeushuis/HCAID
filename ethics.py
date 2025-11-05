class GoodUX:
    def collect(self, form:dict):
        # Minimal data collection; ignore any extra fields sent by client
        allowed = {"leeftijd","inkomen","spaardoel","horizon_maanden","risico_houding","ervaring","buffer_maanden"}
        filtered = {k:self._cast(v) for k,v in form.items() if k in allowed}
        return filtered

    def _cast(self, v):
        try:
            if v is None: return 0
            if v.strip()=="" : return 0
        except AttributeError:
            pass
        # naive cast to float then int where applicable
        try:
            fv = float(v)
            if fv.is_integer():
                return int(fv)
            return fv
        except Exception:
            return v

    def warnings(self, result, explanations):
        w = []
        # Transparant over onzekerheid (simpele melding)
        if result and 0.4 < result["proba_risk"] < 0.6:
            w.append("Let op: de inschatting is onzeker (grensgebied). Overweeg extra informatie.")
        return w

    def privacy_text(self):
        return (
            "Wij verzamelen uitsluitend de gegevens die nodig zijn voor een risicoberekening. "
            "Je gegevens blijven lokaal in deze demonstratie en kunnen worden gedownload of verwijderd."
        )

class BadUX:
    def collect(self, form:dict):
        # Overcollect & coerce; maak 'dark' keuzes (simulatie)
        return form  # sla alles op, inclusief BSN etc. (in de demo alleen in-memory)

    def warnings(self, result, _):
        # Geen uitleg, wel manipulatieve copy
        w = []
        if result and result["proba_risk"] < 0.7:
            w.append("Top! Je mist kansen als je nu niet instapt. Beperk aanbod, laatste plekken.")
        return w

    def privacy_text(self):
        return (
            "We verbeteren je ervaring door gegevens te delen met partners. "
            "Door verder te gaan ga je hiermee akkoord."
        )
