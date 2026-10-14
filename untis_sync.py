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
  res = session.get(init_url)
  data = res.json()
  elements = data.get("data", {}).get("elements", [])
  for el in elements:
    name = el.get("name", "")
    display_name = el.get("displayname", "")
    if (
        TARGET_NAME.lower() in name.lower()
        or TARGET_NAME.lower() in display_name.lower()
    ):
      print(f"Gefunden: {name} (ID: {el.get('id')})")
      return el.get("id")
  raise ValueError(
      f"Studiengang mit '{TARGET_NAME}' in WebUntis nicht gefunden!"
  )


def fetch_timetable(class_id, date_str):
  url = f"{BASE_URL}/api/public/timetable/weekly/data"
  params = {
      "elementType": 1,
      "elementId": class_id,
      "date": date_str,
      "formatId": 1,
  }
  res = session.get(url, params=params)
  return res.json()


def parse_untis_time(date_int, time_int):
  d_str = str(date_int)
  year, month, day = int(d_str[:4]), int(d_str[4:6]), int(d_str[6:])
  t_str = str(time_int).zfill(4)
  hour, minute = int(t_str[:2]), int(t_str[2:])
  return datetime.datetime(year, month, day, hour, minute)


def build_calendar(class_id, weeks_ahead=16):
  cal = Calendar()
  cal.add("prodid", "-//HS Albstadt DPM_1 AutoSync//DE")
  cal.add("version", "2.0")

  today = datetime.date.today()

  for w in range(weeks_ahead):
    current_date = today + datetime.timedelta(weeks=w)
    date_str = current_date.strftime("%Y-%m-%d")

    data = fetch_timetable(class_id, date_str)
    elements = (
        data.get("data", {})
        .get("result", {})
        .get("data", {})
        .get("elementPeriods", {})
    )

    periods = elements.get(str(class_id), [])
    for p in periods:
      event = Event()
      elements_list = p.get("elements", [])

      # Sauberes Auslesen ohne NoneType-Fehler
      subjects = [
          e.get("name") or e.get("displayname") or ""
          for e in elements_list
          if e.get("type") == 3
      ]
      rooms = [
          e.get("name") or e.get("displayname") or ""
          for e in elements_list
          if e.get("type") == 4
      ]
      teachers = [
          e.get("name") or e.get("displayname") or ""
          for e in elements_list
          if e.get("type") == 2
      ]

      subject = ", ".join([s for s in subjects if s])
      room = ", ".join([r for r in rooms if r])
      teacher = ", ".join([t for t in teachers if t])

      start_dt = parse_untis_time(p.get("date"), p.get("startTime"))
      end_dt = parse_untis_time(p.get("date"), p.get("endTime"))

      title = subject if subject else "Vorlesung"
      if p.get("is", {}).get("cancelled"):
        title = f"[AUSFALL] {title}"

      summary_text = f"{title} ({room})" if room else title
      event.add("summary", summary_text)
      event.add("dtstart", start_dt)
      event.add("dtend", end_dt)
      if room:
        event.add("location", room)
      event.add(
          "description",
          f"Dozent: {teacher}\nStatus: {p.get('activityType', 'Vorlesung')}",
      )
      cal.add_component(event)

  with open("dpm_1_stundenplan.ics", "wb") as f:
    f.write(cal.to_ical())
  print("FERTIG! 'dpm_1_stundenplan.ics' wurde erfolgreich erstellt.")


if __name__ == "__main__":
  cid = get_class_id()
  build_calendar(cid, weeks_ahead=16)