import datetime
import requests
from icalendar import Calendar, Event

SCHOOL = "hs-albstadt"
BASE_URL = f"https://{SCHOOL}.webuntis.com/WebUntis"
TARGET_NAME = "DPM_1"

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ),
    "Accept": "application/json",
})


def get_class_id():
  init_url = f"{BASE_URL}/api/public/timetable/weekly/pageconfig?type=1"
  res = session.get(init_url).json()
  elements = res.get("data", {}).get("elements", [])
  for el in elements:
    name = el.get("name", "")
    display_name = el.get("displayname", "")
    if (
        TARGET_NAME.lower() in name.lower()
        or TARGET_NAME.lower() in display_name.lower()
    ):
      print(f"Gefunden: {name} (ID: {el.get('id')})")
      return el.get("id")
  raise ValueError(f"Klasse {TARGET_NAME} nicht gefunden!")


def parse_untis_time(date_int, time_int):
  d_str = str(date_int)
  year, month, day = int(d_str[:4]), int(d_str[4:6]), int(d_str[6:])
  t_str = str(time_int).zfill(4)
  hour, minute = int(t_str[:2]), int(t_str[2:])
  return datetime.datetime(year, month, day, hour, minute)


def build_calendar(class_id, weeks_ahead=12):
  cal = Calendar()
  cal.add("prodid", "-//HS Albstadt DPM_1 AutoSync//DE")
  cal.add("version", "2.0")

  today = datetime.date.today()

  for w in range(weeks_ahead):
    current_date = today + datetime.timedelta(weeks=w)
    url = f"{BASE_URL}/api/public/timetable/weekly/data"
    params = {
        "elementType": 1,
        "elementId": class_id,
        "date": current_date.strftime("%Y-%m-%d"),
        "formatId": 1,
    }
    data = session.get(url, params=params).json()

    result = data.get("data", {}).get("result", {}).get("data", {})

    # Element-Lookup bauen (ID -> Name, Typ)
    element_map = {}
    for elem_list in result.get("elements", []):
      elem_id = elem_list.get("id")
      elem_name = (
          elem_list.get("displayname")
          or elem_list.get("name")
          or elem_list.get("longName")
      )
      elem_type = elem_list.get("type")  # 3 = Fach, 4 = Raum, 2 = Dozent
      if elem_id:
        element_map[elem_id] = (elem_name, elem_type)

    periods = result.get("elementPeriods", {}).get(str(class_id), [])
    for p in periods:
      event = Event()
      subjects, rooms, teachers = [], [], []

      for e in p.get("elements", []):
        eid = e.get("id")
        name = e.get("name") or e.get("displayname")
        etype = e.get("type")

        # Fallback auf Lookup-Map falls Name leer
        if not name and eid in element_map:
          name, etype = element_map[eid]

        if name:
          if etype == 3:
            subjects.append(name)
          elif etype == 4:
            rooms.append(name)
          elif etype == 2:
            teachers.append(name)

      fach = ", ".join(dict.fromkeys(subjects)) or "Vorlesung"
      raum = ", ".join(dict.fromkeys(rooms))
      dozent = ", ".join(dict.fromkeys(teachers))

      is_cancelled = p.get("is", {}).get("cancelled", False)
      title = f"[AUSFALL] {fach}" if is_cancelled else fach
      if raum:
        title += f" ({raum})"

      start_dt = parse_untis_time(p.get("date"), p.get("startTime"))
      end_dt = parse_untis_time(p.get("date"), p.get("endTime"))

      event.add("summary", title)
      event.add("dtstart", start_dt)
      event.add("dtend", end_dt)
      if raum:
        event.add("location", raum)
      event.add(
          "description",
          f"Fach: {fach}\nRaum: {raum}\nDozent: {dozent}\nStatus:"
          f" {p.get('activityType', 'Vorlesung')}",
      )
      cal.add_component(event)

  with open("dpm_1_stundenplan.ics", "wb") as f:
    f.write(cal.to_ical())
  print("Erfolgreich generiert mit Fächern und Räumen!")


if __name__ == "__main__":
  cid = get_class_id()
  build_calendar(cid, weeks_ahead=12)
