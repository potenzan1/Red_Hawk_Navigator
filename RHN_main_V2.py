from datetime import datetime

import flet as ft
import flet_geolocator as ftg
import flet_map as ftm
import httpx
import mysql.connector

GRAPH_HOPPER_API_KEY = "3e19284a-10f0-424f-9add-57bd72967758"
DEFAULT_CENTER = ftm.MapLatitudeLongitude(40.862147765671764, -74.1981587142951)
DEFAULT_ZOOM = 17

CAMPUS_LOCATIONS = {
    "cs building": {
        "label": "Center for Computing and Information Science",
        "coordinates": ftm.MapLatitudeLongitude(40.86332, -74.19735),
    },
    "center for computing and information science": {
        "label": "Center for Computing and Information Science",
        "coordinates": ftm.MapLatitudeLongitude(40.86332, -74.19735),
    },
    "ccis": {
        "label": "Center for Computing and Information Science",
        "coordinates": ftm.MapLatitudeLongitude(40.86332, -74.19735),
    },
    "student center": {
        "label": "Student Center",
        "coordinates": ftm.MapLatitudeLongitude(40.86272, -74.19710),
    },
    "university hall": {
        "label": "University Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.86162, -74.19946),
    },
    "dickson hall": {
        "label": "Dickson Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.86062, -74.19866),
    },
    "feliciano school of business": {
        "label": "Feliciano School of Business",
        "coordinates": ftm.MapLatitudeLongitude(40.86020, -74.20045),
    },
    "schmitt hall": {
        "label": "Schmitt Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.86028, -74.19678),
    },
    "sprague library": {
        "label": "Sprague Library",
        "coordinates": ftm.MapLatitudeLongitude(40.85895, -74.19735),
    },
    "finley hall": {
        "label": "Finley Hall",
        "coordinates": ftm.MapLatitudeLongitude(40.85965, -74.19685),
    },
}

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="MSU_Admin",
        password="MSU",
        database="red_hawk_navigation",
    )

def username_ok(value):
    value = (value or "").strip().lower()
    return value.endswith("@montclair.edu") and " " not in value and len(value) > len("@montclair.edu")

def user_auth(username, password):
    username = (username or "").strip().lower()
    password = (password or "").strip()

    if not username_ok(username) or not password:
        return None

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

def get_events():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT eventID, title, location, date, time, description, status
        FROM event
        ORDER BY date ASC, time ASC, eventID DESC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

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

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get("https://graphhopper.com/api/1/route", params=params)
        response.raise_for_status()
        data = response.json()

    coords = data["paths"][0]["points"]["coordinates"]
    return [ftm.MapLatitudeLongitude(lat, lon) for lon, lat in coords]

async def geocode_location(query):
    q = (query or "").strip().lower()
    if not q:
        return None

    if q in CAMPUS_LOCATIONS:
        place = CAMPUS_LOCATIONS[q]
        return {
            "label": place["label"],
            "coordinates": place["coordinates"],
        }

    for key, value in CAMPUS_LOCATIONS.items():
        if q in key or q in value["label"].lower():
            return {
                "label": value["label"],
                "coordinates": value["coordinates"],
            }

    params = {
        "q": f"{query}, Montclair State University",
        "format": "jsonv2",
        "limit": 1,
    }
    headers = {"User-Agent": "red_hawk_navigator/1.0"}

    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            response = await client.get("https://nominatim.openstreetmap.org/search", params=params)
            response.raise_for_status()
            data = response.json()

        if not data:
            return None

        item = data[0]
        return {
            "label": item.get("display_name", query),
            "coordinates": ftm.MapLatitudeLongitude(float(item["lat"]), float(item["lon"])),
        }
    except Exception:
        return None

