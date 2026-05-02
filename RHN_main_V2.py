from datetime import datetime, date

import flet as ft
import flet_geolocator as ftg
import flet_map as ftm
import httpx
import mysql.connector


MSU_DOMAIN = "@montclair.edu"
GRAPH_HOPPER_API_KEY = "3e19284a-10f0-424f-9add-57bd72967758"

MSU_RED = "#C8102E"
WHITE = "#FFFFFF"
BLACK = "#111111"
LIGHT_BG = "#F5F5F5"
LIGHT_BORDER = "#E4E4E4"
LIGHT_INPUT = "#F3F3F3"
TEXT_MUTED = "#666666"
APP_SHELL = "#D9D9D9"
SOFT_GRAY = "#F0F0F0"

DEFAULT_CENTER = ftm.MapLatitudeLongitude(40.862147765671764, -74.1981587142951)
DEFAULT_ZOOM = 17
FOCUSED_ZOOM = 18.5


CAMPUS_LOCATIONS = {
    "cs building": {
        "label": "Center for Computing and Information Science",
        "coordinates": ftm.MapLatitudeLongitude(40.861983, -74.196905),
        "info": "Academic building with classrooms and faculty offices.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "center for computing and information science": {
        "label": "Center for Computing and Information Science",
        "coordinates": ftm.MapLatitudeLongitude(40.861983, -74.196905),
        "info": "Academic building with classrooms and faculty offices.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "ccis": {
        "label": "Center for Computing and Information Science",
        "coordinates": ftm.MapLatitudeLongitude(40.861983, -74.196905),
        "info": "Academic building with classrooms and faculty offices.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "student center": {
        "label": "Student Center",
        "coordinates": ftm.MapLatitudeLongitude(40.862775, -74.197206),
        "info": "Dining, study areas, student lounges, and events.",
        "hours": "8:00 AM - 10:00 PM",
    },
    "university hall": {
        "label": "University Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.862435, -74.199034),
        "info": "Administrative offices and classrooms.",
        "hours": "8:30 AM - 6:00 PM",
    },
    "dickson hall": {
        "label": "Dickson Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.861141, -74.199041),
        "info": "Lecture halls and academic departments.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "feliciano school of business": {
        "label": "Feliciano School of Business",
        "coordinates": ftm.MapLatitudeLongitude(40.861808, -74.199822),
        "info": "Business school classrooms, labs, and offices.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "schmitt hall": {
        "label": "Schmitt Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.861434, -74.197225),
        "info": "Classrooms and faculty offices.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "sprague library": {
        "label": "Sprague Library",
        "coordinates": ftm.MapLatitudeLongitude(40.860372, -74.198110),
        "info": "Main campus library with study spaces and resources.",
        "hours": "7:00 AM - 12:00 AM",
    },
    "richardson hall": {
        "label": "Richardson Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.862398, -74.196191),
        "info": "Academic building with classrooms and faculty offices.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "richardson": {
        "label": "Richardson Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.862398, -74.196191),
        "info": "Academic building with classrooms and faculty offices.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "finley hall": {
        "label": "Finley Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.860977, -74.197651),
        "info": "Lecture halls and classrooms.",
        "hours": "8:00 AM - 9:00 PM",
    },
    "red hawk diner": {
        "label": "Red Hawk Diner",
        "coordinates": ftm.MapLatitudeLongitude(40.862998, -74.199411),
        "info": "Popular campus dining location.",
        "hours": "7:00 AM - 10:00 PM",
    },
    "school of communication and media": {
        "label": "School of Communication and Media",
        "coordinates": ftm.MapLatitudeLongitude(40.860098, -74.197173),
        "info": "Media, communication, and production spaces.",
        "hours": "8:00 AM - 9:00 PM",
    },
}

DEMO_EVENTS = [
    {
        "title": "World's Fair Day",
        "location": "Student Center",
        "date": None,
        "time": "12:00:00",
        "description": "Campus celebration event.",
    },
    {
        "title": "Career Fair",
        "location": "University Hall",
        "date": "2028-04-07",
        "time": "01:54:00",
        "description": "Meet employers and explore opportunities.",
    },
    {
        "title": "Club Expo",
        "location": "Student Center",
        "date": "2024-04-07",
        "time": "01:54:00",
        "description": "Discover student organizations.",
    },
]

ALIAS_TO_LABEL = {}
LABEL_TO_PLACE = {}

for key, value in CAMPUS_LOCATIONS.items():
    label = value["label"]
    ALIAS_TO_LABEL[key.lower()] = label
    ALIAS_TO_LABEL[label.lower()] = label

for value in CAMPUS_LOCATIONS.values():
    label = value["label"]
    LABEL_TO_PLACE[label] = {
        "label": label,
        "coordinates": value["coordinates"],
        "info": value.get("info", "No information available."),
        "hours": value.get("hours", "Hours not available."),
        "source": "campus",
    }


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="MSU_Admin",
        password="MSU",
        database="red_hawk_navigation",
    )


def username_ok(value: str) -> bool:
    value = (value or "").strip().lower()
    return value.endswith(MSU_DOMAIN) and " " not in value and len(value) > len(MSU_DOMAIN)


def user_auth(username: str, password: str):
    username = (username or "").strip().lower()
    password = (password or "").strip()

    if not username_ok(username) or not password:
        return None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT email, password, role FROM user WHERE email = %s AND password = %s",
            (username, password),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return None

        role_value = user.get("role", 0)
        role_name = "Faculty" if int(role_value) == 1 else "Student"
        return {"email": user["email"], "role": role_name}
    except Exception:
        return {"email": username, "role": "Student"} if username_ok(username) and password else None


