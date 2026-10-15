import os
import requests
from datetime import datetime, timedelta
from icalendar import Calendar, Event

# ==============================================================================
# HIER DEINE ORIGINAL UNTIS/SPLAN URL EINTRAGEN (falls nicht als Secret hinterlegt)
# ==============================================================================
UNTIS_ICS_URL = os.environ.get("UNTIS_ICS_URL", "DEINE_ORIGINAL_UNTIS_URL_HIER")
OUTPUT_FILE = "dpm_1_stundenplan.ics"

def fix_calendar():
    print("Lade Kalender herunter...")
    url = UNTIS_ICS_URL.replace("webcal://", "https://")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    cal = Calendar.from_ical(response.content)
    fixed_cal = Calendar()

    for key, value in cal.items():
        if key not in ["BEGIN", "END"]:
            fixed_cal.add(key, value)

    count_fixed = 0

    for component in cal.walk():
        if component.name == "VEVENT":
            event = component
            dtstart = event.get("dtstart")
            dtend = event.get("dtend")

            if dtstart and dtend:
                s = dtstart.dt
                e = dtend.dt

                if isinstance(s, datetime):
                    # KORREKTUR 1: Alles was zwischen 11:30 und 11:45 beginnt und bis 13:15 geht -> auf 11:30 - 13:00 setzen!
                    if (s.hour == 11 and s.minute in [30, 45]) and (e.hour == 13 and e.minute == 15):
                        event["dtstart"].dt = s.replace(hour=11, minute=30)
                        event["dtend"].dt = e.replace(hour=13, minute=0)
                        count_fixed += 1

                    # KORREKTUR 2: Falls der Block davor 10:00 - 11:30 war, aber eigentlich 09:45 - 11:15 sein soll:
                    elif s.hour == 10 and s.minute == 0 and e.hour == 11 and e.minute == 30:
                        event["dtstart"].dt = s.replace(hour=9, minute=45)
                        event["dtend"].dt = e.replace(hour=11, minute=15)
                        count_fixed += 1

                    # KORREKTUR 3: Falls ein Block nur mit Start 11:45 eingetragen war, auf 11:30 - 13:00 rücken
                    elif s.hour == 11 and s.minute == 45:
                        event["dtstart"].dt = s.replace(hour=11, minute=30)
                        event["dtend"].dt = e.replace(hour=13, minute=0)
                        count_fixed += 1

            fixed_cal.add_component(event)
        elif component.name not in ["VCALENDAR"]:
            fixed_cal.add_component(component)

    with open(OUTPUT_FILE, "wb") as f:
        f.write(fixed_cal.to_ical())

    print(f"Erfolgreich! {count_fixed} Termine korrigiert.")

if __name__ == "__main__":
    fix_calendar()