async def main(page: ft.Page):
    page.title = "Red Hawk Navigator"
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed="#C8102E")

    try:
        page.window_width = 390
        page.window_height = 844
        page.window_resizable = False
    except Exception:
        pass

    MSU_RED = "#C8102E"
    RED_TINT = "#FFF1F3"
    BLACK = "#111111"
    WHITE = "#FFFFFF"
    MUTED = "#666666"
    LIGHT_BG = "#F5F5F5"
    LIGHT_BORDER = "#E3E3E3"
    PAGE_BG = "#F7F7F7"
    APP_SHELL = "#D9D9D9"

    main_area = ft.Container(expand=True)

    current_user_name = ""
    current_user_role = ""
    user_location = None
    active_destination = None
    current_center = DEFAULT_CENTER
    current_zoom = DEFAULT_ZOOM
    map_refresh_token = 0
    current_location_status = "Location not loaded yet."

    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    user_marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    polyline_layer_ref = ft.Ref[ftm.PolylineLayer]()

    search_field = ft.TextField(
        hint_text="Search a campus building",
        border_radius=14,
        filled=True,
        bgcolor=LIGHT_BG,
        border_color="transparent",
        focused_border_color="transparent",
        text_size=13,
        height=42,
        dense=True,
        content_padding=ft.Padding(10, 6, 10, 6),
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
    )

    def colors():
        return {
            "page_bg": PAGE_BG,
            "card_bg": WHITE,
            "text": BLACK,
            "subtext": MUTED,
            "border": LIGHT_BORDER,
            "surface": WHITE,
            "soft_tint": RED_TINT,
            "app_shell": APP_SHELL,
        }

    def show_snack(message):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def handle_geo_error(e):
        nonlocal current_location_status
        current_location_status = f"Location error: {e.data}"
        show_snack(current_location_status)

    geo = ftg.Geolocator(
        configuration=ftg.GeolocatorConfiguration(
            accuracy=ftg.GeolocatorPositionAccuracy.BEST
        ),
        on_error=handle_geo_error,
    )

    def app_shell(content):
        c = colors()
        return ft.Container(
            expand=True,
            bgcolor=c["app_shell"],
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

    def nav_item(icon, label, selected, on_click):
        c = colors()
        active_color = MSU_RED if selected else c["text"]
        return ft.Container(
            expand=True,
            ink=True,
            on_click=on_click,
            padding=10,
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
            padding=ft.Padding(8, 4, 8, 8),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    nav_item(ft.Icons.MAP_OUTLINED, "Map", active == "home", lambda e: show_home_page()),
                    nav_item(ft.Icons.CALENDAR_MONTH_OUTLINED, "Events", active == "events", lambda e: show_events_page()),
                    nav_item(ft.Icons.SETTINGS_OUTLINED, "Settings", active == "settings", lambda e: show_settings_page()),
                ],
            ),
        )

    def show_screen(content):
        main_area.content = content
        page.update()

    def set_map_view(center, zoom=18):
        nonlocal current_center, current_zoom, map_refresh_token
        current_center = center
        current_zoom = zoom
        map_refresh_token += 1

    def clear_route_and_pins():
        nonlocal active_destination
        active_destination = None
        if marker_layer_ref.current:
            marker_layer_ref.current.markers.clear()
        if polyline_layer_ref.current:
            polyline_layer_ref.current.polylines.clear()

    async def draw_route_to(destination, label=None):
        nonlocal active_destination
        if marker_layer_ref.current is None or polyline_layer_ref.current is None:
            return

        marker_layer_ref.current.markers.clear()
        polyline_layer_ref.current.polylines.clear()

        marker_layer_ref.current.markers.append(
            ftm.Marker(
                coordinates=destination,
                content=ft.Icon(ft.Icons.LOCATION_ON, color=MSU_RED, size=36),
            )
        )

        active_destination = destination
        set_map_view(destination)

        if user_location is None:
            page.update()
            if label:
                show_snack(f"Centered on {label}.")
            return

        try:
            route_points = await get_route(user_location, destination)
            polyline_layer_ref.current.polylines.append(
                ftm.PolylineMarker(
                    coordinates=route_points,
                    color=MSU_RED,
                    stroke_width=5,
                )
            )
            page.update()
            if label:
                show_snack(f"Route loaded to {label}.")
        except Exception as ex:
            page.update()
            show_snack(f"Could not load route: {ex}")

    async def load_user_location(show_feedback=False, recenter=True):
        nonlocal user_location, current_location_status
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
            current_location_status = "Could not get your current location. Check app permissions and GPS."
            if show_feedback:
                show_snack(current_location_status)
            return

        user_location = ftm.MapLatitudeLongitude(pos.latitude, pos.longitude)
        current_location_status = "Your location is active for navigation."

        if recenter:
            set_map_view(user_location, 18)
            show_home_page()

        if active_destination is not None:
            await draw_route_to(active_destination)

        if show_feedback:
            show_snack(current_location_status)

    async def perform_search(_=None):
        query = (search_field.value or "").strip()
        if not query:
            show_snack("Enter a building or place to search.")
            return

        result = await geocode_location(query)
        if result is None:
            show_snack("Location not found.")
            return

        await draw_route_to(result["coordinates"], result["label"])
        show_home_page()

    async def center_to_cs_building(_=None):
        cs = CAMPUS_LOCATIONS["cs building"]
        search_field.value = cs["label"]
        await draw_route_to(cs["coordinates"], cs["label"])
        show_home_page()

    async def handle_map_tap(e: ftm.MapTapEvent):
        if e.name != "tap":
            return
        await draw_route_to(e.coordinates, "selected point")

    def format_event_date(date_value):
        if isinstance(date_value, datetime):
            return date_value.strftime("%b %d, %Y")
        try:
            return datetime.strptime(str(date_value), "%Y-%m-%d").strftime("%b %d, %Y")
        except Exception:
            return str(date_value)

    def format_event_time(time_value):
        value = str(time_value).split(".")[0]
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).strftime("%I:%M %p").lstrip("0")
            except Exception:
                continue
        return str(time_value)

    def normalize_time(value):
        value = (value or "").strip()

        try:
            return datetime.strptime(value, "%H:%M").strftime("%H:%M:%S")
        except ValueError:
            pass

        try:
            return datetime.strptime(value.upper(), "%I:%M %p").strftime("%H:%M:%S")
        except ValueError:
            pass

        return None

    def show_login():
        email_field = ft.TextField(
            hint_text="Email address",
            prefix_icon=ft.Icons.MAIL_OUTLINE,
            border_radius=18,
            border_color="transparent",
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor="#F2F2F2",
            color=BLACK,
            text_size=14,
            height=55,
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
            bgcolor="#F2F2F2",
            color=BLACK,
            text_size=14,
            height=55,
            content_padding=ft.Padding(16, 12, 16, 12),
        )

        error_text = ft.Text("", size=12, color=MSU_RED, visible=False)

        def do_login(_):
            nonlocal current_user_name, current_user_role

            result = user_auth(email_field.value, password_field.value)

            if not result:
                error_text.value = "Invalid email or password."
                error_text.visible = True
                page.update()
                return

            current_user_name = result["email"]
            current_user_role = result["role"]
            error_text.visible = False
            search_field.value = ""
            set_map_view(DEFAULT_CENTER, DEFAULT_ZOOM)
            show_home_page()
            page.run_task(load_user_location, False, False)

        header = ft.Column(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "MONTCLAIR",
                    size=32,
                    weight=ft.FontWeight.W_900,
                    color=MSU_RED,
                ),
                ft.Text(
                    "STATE UNIVERSITY",
                    size=13,
                    weight=ft.FontWeight.W_700,
                    color=BLACK,
                ),
            ],
        )

        login_card = ft.Container(
            padding=ft.Padding(24, 30, 24, 26),
            border_radius=28,
            bgcolor=WHITE,
            shadow=ft.BoxShadow(
                blur_radius=20,
                spread_radius=0,
                color="#20000000",
                offset=ft.Offset(0, 6),
            ),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=18,
                controls=[
                    header,
                    ft.Text(
                        "Red Hawk Navigator",
                        size=24,
                        weight=ft.FontWeight.W_800,
                        color=BLACK,
                    ),
                    ft.Text(
                        "Student project demo",
                        size=12,
                        color="#777777",
                    ),
                    ft.Container(height=8),
                    email_field,
                    password_field,
                    error_text,
                    ft.Container(
                        margin=ft.Margin.only(top=8),
                        content=ft.FilledButton(
                            "Sign In",
                            width=320,
                            height=52,
                            style=ft.ButtonStyle(
                                bgcolor=MSU_RED,
                                color=WHITE,
                                shape=ft.RoundedRectangleBorder(radius=16),
                                elevation=3,
                                text_style=ft.TextStyle(
                                    size=15,
                                    weight=ft.FontWeight.W_700,
                                ),
                            ),
                            on_click=do_login,
                        ),
                    ),
                    ft.TextButton(
                        "Forgot username or password?",
                        on_click=lambda e: show_help_page(),
                        style=ft.ButtonStyle(
                            color="#2D5D95",
                            text_style=ft.TextStyle(
                                size=13,
                                weight=ft.FontWeight.W_600,
                            ),
                        ),
                    ),
                ],
            ),
        )

        content = ft.Container(
            expand=True,
            bgcolor="#EFEFEF",
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=390,
                height=844,
                padding=20,
                alignment=ft.Alignment(0, 0),
                content=login_card,
            ),
        )

        show_screen(content)

    def show_help_page():
        c = colors()

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding(28, 26, 28, 14),
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(
                                "Account Help",
                                size=24,
                                weight=ft.FontWeight.W_800,
                                color=c["text"],
                            ),
                            ft.Text(
                                "Montclair State University",
                                size=11,
                                color=c["subtext"],
                            ),
                        ],
                    ),
                ),
                ft.Divider(height=1, color=c["border"]),
                ft.Container(
                    expand=True,
                    padding=30,
                    content=ft.Column(
                        spacing=22,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Text(
                                "Forgot username or password?",
                                size=21,
                                weight=ft.FontWeight.W_800,
                                color=c["text"],
                            ),
                            ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text("Please contact:", size=14, color=c["text"]),
                                    ft.Text(
                                        "netidmanagement@mail.montclair.edu",
                                        size=14,
                                        color=c["text"],
                                    ),
                                ],
                            ),
                            ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text("Or the IT Service Desk:", size=14, color=c["text"]),
                                    ft.Text("973-655-7971", size=14, color=c["text"]),
                                ],
                            ),
                            ft.OutlinedButton(
                                "Back to Sign In",
                                on_click=lambda e: show_login(),
                                style=ft.ButtonStyle(
                                    color="#2D5D95",
                                    side=ft.BorderSide(1, "#8F949C"),
                                    shape=ft.RoundedRectangleBorder(radius=18),
                                    padding=ft.Padding(22, 16, 22, 16),
                                    text_style=ft.TextStyle(
                                        size=13,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        )

        content = ft.Container(
            expand=True,
            bgcolor="#E9E9E9",
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=390,
                height=844,
                border_radius=28,
                bgcolor=c["page_bg"],
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=body,
            ),
        )

        show_screen(content)

    def build_map():
        return ftm.Map(
            key=f"map-{map_refresh_token}",
            expand=True,
            initial_center=current_center,
            initial_zoom=current_zoom,
            interaction_configuration=ftm.InteractionConfiguration(flags=ftm.InteractionFlag.ALL),
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
                ftm.MarkerLayer(
                    ref=user_marker_layer_ref,
                    markers=[
                        ftm.Marker(
                            coordinates=user_location,
                            content=ft.Icon(ft.Icons.MY_LOCATION, color="#1E88E5", size=30),
                        )
                    ] if user_location is not None else [],
                ),
                ftm.MarkerLayer(ref=marker_layer_ref, markers=[]),
                ftm.PolylineLayer(ref=polyline_layer_ref, polylines=[]),
            ],
        )

    def show_home_page():
        c = colors()

        search_bar = ft.Container(
            bgcolor=c["surface"],
            border_radius=18,
            border=ft.Border.all(1, c["border"]),
            padding=6,
            margin=ft.Margin.only(left=14, top=12, right=14, bottom=0),
            shadow=ft.BoxShadow(
                blur_radius=10,
                spread_radius=0,
                color="#14000000",
                offset=ft.Offset(0, 3),
            ),
            content=ft.Row(
                controls=[
                    search_field,
                    ft.Container(
                        width=38,
                        height=38,
                        border_radius=11,
                        bgcolor=RED_TINT,
                        alignment=ft.Alignment(0, 0),
                        content=ft.IconButton(
                            icon=ft.Icons.SEARCH,
                            icon_color=MSU_RED,
                            icon_size=20,
                            on_click=lambda e: page.run_task(perform_search),
                        ),
                    ),
                ],
            ),
        )

        user_badge = ft.Container(
            left=14,
            top=78,
            content=ft.Container(
                bgcolor=c["surface"],
                border_radius=18,
                border=ft.Border.all(1, c["border"]),
                padding=ft.Padding(12, 10, 12, 10),
                shadow=ft.BoxShadow(
                    blur_radius=8,
                    spread_radius=0,
                    color="#10000000",
                    offset=ft.Offset(0, 2),
                ),
                content=ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            current_user_name,
                            size=12,
                            weight=ft.FontWeight.W_700,
                            color=c["text"],
                        ),
                        ft.Text(
                            current_user_role,
                            size=11,
                            color=MSU_RED,
                        ),
                    ],
                ),
            ),
        )

        map_controls = ft.Column(
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.END,
            spacing=10,
            controls=[
                ft.FloatingActionButton(
                    icon=ft.Icons.APARTMENT,
                    bgcolor=c["surface"],
                    foreground_color=MSU_RED,
                    mini=True,
                    on_click=lambda e: page.run_task(center_to_cs_building),
                ),
                ft.FloatingActionButton(
                    icon=ft.Icons.MY_LOCATION,
                    bgcolor=c["surface"],
                    foreground_color="#1E88E5",
                    mini=True,
                    on_click=lambda e: page.run_task(load_user_location, True, True),
                ),
                ft.FloatingActionButton(
                    icon=ft.Icons.CLOSE,
                    bgcolor=c["surface"],
                    foreground_color=c["text"],
                    mini=True,
                    on_click=lambda e: [clear_route_and_pins(), show_home_page()],
                ),
            ],
        )

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(
                    expand=True,
                    content=ft.Stack(
                        expand=True,
                        controls=[
                            build_map(),
                            ft.Container(top=0, left=0, right=0, content=search_bar),
                            user_badge,
                            ft.Container(right=14, bottom=20, content=map_controls),
                        ],
                    ),
                ),
                build_bottom_nav("home"),
            ],
        )
        show_screen(app_shell(body))

    def show_events_page():
        c = colors()

        def event_card(event_item):
            status_value = (event_item.get("status") or "").strip().lower()

            header_controls = [
                ft.Text(
                    event_item["title"],
                    size=18,
                    weight=ft.FontWeight.W_800,
                    color=c["text"],
                    expand=True,
                )
            ]

            if status_value == "pending":
                header_controls.append(
                    ft.Container(
                        padding=ft.Padding(10, 4, 10, 4),
                        border_radius=12,
                        bgcolor="#FFF1F3",
                        content=ft.Text(
                            "Pending",
                            size=11,
                            weight=ft.FontWeight.W_700,
                            color=MSU_RED,
                        ),
                    )
                )

            return ft.Container(
                border_radius=18,
                bgcolor=c["card_bg"],
                border=ft.Border.all(1, c["border"]),
                padding=16,
                shadow=ft.BoxShadow(
                    blur_radius=10,
                    spread_radius=0,
                    color="#0C000000",
                    offset=ft.Offset(0, 2),
                ),
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=header_controls,
                        ),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.PLACE_OUTLINED, size=16, color=MSU_RED),
                                ft.Text(event_item["location"], size=13, color=c["text"]),
                            ],
                        ),
                        ft.Row(
                            spacing=16,
                            controls=[
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=16, color=MSU_RED),
                                        ft.Text(format_event_date(event_item["date"]), size=13, color=c["text"]),
                                    ],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=MSU_RED),
                                        ft.Text(format_event_time(event_item["time"]), size=13, color=c["text"]),
                                    ],
                                ),
                            ],
                        ),
                        ft.Text(
                            event_item["description"],
                            size=13,
                            color=c["subtext"],
                        ),
                    ],
                ),
            )

        add_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            bgcolor=MSU_RED,
            foreground_color=WHITE,
            mini=True,
            on_click=lambda e: show_add_event_page(),
        )

        cards = [event_card(item) for item in get_events()]

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(
                    padding=20,
                    border=ft.Border.only(bottom=ft.BorderSide(1, c["border"])) ,
                    bgcolor=c["surface"],
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(
                                        "MSU Events",
                                        size=22,
                                        weight=ft.FontWeight.W_800,
                                        color=c["text"],
                                    ),
                                    ft.Text(
                                        "Campus events",
                                        size=12,
                                        color=c["subtext"],
                                    ),
                                ],
                            ),
                            add_button,
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    bgcolor=c["page_bg"],
                    padding=20,
                    content=ft.ListView(
                        spacing=16,
                        controls=cards if cards else [ft.Text("No events found.", color=c["text"])],
                    ),
                ),
                build_bottom_nav("events"),
            ],
        )

        show_screen(app_shell(body))

    def show_add_event_page():
        c = colors()

        title_field = ft.TextField(
            label="Event title",
            border_radius=16,
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor=c["card_bg"],
            color=c["text"],
        )

        location_field = ft.TextField(
            label="Location",
            border_radius=16,
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor=c["card_bg"],
            color=c["text"],
        )

        date_field = ft.TextField(
            label="Date",
            hint_text="YYYY-MM-DD",
            border_radius=16,
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor=c["card_bg"],
            color=c["text"],
        )

        time_field = ft.TextField(
            label="Time",
            hint_text="9:00 AM or 13:00",
            border_radius=16,
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor=c["card_bg"],
            color=c["text"],
        )

        details_field = ft.TextField(
            label="Details",
            multiline=True,
            min_lines=4,
            max_lines=6,
            border_radius=16,
            focused_border_color=MSU_RED,
            filled=True,
            bgcolor=c["card_bg"],
            color=c["text"],
        )

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
                show_snack("Event submitted and marked as Pending.")
            except mysql.connector.Error as ex:
                show_snack(f"Could not save event: {ex}")

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(
                    padding=20,
                    bgcolor=c["surface"],
                    border=ft.Border.only(bottom=ft.BorderSide(1, c["border"])) ,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Add Event",
                                size=22,
                                weight=ft.FontWeight.W_800,
                                color=c["text"],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                on_click=lambda e: show_events_page(),
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    bgcolor=c["page_bg"],
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
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                ),
                                on_click=save_event,
                            ),
                        ],
                    ),
                ),
            ],
        )
        show_screen(app_shell(body))

    def show_settings_page():
        c = colors()

        def settings_row(icon, title, subtitle=None, trailing=None, on_click=None):
            return ft.Container(
                padding=16,
                border_radius=18,
                bgcolor=c["card_bg"],
                border=ft.Border.all(1, c["border"]),
                ink=on_click is not None,
                on_click=on_click,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=48,
                            height=48,
                            border_radius=14,
                            bgcolor=c["soft_tint"],
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, color=MSU_RED, size=24),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=4,
                            controls=[
                                ft.Text(
                                    title,
                                    size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=c["text"],
                                ),
                                ft.Text(
                                    subtitle or "",
                                    size=12,
                                    color=c["subtext"],
                                ),
                            ],
                        ),
                        trailing if trailing else ft.Icon(ft.Icons.CHEVRON_RIGHT, color=c["subtext"]),
                    ],
                ),
            )

        def sign_out(_):
            nonlocal current_user_name, current_user_role, user_location, active_destination, current_location_status
            current_user_name = ""
            current_user_role = ""
            user_location = None
            active_destination = None
            current_location_status = "Location not loaded yet."
            clear_route_and_pins()
            search_field.value = ""
            set_map_view(DEFAULT_CENTER, DEFAULT_ZOOM)
            show_login()

        header = ft.Container(
            padding=ft.Padding(20, 20, 20, 14),
            bgcolor=c["surface"],
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(
                        "Settings",
                        size=24,
                        weight=ft.FontWeight.W_800,
                        color=c["text"],
                    ),
                    ft.Text(
                        "Manage your account and app preferences",
                        size=12,
                        color=c["subtext"],
                    ),
                ],
            ),
        )

        divider = ft.Divider(height=1, color=c["border"])

        profile_card = ft.Container(
            padding=18,
            border_radius=22,
            bgcolor=c["soft_tint"],
            border=ft.Border.all(1, "#F3D9DF"),
            content=ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=60,
                        height=60,
                        border_radius=18,
                        bgcolor=MSU_RED,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            (current_user_name[:1].upper() if current_user_name else "U"),
                            size=26,
                            weight=ft.FontWeight.W_800,
                            color=WHITE,
                        ),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=4,
                        controls=[
                            ft.Text(
                                current_user_name or "Not signed in",
                                size=16,
                                weight=ft.FontWeight.W_700,
                                color=c["text"],
                            ),
                            ft.Text(
                                current_user_role or "Unknown role",
                                size=13,
                                color=MSU_RED,
                            ),
                        ],
                    ),
                ],
            ),
        )

        location_row = settings_row(
            ft.Icons.GPS_FIXED,
            "Location status",
            current_location_status,
            trailing=ft.TextButton(
                "Refresh",
                on_click=lambda e: page.run_task(load_user_location, True, False),
            ),
        )

        help_row = settings_row(
            ft.Icons.HELP_OUTLINE,
            "Account help",
            "Forgot username or password?",
            trailing=ft.TextButton("Open", on_click=lambda e: show_help_page()),
        )

        map_row = settings_row(
            ft.Icons.MAP_OUTLINED,
            "Back to map",
            "Return to the campus map screen.",
            trailing=ft.TextButton("Open", on_click=lambda e: show_home_page()),
        )

        clear_row = settings_row(
            ft.Icons.ROUTE_OUTLINED,
            "Clear current route",
            "Remove the active destination and route line.",
            trailing=ft.TextButton(
                "Clear",
                on_click=lambda e: [clear_route_and_pins(), show_settings_page()],
            ),
        )

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                divider,
                ft.Container(
                    expand=True,
                    bgcolor=c["page_bg"],
                    padding=20,
                    content=ft.ListView(
                        spacing=16,
                        controls=[
                            profile_card,
                            location_row,
                            help_row,
                            map_row,
                            clear_row,
                            ft.Container(height=6),
                            ft.FilledButton(
                                "Sign Out",
                                height=52,
                                style=ft.ButtonStyle(
                                    bgcolor="#111111",
                                    color=WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=14),
                                    text_style=ft.TextStyle(
                                        size=16,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                ),
                                on_click=sign_out,
                            ),
                        ],
                    ),
                ),
                build_bottom_nav("settings"),
            ],
        )

        show_screen(app_shell(body))

    page.add(main_area)
    page.services.append(geo)
    show_login()

if __name__ == "__main__":
    ft.run(main)