def get_events():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT eventID, title, location, date, time, description
            FROM event
            ORDER BY date ASC, time ASC, eventID DESC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception:
        return DEMO_EVENTS.copy()


def add_event(title, location, date_value, time_value, description, status="Pending"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO event (title, location, date, time, description, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (title, location, date_value, time_value, description, status),
    )
    conn.commit()
    cursor.close()
    conn.close()


async def get_route(start, end):
    params = {
        "point": [
            f"{start.latitude},{start.longitude}",
            f"{end.latitude},{end.longitude}",
        ],
        "profile": "foot",
        "locale": "en",
        "points_encoded": "false",
        "key": GRAPH_HOPPER_API_KEY,
        "calc_points": "true",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://graphhopper.com/api/1/route", params=params)
        response.raise_for_status()
        data = response.json()

    coords = data["paths"][0]["points"]["coordinates"]
    return [ftm.MapLatitudeLongitude(lat, lon) for lon, lat in coords]


async def geocode_location(query):
    q = (query or "").strip().lower()
    if not q:
        return None

    direct_label = ALIAS_TO_LABEL.get(q)
    if direct_label:
        return dict(LABEL_TO_PLACE[direct_label])

    for alias_key, label in ALIAS_TO_LABEL.items():
        if q in alias_key:
            return dict(LABEL_TO_PLACE[label])

    params = {
        "q": f"{query}, Montclair State University",
        "format": "jsonv2",
        "limit": 1,
    }
    headers = {"User-Agent": "red_hawk_navigator/1.0"}

    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        if not data:
            return None

        item = data[0]
        return {
            "label": item.get("display_name", query),
            "coordinates": ftm.MapLatitudeLongitude(float(item["lat"]), float(item["lon"])),
            "info": "Location found from search.",
            "hours": "Hours not available.",
            "source": "external",
        }
    except Exception:
        return None


def format_event_date(date_value):
    if isinstance(date_value, datetime):
        return date_value.strftime("%b %d, %Y")
    if date_value in (None, "", "None"):
        return "Date TBD"
    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return str(date_value)


def format_event_time(time_value):
    if time_value in (None, "", "None"):
        return "Time TBD"
    raw = str(time_value).split(".")[0]
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).strftime("%I:%M %p").lstrip("0")
        except Exception:
            continue
    return str(time_value)


def normalize_time(value):
    value = (value or "").strip()
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(value.upper(), fmt).strftime("%H:%M:%S")
        except ValueError:
            pass
    return None


def parse_event_date(date_value):
    if isinstance(date_value, datetime):
        return date_value.date()
    if date_value in (None, "", "None"):
        return None
    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d").date()
    except Exception:
        return None


async def main(page: ft.Page):
    page.title = "Red Hawk Navigator"
    page.padding = 0
    page.spacing = 0

    try:
        page.window_width = 390
        page.window_height = 844
        page.window_resizable = False
    except Exception:
        pass

    main_area = ft.Container(expand=True)

    current_user_email = ""
    current_user_role = ""
    current_view = "login"
    help_return_view = "login"

    is_dark_mode = False
    current_center = DEFAULT_CENTER
    current_zoom = DEFAULT_ZOOM
    map_refresh_token = 0

    user_location = None
    location_status = "Location not loaded yet."

    selected_place = None
    favorite_places = []
    route_points = []
    search_value = ""

    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    route_marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    polyline_layer_ref = ft.Ref[ftm.PolylineLayer]()

    search_field_ref = ft.Ref[ft.TextField]()
    suggestion_column_ref = ft.Ref[ft.Column]()
    suggestion_box_ref = ft.Ref[ft.Container]()
    place_card_ref = ft.Ref[ft.Container]()
    clear_search_button_ref = ft.Ref[ft.IconButton]()

    geo = ftg.Geolocator(
        configuration=ftg.GeolocatorConfiguration(
            accuracy=ftg.GeolocatorPositionAccuracy.BEST
        )
    )

    def colors():
        if is_dark_mode:
            return {
                "shell": BLACK,
                "page_bg": BLACK,
                "surface": "#161616",
                "card_bg": "#1A1A1A",
                "input_bg": "#191919",
                "border": "#2D2D2D",
                "text": WHITE,
                "subtext": "#CFCFCF",
                "soft_fill": "#202020",
                "profile_fill": "#211215",
                "fab_bg": "#1B1B1B",
            }
        return {
            "shell": APP_SHELL,
            "page_bg": WHITE,
            "surface": WHITE,
            "card_bg": WHITE,
            "input_bg": LIGHT_INPUT,
            "border": LIGHT_BORDER,
            "text": BLACK,
            "subtext": TEXT_MUTED,
            "soft_fill": SOFT_GRAY,
            "profile_fill": "#FFF6F7",
            "fab_bg": WHITE,
        }

    def show_snack(message):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=WHITE),
            bgcolor=BLACK,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        page.snack_bar.open = True
        page.update()

    def app_shell(content):
        c = colors()
        return ft.Container(
            expand=True,
            bgcolor=c["shell"],
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=390,
                height=844,
                bgcolor=c["page_bg"],
                border_radius=24,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=content,
            ),
        )

    def show_screen(content, view_name):
        nonlocal current_view
        current_view = view_name
        main_area.content = content
        page.update()

    def set_map_view(center, zoom=FOCUSED_ZOOM):
        nonlocal current_center, current_zoom, map_refresh_token
        current_center = ftm.MapLatitudeLongitude(center.latitude, center.longitude)
        current_zoom = zoom
        map_refresh_token += 1

    def get_suggestion_labels(query: str):
        q = (query or "").strip().lower()
        if not q:
            return []

        exact = []
        starts = []
        contains = []
        seen = set()

        def add_label(label, bucket):
            key = label.lower().strip()
            if key not in seen:
                seen.add(key)
                bucket.append(label.strip())

        for alias_key, label in ALIAS_TO_LABEL.items():
            if q == alias_key:
                add_label(label, exact)
            elif alias_key.startswith(q):
                add_label(label, starts)
            elif q in alias_key:
                add_label(label, contains)

        return (exact + starts + contains)[:6]

    def favorite_exists(label):
        return any(item["label"].lower() == label.lower() for item in favorite_places)

    def clear_route():
        nonlocal route_points
        route_points = []
        if polyline_layer_ref.current:
            polyline_layer_ref.current.polylines.clear()

    def clear_search_box():
        nonlocal search_value
        search_value = ""
        if search_field_ref.current:
            search_field_ref.current.value = ""
        if suggestion_box_ref.current:
            suggestion_box_ref.current.visible = False
        if suggestion_column_ref.current:
            suggestion_column_ref.current.controls.clear()
        if clear_search_button_ref.current:
            clear_search_button_ref.current.visible = False
        page.update()

    def close_place_card():
        nonlocal selected_place
        selected_place = None
        if place_card_ref.current:
            place_card_ref.current.visible = False
        refresh_map_layers()

    def refresh_map_layers():
        if marker_layer_ref.current is not None:
            marker_layer_ref.current.markers.clear()
            for place in LABEL_TO_PLACE.values():
                marker_layer_ref.current.markers.append(
                    ftm.Marker(
                        coordinates=place["coordinates"],
                        content=ft.Container(
                            width=16,
                            height=16,
                            border_radius=8,
                            bgcolor=MSU_RED,
                            border=ft.Border.all(2, WHITE if not is_dark_mode else BLACK),
                            ink=True,
                            on_click=lambda e, p=dict(place): page.run_task(select_place, p, False),
                        ),
                    )
                )

        if route_marker_layer_ref.current is not None:
            route_marker_layer_ref.current.markers.clear()

            if user_location is not None:
                route_marker_layer_ref.current.markers.append(
                    ftm.Marker(
                        coordinates=user_location,
                        content=ft.Icon(ft.Icons.MY_LOCATION, color="#1E88E5", size=28),
                    )
                )

            if selected_place is not None:
                route_marker_layer_ref.current.markers.append(
                    ftm.Marker(
                        coordinates=selected_place["coordinates"],
                        content=ft.Icon(ft.Icons.LOCATION_ON, color=MSU_RED, size=36),
                    )
                )

        if polyline_layer_ref.current is not None:
            polyline_layer_ref.current.polylines.clear()
            if route_points:
                polyline_layer_ref.current.polylines.append(
                    ftm.PolylineMarker(
                        coordinates=route_points,
                        color=MSU_RED,
                        stroke_width=5,
                    )
                )

        page.update()

    def build_header(title, subtitle=None, trailing=None, fill=None):
        c = colors()
        return ft.Container(
            bgcolor=fill if fill else c["surface"],
            padding=ft.Padding(20, 18, 20, 14),
            border=ft.Border.only(bottom=ft.BorderSide(1, c["border"])),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(
                                title,
                                size=24,
                                weight=ft.FontWeight.W_800,
                                color=c["text"],
                            ),
                            ft.Text(
                                subtitle or "",
                                size=12,
                                color=c["subtext"],
                            ),
                        ],
                    ),
                    trailing if trailing else ft.Container(width=1),
                ],
            ),
        )

    def nav_item(icon, label, selected, on_click):
        c = colors()
        active_color = MSU_RED if selected else c["text"]
        return ft.Container(
            expand=True,
            ink=True,
            on_click=on_click,
            padding=ft.Padding(8, 8, 8, 6),
            content=ft.Column(
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=24, color=active_color),
                    ft.Text(
                        label,
                        size=11,
                        weight=ft.FontWeight.W_700 if selected else ft.FontWeight.W_500,
                        color=active_color,
                    ),
                ],
            ),
        )

    def build_bottom_nav(active):
        c = colors()
        return ft.Container(
            bgcolor=c["surface"],
            border=ft.Border.only(top=ft.BorderSide(1, c["border"])),
            padding=ft.Padding(8, 4, 8, 10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    nav_item(ft.Icons.MAP_OUTLINED, "Map", active == "home", lambda e: show_home_page()),
                    nav_item(ft.Icons.CALENDAR_MONTH_OUTLINED, "Events", active == "events", lambda e: show_events_page()),
                    nav_item(ft.Icons.SETTINGS_OUTLINED, "Settings", active == "settings", lambda e: show_settings_page()),
                ],
            ),
        )

    async def load_user_location(show_feedback=False, recenter=False):
        nonlocal user_location, location_status
        pos = None

        try:
            permission = await geo.get_permission_status()
            if str(permission).lower() not in {"granted", "while_in_use", "always"}:
                await geo.request_permission(timeout=30)
        except Exception:
            pass

        try:
            pos = await geo.get_current_position(timeout=20)
        except Exception:
            pos = None

        if pos is None:
            try:
                pos = await geo.get_last_known_position()
            except Exception:
                pos = None

        if pos is None:
            location_status = "Could not get your current location."
            if show_feedback:
                show_snack(location_status)
            return

        user_location = ftm.MapLatitudeLongitude(pos.latitude, pos.longitude)
        location_status = "Location is active."

        if recenter:
            set_map_view(user_location, FOCUSED_ZOOM)
            show_home_page()
        else:
            refresh_map_layers()

        if show_feedback:
            show_snack("Current location loaded.")

    async def draw_route_to_selected_place():
        if selected_place is None:
            show_snack("Select a building first.")
            return

        if user_location is None:
            await load_user_location(show_feedback=False, recenter=False)

        if user_location is None:
            show_snack("Enable location to get directions.")
            return

        clear_route()

        try:
            new_points = await get_route(user_location, selected_place["coordinates"])
            nonlocal route_points
            route_points = new_points
            set_map_view(selected_place["coordinates"], FOCUSED_ZOOM)
            show_home_page()
            show_snack(f"Directions loaded to {selected_place['label']}.")
        except Exception as ex:
            show_snack(f"Could not load directions: {ex}")

    async def select_place(place, auto_route=False):
        nonlocal selected_place, search_value
        selected_place = dict(place)
        search_value = place["label"]

        if search_field_ref.current:
            search_field_ref.current.value = place["label"]
        if suggestion_box_ref.current:
            suggestion_box_ref.current.visible = False
        if suggestion_column_ref.current:
            suggestion_column_ref.current.controls.clear()
        if clear_search_button_ref.current:
            clear_search_button_ref.current.visible = True

        set_map_view(place["coordinates"], FOCUSED_ZOOM)
        update_place_card()
        refresh_map_layers()

        if auto_route:
            await draw_route_to_selectedPlace_fix()

    async def draw_route_to_selectedPlace_fix():
        await draw_route_to_selected_place()

    async def perform_search():
        query = (search_field_ref.current.value if search_field_ref.current else search_value or "").strip()
        if not query:
            show_snack("Enter a building or place to search.")
            return

        result = await geocode_location(query)
        if result is None:
            show_snack("Location not found.")
            return

        await select_place(result, False)

    async def route_to_event_location(event_location):
        result = await geocode_location(event_location)
        if result is None:
            show_snack("Could not find event location.")
            return
        await select_place(result, True)
        show_home_page()

    def update_search_suggestions(value: str):
        nonlocal search_value
        search_value = value

        matches = get_suggestion_labels(value)
        if suggestion_column_ref.current is None or suggestion_box_ref.current is None:
            return

        suggestion_column_ref.current.controls.clear()

        if clear_search_button_ref.current:
            clear_search_button_ref.current.visible = bool((value or "").strip())

        if not (value or "").strip():
            suggestion_box_ref.current.visible = False
            page.update()
            return

        if not matches:
            suggestion_column_ref.current.controls.append(
                ft.Container(
                    padding=ft.Padding(18, 12, 18, 12),
                    content=ft.Text(
                        "No results found",
                        size=13,
                        color=colors()["subtext"],
                    ),
                )
            )
            suggestion_box_ref.current.visible = True
            page.update()
            return

        for label in matches:
            suggestion_column_ref.current.controls.append(
                ft.TextButton(
                    content=ft.Text(
                        label,
                        size=14,
                        color=colors()["text"],
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    on_click=lambda e, name=label: page.run_task(select_place, dict(LABEL_TO_PLACE[name]), False),
                    style=ft.ButtonStyle(
                        alignment=ft.Alignment(-1, 0),
                        padding=ft.Padding(18, 12, 18, 12),
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                )
            )

        suggestion_box_ref.current.visible = True
        page.update()

    def toggle_favorite(place):
        nonlocal favorite_places
        if favorite_exists(place["label"]):
            favorite_places = [item for item in favorite_places if item["label"].lower() != place["label"].lower()]
            show_snack(f"Removed {place['label']} from favorites.")
        else:
            favorite_places.append(dict(place))
            show_snack(f"Added {place['label']} to favorites.")
        update_place_card()

    def update_place_card():
        if place_card_ref.current is None:
            return

        c = colors()

        if selected_place is None:
            place_card_ref.current.visible = False
            page.update()
            return

        is_fav = favorite_exists(selected_place["label"])

        place_card_ref.current.content = ft.Container(
            padding=16,
            border_radius=22,
            bgcolor=c["surface"],
            border=ft.Border.all(1, c["border"]),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Column(
                                expand=True,
                                spacing=6,
                                controls=[
                                    ft.Text(
                                        selected_place["label"],
                                        size=18,
                                        weight=ft.FontWeight.W_800,
                                        color=c["text"],
                                    ),
                                    ft.Text(
                                        selected_place.get("info", "No information available."),
                                        size=13,
                                        color=c["subtext"],
                                    ),
                                    ft.Text(
                                        f"Hours: {selected_place.get('hours', 'N/A')}",
                                        size=12,
                                        color=MSU_RED,
                                    ),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=c["text"],
                                on_click=lambda e: close_place_card(),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.FilledButton(
                                "Directions",
                                icon=ft.Icons.DIRECTIONS_WALK,
                                style=ft.ButtonStyle(
                                    bgcolor=MSU_RED,
                                    color=WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=16),
                                    padding=ft.Padding(16, 14, 16, 14),
                                ),
                                on_click=lambda e: page.run_task(draw_route_to_selected_place),
                            ),
                            ft.OutlinedButton(
                                "Favorite",
                                icon=ft.Icons.FAVORITE if is_fav else ft.Icons.FAVORITE_BORDER,
                                style=ft.ButtonStyle(
                                    color=MSU_RED,
                                    side=ft.BorderSide(1, MSU_RED),
                                    shape=ft.RoundedRectangleBorder(radius=16),
                                    padding=ft.Padding(16, 14, 16, 14),
                                ),
                                on_click=lambda e, p=dict(selected_place): toggle_favorite(p),
                            ),
                        ],
                    ),
                ],
            ),
        )
        place_card_ref.current.visible = True
        page.update()

    async def handle_map_tap(e: ftm.MapTapEvent):
        if e.name != "tap":
            return

        nearest_place = None
        nearest_score = 999.0

        for place in LABEL_TO_PLACE.values():
            dx = e.coordinates.latitude - place["coordinates"].latitude
            dy = e.coordinates.longitude - place["coordinates"].longitude
            score = (dx * dx + dy * dy) ** 0.5
            if score < nearest_score:
                nearest_score = score
                nearest_place = place

        if nearest_place is not None and nearest_score < 0.00055:
            await select_place(nearest_place, False)

    def build_map():
        return ftm.Map(
            key=f"map-{map_refresh_token}",
            expand=True,
            initial_center=current_center,
            initial_zoom=current_zoom,
            interaction_configuration=ftm.InteractionConfiguration(
                flags=ftm.InteractionFlag.ALL
            ),
            on_tap=handle_map_tap,
            layers=[
                ftm.TileLayer(
                    url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    user_agent_package_name="red_hawk_navigator",
                ),
                ftm.RichAttribution(
                    attributions=[
                        ftm.TextSourceAttribution(text="OpenStreetMap Contributors"),
                        ftm.TextSourceAttribution(text="GraphHopper"),
                        ftm.TextSourceAttribution(text="Flet"),
                    ]
                ),
                ftm.MarkerLayer(ref=marker_layer_ref, markers=[]),
                ftm.MarkerLayer(ref=route_marker_layer_ref, markers=[]),
                ftm.PolylineLayer(ref=polyline_layer_ref, polylines=[]),
            ],
        )

    def show_login():
        c = colors()

        email_field = ft.TextField(
            hint_text="Email address",
            prefix_icon=ft.Icons.MAIL_OUTLINE,
            border_radius=18,
            border_color="transparent",
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor=c["input_bg"],
            color=c["text"],
            text_size=15,
            height=56,
            content_padding=ft.Padding(16, 12, 16, 12),
        )

        password_field = ft.TextField(
            hint_text="Password",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            border_radius=18,
            border_color="transparent",
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor=c["input_bg"],
            color=c["text"],
            text_size=15,
            height=56,
            content_padding=ft.Padding(16, 12, 16, 12),
        )

        error_text = ft.Text("", size=12, color=MSU_RED, visible=False)

        def do_login(_):
            nonlocal current_user_email, current_user_role
            result = user_auth(email_field.value, password_field.value)

            if not result:
                error_text.value = "Invalid email or password."
                error_text.visible = True
                page.update()
                return

            current_user_email = result["email"]
            current_user_role = result["role"]
            error_text.visible = False

            clear_search_box()
            clear_route()
            show_home_page()
            page.run_task(load_user_location, False, False)

        login_card = ft.Container(
            padding=ft.Padding(26, 34, 26, 30),
            border_radius=30,
            bgcolor=c["surface"],
            border=ft.Border.all(1, c["border"]),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
                controls=[
                    ft.Text("MONTCLAIR", size=34, weight=ft.FontWeight.W_900, color=MSU_RED),
                    ft.Text("STATE UNIVERSITY", size=13, weight=ft.FontWeight.W_700, color=c["text"]),
                    ft.Container(height=4),
                    ft.Text("Red Hawk Navigator", size=25, weight=ft.FontWeight.W_800, color=c["text"]),
                    ft.Container(height=8),
                    email_field,
                    password_field,
                    error_text,
                    ft.FilledButton(
                        "Sign In",
                        width=320,
                        height=54,
                        style=ft.ButtonStyle(
                            bgcolor=MSU_RED,
                            color=WHITE,
                            shape=ft.RoundedRectangleBorder(radius=18),
                            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_700),
                        ),
                        on_click=do_login,
                    ),
                    ft.TextButton(
                        "Forgot username or password?",
                        on_click=lambda e: show_help_page("login"),
                        style=ft.ButtonStyle(
                            color=MSU_RED,
                            text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_600),
                        ),
                    ),
                ],
            ),
        )

        content = ft.Container(
            expand=True,
            bgcolor=LIGHT_BG if not is_dark_mode else BLACK,
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=390,
                height=844,
                padding=20,
                alignment=ft.Alignment(0, 0),
                content=login_card,
            ),
        )

        show_screen(content, "login")

    def show_help_page(return_view="login"):
        nonlocal help_return_view
        help_return_view = return_view
        c = colors()

        def go_back(_):
            if help_return_view == "settings" and current_user_email:
                show_settings_page()
            else:
                show_login()

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header("Account Help", "Montclair State University", fill=c["soft_fill"]),
                ft.Container(
                    expand=True,
                    padding=ft.Padding(28, 24, 24, 24),
                    content=ft.Column(
                        spacing=22,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Text(
                                "Forgot username or password?",
                                size=20,
                                weight=ft.FontWeight.W_800,
                                color=c["text"],
                            ),
                            ft.Text("Please contact:", size=14, color=c["text"]),
                            ft.Text("itservicedesk@montclair.edu", size=15, color=c["text"], selectable=True),
                            ft.Text("Or the IT Service Desk:", size=14, color=c["text"]),
                            ft.Text("973-655-7971", size=15, color=c["text"], selectable=True),
                            ft.OutlinedButton(
                                "Back",
                                on_click=go_back,
                                style=ft.ButtonStyle(
                                    color=MSU_RED,
                                    side=ft.BorderSide(1, MSU_RED),
                                    shape=ft.RoundedRectangleBorder(radius=18),
                                    padding=ft.Padding(20, 12, 20, 12),
                                    text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_700),
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        )
        show_screen(app_shell(body), "help")

    def build_home_overlays():
        c = colors()

        search_bar = ft.Container(
            margin=ft.Margin.only(left=14, top=12, right=14),
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Container(
                        height=58,
                        bgcolor=c["surface"],
                        border=ft.Border.all(1, c["border"]),
                        border_radius=29,
                        padding=ft.Padding(16, 6, 12, 6),
                        content=ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.SEARCH, color=c["subtext"], size=24),
                                ft.Container(width=12),
                                ft.TextField(
                                    ref=search_field_ref,
                                    value=search_value,
                                    hint_text="Search campus building",
                                    border=ft.InputBorder.NONE,
                                    filled=False,
                                    text_size=16,
                                    color=c["text"],
                                    cursor_color=MSU_RED,
                                    expand=True,
                                    dense=False,
                                    height=44,
                                    content_padding=ft.Padding(0, 10, 0, 8),
                                    on_change=lambda e: update_search_suggestions(e.control.value),
                                    on_submit=lambda e: page.run_task(perform_search),
                                ),
                                ft.IconButton(
                                    ref=clear_search_button_ref,
                                    icon=ft.Icons.CLOSE,
                                    icon_color=c["subtext"],
                                    icon_size=20,
                                    visible=bool(search_value.strip()),
                                    on_click=lambda e: clear_search_box(),
                                    style=ft.ButtonStyle(padding=0),
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        ref=suggestion_box_ref,
                        visible=False,
                        bgcolor=c["surface"],
                        border=ft.Border.all(1, c["border"]),
                        border_radius=20,
                        margin=ft.Margin.only(top=6),
                        padding=ft.Padding(0, 6, 0, 6),
                        content=ft.Column(ref=suggestion_column_ref, spacing=0, tight=True),
                    ),
                ],
            ),
        )

        my_location_fab = ft.Container(
            width=48,
            height=48,
            border_radius=24,
            bgcolor=c["fab_bg"],
            border=ft.Border.all(1, c["border"]),
            alignment=ft.Alignment(0, 0),
            ink=True,
            on_click=lambda e: page.run_task(load_user_location, True, True),
            content=ft.Icon(ft.Icons.MY_LOCATION, color=MSU_RED, size=24),
        )

        cs_fab = ft.Container(
            width=48,
            height=48,
            border_radius=24,
            bgcolor=c["fab_bg"],
            border=ft.Border.all(1, c["border"]),
            alignment=ft.Alignment(0, 0),
            ink=True,
            on_click=lambda e: center_to_cs_building(),
            content=ft.Icon(ft.Icons.APARTMENT, color=MSU_RED, size=22),
        )

        clear_route_fab = ft.Container(
            visible=bool(route_points),
            width=48,
            height=48,
            border_radius=24,
            bgcolor=c["fab_bg"],
            border=ft.Border.all(1, c["border"]),
            alignment=ft.Alignment(0, 0),
            ink=True,
            on_click=lambda e: clear_route_and_refresh(),
            content=ft.Icon(ft.Icons.CLOSE, color=MSU_RED, size=22),
        )

        place_card = ft.Container(
            ref=place_card_ref,
            visible=False,
            left=14,
            right=14,
            bottom=78,
        )

        return ft.Stack(
            expand=True,
            controls=[
                build_map(),
                ft.Container(top=0, left=0, right=0, content=search_bar),
                ft.Container(
                    right=14,
                    bottom=90,
                    content=ft.Column(
                        spacing=10,
                        controls=[my_location_fab, cs_fab, clear_route_fab],
                    ),
                ),
                place_card,
            ],
        )

    def show_home_page():
        content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(expand=True, content=build_home_overlays()),
                build_bottom_nav("home"),
            ],
        )
        show_screen(app_shell(content), "home")
        refresh_map_layers()
        update_place_card()

    def clear_route_and_refresh():
        clear_route()
        refresh_map_layers()

    def center_to_cs_building():
        place = LABEL_TO_PLACE["Center for Computing and Information Science"]
        set_map_view(place["coordinates"], FOCUSED_ZOOM)
        show_home_page()

    def split_events(events):
        today = date.today()
        upcoming = []
        past = []

        for event in events:
            event_date = parse_event_date(event.get("date"))
            if event_date is None or event_date >= today:
                upcoming.append(event)
            else:
                past.append(event)

        return upcoming, past

    def build_event_card(event_item):
        c = colors()
        location_name = event_item.get("location") or "Location TBD"

        return ft.Container(
            border_radius=22,
            bgcolor=c["surface"],
            border=ft.Border.all(1, c["border"]),
            padding=16,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text(
                        event_item.get("title") or "Untitled Event",
                        size=17,
                        weight=ft.FontWeight.W_800,
                        color=c["text"],
                        expand=True,
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.PLACE_OUTLINED, size=16, color=MSU_RED),
                            ft.Text(location_name, size=13, color=c["text"]),
                        ],
                    ),
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=15, color=MSU_RED),
                                    ft.Text(format_event_date(event_item.get("date")), size=12, color=c["text"]),
                                ],
                            ),
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.ACCESS_TIME, size=15, color=MSU_RED),
                                    ft.Text(format_event_time(event_item.get("time")), size=12, color=c["text"]),
                                ],
                            ),
                        ],
                    ),
                    ft.Text(
                        event_item.get("description") or "No details available.",
                        size=12,
                        color=c["subtext"],
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.FilledButton(
                        "Directions",
                        icon=ft.Icons.DIRECTIONS_WALK,
                        width=9999,
                        height=44,
                        style=ft.ButtonStyle(
                            bgcolor=MSU_RED,
                            color=WHITE,
                            shape=ft.RoundedRectangleBorder(radius=14),
                            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_700),
                        ),
                        on_click=lambda e, loc=location_name: page.run_task(route_to_event_location, loc),
                    ),
                ],
            ),
        )

    def show_events_page():
        c = colors()
        events = get_events()
        upcoming_events, past_events = split_events(events)

        add_button = (
            ft.IconButton(
                icon=ft.Icons.ADD,
                icon_color=MSU_RED,
                on_click=lambda e: show_add_event_page(),
            )
            if current_user_role == "Faculty"
            else None
        )

        controls = [build_event_card(item) for item in upcoming_events] if upcoming_events else [
            ft.Text("No upcoming events found.", color=c["text"])
        ]

        controls.append(ft.Container(height=8))
        controls.append(
            ft.OutlinedButton(
                "Past Events",
                icon=ft.Icons.HISTORY,
                height=46,
                style=ft.ButtonStyle(
                    color=MSU_RED,
                    side=ft.BorderSide(1, MSU_RED),
                    shape=ft.RoundedRectangleBorder(radius=14),
                ),
                on_click=lambda e: show_past_events_page(past_events),
            )
        )

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header("MSU Events", "Campus events", trailing=add_button),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.ListView(spacing=16, controls=controls),
                ),
                build_bottom_nav("events"),
            ],
        )

        show_screen(app_shell(body), "events")

    def show_past_events_page(past_events):
        c = colors()

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header(
                    "Past Events",
                    "Previous campus events",
                    trailing=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=MSU_RED,
                        on_click=lambda e: show_events_page(),
                    ),
                ),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.ListView(
                        spacing=16,
                        controls=[build_event_card(item) for item in past_events] if past_events else [
                            ft.Text("No past events found.", color=c["text"])
                        ],
                    ),
                ),
            ],
        )
        show_screen(app_shell(body), "past_events")

    def show_add_event_page():
        c = colors()

        title_field = ft.TextField(label="Event title", border_radius=16, focused_border_color=MSU_RED, filled=True, bgcolor=c["input_bg"], color=c["text"])
        location_field = ft.TextField(label="Location", border_radius=16, focused_border_color=MSU_RED, filled=True, bgcolor=c["input_bg"], color=c["text"])
        date_field = ft.TextField(label="Date", hint_text="YYYY-MM-DD", border_radius=16, focused_border_color=MSU_RED, filled=True, bgcolor=c["input_bg"], color=c["text"])
        time_field = ft.TextField(label="Time", hint_text="9:00 AM or 13:00", border_radius=16, focused_border_color=MSU_RED, filled=True, bgcolor=c["input_bg"], color=c["text"])
        details_field = ft.TextField(label="Details", multiline=True, min_lines=4, max_lines=6, border_radius=16, focused_border_color=MSU_RED, filled=True, bgcolor=c["input_bg"], color=c["text"])

        def save_event(_):
            title = (title_field.value or "").strip()
            location = (location_field.value or "").strip()
            date_value = (date_field.value or "").strip()
            raw_time_value = (time_field.value or "").strip()
            details = (details_field.value or "").strip() or "No details added."

            if not title or not location or not date_value or not raw_time_value:
                show_snack("Please fill in title, location, date, and time.")
                return

            try:
                datetime.strptime(date_value, "%Y-%m-%d")
            except ValueError:
                show_snack("Use date as YYYY-MM-DD.")
                return

            time_value = normalize_time(raw_time_value)
            if time_value is None:
                show_snack("Use time like 9:00 AM or 13:00.")
                return

            try:
                add_event(title, location, date_value, time_value, details, "Pending")
                show_events_page()
                show_snack("Event submitted.")
            except Exception as ex:
                show_snack(f"Could not save event: {ex}")

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header(
                    "Add Event",
                    "Faculty event submission",
                    trailing=ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color=MSU_RED,
                        on_click=lambda e: show_events_page(),
                    ),
                ),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.ListView(
                        spacing=14,
                        controls=[
                            title_field,
                            location_field,
                            date_field,
                            time_field,
                            details_field,
                            ft.FilledButton(
                                "Save Event",
                                height=48,
                                style=ft.ButtonStyle(
                                    bgcolor=MSU_RED,
                                    color=WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=14),
                                ),
                                on_click=save_event,
                            ),
                        ],
                    ),
                ),
            ],
        )
        show_screen(app_shell(body), "add_event")

    def show_favorites_page():
        c = colors()

        def fav_card(place):
            return ft.Container(
                border_radius=18,
                bgcolor=c["surface"],
                border=ft.Border.all(1, c["border"]),
                padding=14,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            expand=True,
                            spacing=4,
                            controls=[
                                ft.Text(place["label"], size=15, weight=ft.FontWeight.W_700, color=c["text"]),
                                ft.Text(place.get("info", ""), size=12, color=c["subtext"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.OPEN_IN_NEW,
                                    icon_color=MSU_RED,
                                    on_click=lambda e, p=dict(place): page.run_task(open_favorite, p),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=MSU_RED,
                                    on_click=lambda e, p=dict(place): remove_favorite(p),
                                ),
                            ],
                        ),
                    ],
                ),
            )

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header(
                    "Favorites",
                    "Saved campus places",
                    trailing=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=MSU_RED,
                        on_click=lambda e: show_settings_page(),
                    ),
                ),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.ListView(
                        spacing=14,
                        controls=[fav_card(item) for item in favorite_places] if favorite_places else [
                            ft.Text("No favorites yet.", size=14, color=c["subtext"])
                        ],
                    ),
                ),
            ],
        )
        show_screen(app_shell(body), "favorites")

    async def open_favorite(place):
        await select_place(place, False)
        show_home_page()

    def remove_favorite(place):
        nonlocal favorite_places
        favorite_places = [item for item in favorite_places if item["label"].lower() != place["label"].lower()]
        show_favorites_page()
        show_snack(f"Removed {place['label']} from favorites.")

    def show_settings_page():
        c = colors()

        def settings_row(icon, title, subtitle=None, trailing=None, on_click=None):
            return ft.Container(
                padding=16,
                border_radius=18,
                bgcolor=c["surface"],
                border=ft.Border.all(1, c["border"]),
                ink=on_click is not None,
                on_click=on_click,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=52,
                            height=52,
                            border_radius=14,
                            bgcolor=MSU_RED,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=WHITE, size=24),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=4,
                            controls=[
                                ft.Text(title, size=16, weight=ft.FontWeight.W_700, color=c["text"]),
                                ft.Text(subtitle or "", size=12, color=c["subtext"]),
                            ],
                        ),
                        trailing if trailing else ft.Container(width=1),
                    ],
                ),
            )

        def appearance_changed(e):
            nonlocal is_dark_mode
            is_dark_mode = e.control.value
            show_settings_page()

        def sign_out(_):
            nonlocal current_user_email, current_user_role, user_location, selected_place, route_points, search_value
            current_user_email = ""
            current_user_role = ""
            user_location = None
            selected_place = None
            route_points = []
            search_value = ""
            show_login()

        profile_card = ft.Container(
            padding=18,
            border_radius=20,
            bgcolor=c["profile_fill"],
            border=ft.Border.all(1, c["border"]),
            content=ft.Row(
                spacing=14,
                controls=[
                    ft.Container(
                        width=56,
                        height=56,
                        border_radius=18,
                        bgcolor=MSU_RED,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            (current_user_email[:1].upper() if current_user_email else "U"),
                            size=24,
                            weight=ft.FontWeight.W_800,
                            color=WHITE,
                        ),
                    ),
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(current_user_email or "Not signed in", size=15, weight=ft.FontWeight.W_700, color=c["text"]),
                            ft.Text(current_user_role or "User", size=13, color=MSU_RED),
                        ],
                    ),
                ],
            ),
        )

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header("Settings", "App preferences and saved places"),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.ListView(
                        spacing=16,
                        controls=[
                            profile_card,
                            settings_row(
                                ft.Icons.PALETTE_OUTLINED,
                                "Dark mode",
                                "Change the app appearance",
                                trailing=ft.Switch(
                                    value=is_dark_mode,
                                    active_color=MSU_RED,
                                    on_change=appearance_changed,
                                ),
                            ),
                            settings_row(
                                ft.Icons.FAVORITE_BORDER,
                                "Favorites",
                                f"{len(favorite_places)} saved place(s)" if favorite_places else "No saved places yet",
                                trailing=ft.TextButton(
                                    "Open",
                                    style=ft.ButtonStyle(color=MSU_RED),
                                    on_click=lambda e: show_favorites_page(),
                                ),
                            ),
                            settings_row(
                                ft.Icons.GPS_FIXED,
                                "Location status",
                                location_status,
                                trailing=ft.TextButton(
                                    "Refresh",
                                    style=ft.ButtonStyle(color=MSU_RED),
                                    on_click=lambda e: page.run_task(load_user_location, True, False),
                                ),
                            ),
                            settings_row(
                                ft.Icons.HELP_OUTLINE,
                                "Account help",
                                "Forgot username or password?",
                                trailing=ft.TextButton(
                                    "Open",
                                    style=ft.ButtonStyle(color=MSU_RED),
                                    on_click=lambda e: show_help_page("settings"),
                                ),
                            ),
                            ft.FilledButton(
                                "Sign Out",
                                height=52,
                                style=ft.ButtonStyle(
                                    bgcolor=BLACK if not is_dark_mode else WHITE,
                                    color=WHITE if not is_dark_mode else BLACK,
                                    shape=ft.RoundedRectangleBorder(radius=16),
                                    text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_700),
                                ),
                                on_click=sign_out,
                            ),
                        ],
                    ),
                ),
                build_bottom_nav("settings"),
            ],
        )
        show_screen(app_shell(body), "settings")

    page.add(main_area)
    page.services.append(geo)
    show_login()


if __name__ == "__main__":
    ft.run(main)