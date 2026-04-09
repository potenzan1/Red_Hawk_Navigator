import flet as ft
import flet_map as ftm
import flet_geolocator as ftg
import httpx
import mysql.connector


MSU_DOMAIN = "@montclair.edu"
GRAPH_HOPPER_API_KEY = "3e19284a-10f0-424f-9add-57bd72967758"

db = mysql.connector.connect(
    host="localhost",
    user="MSU_Admin",
    password="MSU",
    database="red_hawk_navigation"
)

def user_auth(email: str, password: str) -> bool:
    if db is None:
        # Demo fallback: allows app usage when MySQL module/server is unavailable.
        return (email or "").strip().lower().endswith(MSU_DOMAIN) and bool((password or "").strip())

    try:
        cursor = db.cursor(dictionary=True)

        query = "SELECT * FROM user WHERE email = %s AND password = %s"
        cursor.execute(query, (email, password))
        user = cursor.fetchone()

        cursor.close()

        return user is not None
    
    except Exception as e:
        print("Database error:", e)
        return False

async def get_route(start, end):
    url = "https://graphhopper.com/api/1/route"
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

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    coords = data["paths"][0]["points"]["coordinates"]
    return [ftm.MapLatitudeLongitude(lat, lon) for lon, lat in coords]


async def main(page: ft.Page):
    page.title = "Red Hawk Navigator"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#FFFFFF"

    try:
        page.window_width = 390
        page.window_height = 844
        page.window_resizable = False
    except Exception:
        pass

    MSU_RED = "#C8102E"
    BLACK = "#111111"
    WHITE = "#FFFFFF"
    BORDER = "#E5E5E5"
    MUTED = "#666666"

    main_area = ft.Container(expand=True)

    current_user_email = ""
    selected_points = []
    # --- BUILDING DATA ---
    buildings = [
    {
        "name": "Student Center",
        "lat": 40.86248,
        "lon": -74.19818,
        "info": "Main student hub with dining, lounges, and event spaces.",
        "hours": "8:00 AM – 10:00 PM"
    },
    {
        "name": "Schmitt Hall",
        "lat": 40.86188,
        "lon": -74.19755,
        "info": "Academic building with classrooms and faculty offices.",
        "hours": "7:30 AM – 9:00 PM"
    },
    {
        "name": "Sprague Library",
        "lat": 40.86130,
        "lon": -74.19870,
        "info": "Primary campus library with study spaces and resources.",
        "hours": "24 Hours"
    },
    {
        "name": "University Hall",
        "lat": 40.86325,
        "lon": -74.1970,
        "info": "Administrative offices and lecture halls.",
        "hours": "8:30 AM – 5:00 PM"
    },
]

# active building popup
    active_building_popup = ft.Ref[ft.Container]()

    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    user_marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    polyline_layer_ref = ft.Ref[ftm.PolylineLayer]()
    user_location = None

    map_style = "standard"
    walking_mode = True
    show_route_hint = True
    show_markers = True

    events_data = [
        {
            "title": "Spring Career Fair",
            "location": "Student Center",
            "time": "1:00 PM",
            "details": "Meet employers and explore internship opportunities.",
        },
        {
            "title": "Red Hawk Game Night",
            "location": "Campus Recreation Center",
            "time": "6:30 PM",
            "details": "Join other students for games and activities.",
        },
        {
            "title": "Club Expo",
            "location": "University Hall",
            "time": "12:00 PM",
            "details": "Discover clubs and student organizations.",
        },
    ]

    def email_ok(v: str) -> bool:
        v = (v or "").strip().lower()
        return v.endswith(MSU_DOMAIN) and len(v) > len(MSU_DOMAIN)

    def show_snack(msg: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def handle_geo_error(e):
        show_snack(f"Location error: {e.data}")

    geo = ftg.Geolocator(
        configuration=ftg.GeolocatorConfiguration(
            accuracy=ftg.GeolocatorPositionAccuracy.BEST
        ),
        on_error=handle_geo_error,
    )

    def show_screen(content):
        main_area.content = content
        page.update()

    async def load_user_location_and_refresh_home(show_feedback: bool = False):
        nonlocal user_location
        pos = None
        try:
            pos = await geo.get_current_position()
        except Exception:
            pass

        if pos is None:
            try:
                await geo.request_permission(timeout=30)
                pos = await geo.get_current_position()
            except Exception:
                pos = None

        if pos is None:
            try:
                pos = await geo.get_last_known_position()
            except Exception:
                pos = None

        if pos is not None:
            user_location = ftm.MapLatitudeLongitude(pos.latitude, pos.longitude)
            selected_points.clear()
            selected_points.append(user_location)
            show_home_page()
            if show_feedback:
                show_snack(f"My location: {pos.latitude:.5f}, {pos.longitude:.5f}")
        elif show_feedback:
            show_snack("Could not get your location.")

    def recenter_to_my_location(_):
        page.run_task(load_user_location_and_refresh_home, True)

    def app_shell(content):
        return ft.Container(
            expand=True,
            bgcolor="#D9D9D9",
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=390,
                height=844,
                bgcolor=WHITE,
                border_radius=24,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=content,
            ),
        )
    
    def find_nearest_building(lat, lon, threshold=0.00015):
        for b in buildings:
            if abs(b["lat"] - lat) < threshold and abs(b["lon"] - lon) < threshold:
                return b
        return None

    def build_header(title: str, subtitle: str | None = None, trailing=None):
        subtitle_control = (
            ft.Text(subtitle, size=12, color=MUTED) if subtitle else ft.Container(height=0)
        )

        return ft.Container(
            bgcolor=WHITE,
            padding=ft.Padding(left=18, top=18, right=18, bottom=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                title,
                                size=22,
                                weight=ft.FontWeight.W_800,
                                color=BLACK,
                            ),
                            subtitle_control,
                        ],
                    ),
                    trailing if trailing else ft.Container(width=1),
                ],
            ),
        )

    def nav_button(label: str, icon, selected: bool, on_click):
        return ft.Container(
            expand=True,
            ink=True,
            on_click=on_click,
            padding=10,
            content=ft.Column(
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon,
                        size=24,
                        color=MSU_RED if selected else BLACK,
                    ),
                    ft.Text(
                        label,
                        size=11,
                        color=MSU_RED if selected else BLACK,
                        weight=ft.FontWeight.W_700 if selected else ft.FontWeight.W_500,
                    ),
                ],
            ),
        )

    def build_bottom_nav(active: str):
        return ft.Container(
            bgcolor=WHITE,
            border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
            padding=ft.Padding(left=6, top=4, right=6, bottom=8),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    nav_button(
                        "Home",
                        ft.Icons.HOME_OUTLINED,
                        active == "home",
                        lambda e: show_home_page(),
                    ),
                    nav_button(
                        "Events",
                        ft.Icons.EVENT_OUTLINED,
                        active == "events",
                        lambda e: show_events_page(),
                    ),
                    nav_button(
                        "Settings",
                        ft.Icons.TUNE,
                        active == "settings",
                        lambda e: show_settings_page(),
                    ),
                ],
            ),
        )

    def clear_route():
        if polyline_layer_ref.current:
            polyline_layer_ref.current.polylines.clear()
        selected_points.clear()
        if user_location is not None:
            selected_points.append(user_location)

    def clear_markers():
        if marker_layer_ref.current:
            marker_layer_ref.current.markers.clear()
        selected_points.clear()
        if user_location is not None:
            selected_points.append(user_location)

    def get_tile_layer():
        return ftm.TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="red_hawk_navigator",
        )

    async def handle_map_tap(e: ftm.MapTapEvent):
        if e.name != "tap":
            
            return

        if not show_markers:
            return

        if marker_layer_ref.current is None:
            return

        marker_layer_ref.current.markers.append(
            ftm.Marker(
                coordinates=e.coordinates,
                content=ft.Icon(
                    ft.Icons.LOCATION_ON,
                    color=MSU_RED,
                    size=34,
                ),
            )
        )

        if user_location is not None and len(selected_points) == 0:
            selected_points.append(user_location)

        selected_points.append(e.coordinates)

        if len(selected_points) == 2:
            start, end = selected_points

            try:
                route_points = await get_route(start, end)

                if polyline_layer_ref.current:
                    polyline_layer_ref.current.polylines.clear()
                    polyline_layer_ref.current.polylines.append(
                        ftm.PolylineMarker(
                            coordinates=route_points,
                            color=MSU_RED,
                            stroke_width=5,
                        )
                    )
            except Exception as ex:
                show_snack(f"Routing error: {ex}")

            selected_points.clear()
            if user_location is not None:
                selected_points.append(user_location)

        page.update()

    def show_building_popup(building):
        if active_building_popup.current is None:
            return

        active_building_popup.current.content = ft.Column(
            controls=[
                ft.Text(building["name"], weight=ft.FontWeight.W_700),
                ft.Text(building["info"], size=12),
                ft.Text(f"Hours: {building['hours']}", size=11, color="gray"),
            ]
        )
        active_building_popup.current.visible = True
        page.update()

    def show_login():
        email_field = ft.TextField(
            label="Email address",
            hint_text="you@montclair.edu",
            prefix_icon=ft.Icons.MAIL_OUTLINE,
            border_radius=12,
            border_color=BORDER,
            focused_border_color=MSU_RED,
        )

        password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            border_radius=12,
            border_color=BORDER,
            focused_border_color=MSU_RED,
        )

        error_text = ft.Text("", size=12, color=MSU_RED, visible=False)

        def do_login(_):
            nonlocal current_user_email
            entered_email = (email_field.value or "").strip()
            entered_password = (password_field.value or "").strip()

            if not email_ok(entered_email):
                error_text.value = "Please enter a valid @montclair.edu email."
                error_text.visible = True
                page.update()
                return
            
            if not entered_password:
                error_text.value = "Password cannot be empty"
                error_text.visible = True
                page.update()
                return
            
            if user_auth(entered_email, entered_password):
                error_text.visible = False
                current_user_email = entered_email
                show_home_page()
                page.run_task(load_user_location_and_refresh_home, False)
            else:
                error_text.value = "invalid email or password"
                error_text.visible = True
            
            page.update()
=======
                               
            error_text.visible = False
            current_user_email = entered_email
         
            show_home_page()
>>>>>>> 3199783 (updated map Ui and building search)

        login_card = ft.Container(
            width=340,
            bgcolor=WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=20,
            padding=24,
            content=ft.Column(
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "MONTCLAIR",
                        size=30,
                        weight=ft.FontWeight.W_900,
                        color=MSU_RED,
                    ),
                    ft.Text(
                        "STATE UNIVERSITY",
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color=BLACK,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Red Hawk Navigator",
                        size=24,
                        weight=ft.FontWeight.W_800,
                        color=BLACK,
                    ),
                    ft.Text(
                        "Student project demo",
                        size=12,
                        color=MUTED,
                    ),
                    email_field,
                    password_field,
                    error_text,
                    ft.FilledButton(
                        "Sign In",
                        width=292,
                        height=48,
                        style=ft.ButtonStyle(
                            bgcolor=MSU_RED,
                            color=WHITE,
                            shape=ft.RoundedRectangleBorder(radius=12),
                        ),
                        on_click=do_login,
                    ),
                    ft.TextButton(
                        "Forgot username or password?",
                        on_click=lambda e: show_help_page(),
                    ),
                ],
            ),
        )

        content = ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[login_card],
        )

        show_screen(app_shell(content))

    def show_help_page():
        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header("Account Help", "Montclair State University"),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.Column(
                        spacing=16,
                        controls=[
                            ft.Text(
                                "Forgot username or password?",
                                size=20,
                                weight=ft.FontWeight.W_800,
                                color=BLACK,
                            ),
                            ft.Text(
                                "Please contact:\n"
                                "netidmanagement@mail.montclair.edu\n\n"
                                "Or the IT Service Desk:\n"
                                "973-655-7971",
                                size=14,
                                color=BLACK,
                            ),
                            ft.OutlinedButton(
                                "Back to Sign In",
                                on_click=lambda e: show_login(),
                            ),
                        ],
                    ),
                ),
            ],
        )

        show_screen(app_shell(body))

    def show_home_page():
        user_chip = ft.Container(
            padding=ft.Padding(left=12, top=6, right=12, bottom=6),
            border_radius=20,
            bgcolor="#F8F8F8",
            border=ft.Border.all(1, BORDER),
            content=ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.SCHOOL_OUTLINED, size=18, color=MSU_RED),
                    ft.Text("MSU", size=12, weight=ft.FontWeight.W_700, color=BLACK),
                ],
            ),
        )

        route_hint = (
            ft.Container(
                margin=ft.Margin.only(left=14, top=10, right=14, bottom=10),
                padding=12,
                border_radius=14,
                bgcolor=WHITE,
                border=ft.Border.all(1, BORDER),
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=MSU_RED, size=18),
                        ft.Text(
                            "Tap two points on campus walkways to generate a walking route.",
                            size=12,
                            color=BLACK,
                            expand=True,
                        ),
                    ],
                ),
            )
            if show_route_hint
            else ft.Container(height=0)
        )

        top_actions = ft.Container(
            padding=ft.Padding(left=14, top=10, right=14, bottom=8),
            bgcolor=WHITE,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.OutlinedButton(
                        "Clear Pins",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=lambda e: [clear_markers(), page.update()],
                    ),
                    ft.OutlinedButton(
                        "Clear Route",
                        icon=ft.Icons.ROUTE,
                        on_click=lambda e: [clear_route(), page.update()],
                    ),
                ],
            ),
        )
        building_popup = ft.Container(
            ref=active_building_popup,
            visible=False,
            bgcolor=WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=14,
            padding=12,
            right=10,
            top=10,
            width=250,
        )

        map_view = ftm.Map(
            expand=True,
            initial_center=user_location
            if user_location is not None
            else ftm.MapLatitudeLongitude(
                40.862147765671764,
                -74.1981587142951,
            ),
            initial_zoom=17,
            interaction_configuration=ftm.InteractionConfiguration(
                flags=ftm.InteractionFlag.ALL
            ),
            on_tap=handle_map_tap,
            layers=[
                get_tile_layer(),
                ftm.MarkerLayer(
                    markers=[
                        ftm.Marker(
                            coordinates=ftm.MapLatitudeLongitude(b["lat"], b["lon"]),
                            content=ft.Container(
                                width=80,
                                height=80,
                                alignment=ft.Alignment(0, 0),   # 👈 ADD THIS LINE
                                content=ft.Container(   # 👈 visible center dot                                        width=12,
                                    height=12,
                                    border_radius=6,
                                    bgcolor=MSU_RED,
                                ),
                                on_click=lambda e, b=b: show_building_popup(b),
                        ),
                    )
                for b in buildings
        ],
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
                            content=ft.Icon(
                                ft.Icons.MY_LOCATION,
                                color="#1E88E5",
                                size=30,
                            ),
                        )
                    ]
                    if user_location is not None
                    else [],
                ),
                ftm.MarkerLayer(ref=marker_layer_ref, markers=[]),
                ftm.PolylineLayer(ref=polyline_layer_ref, polylines=[]),
            ],
        )

        my_location_fab = ft.Container(
            width=44,
            height=44,
            border_radius=22,
            bgcolor=WHITE,
            border=ft.Border.all(1, BORDER),
            alignment=ft.Alignment(0, 0),
            ink=True,
            on_click=recenter_to_my_location,
            content=ft.Icon(ft.Icons.MY_LOCATION, color="#2D5E93", size=22),
        )

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header(
                    "Red Hawk Navigator",
                    "Montclair State University",
                    trailing=user_chip,
                ),
                route_hint,
                top_actions,
<<<<<<< HEAD
                ft.Container(
                    expand=True,
                    padding=ft.Padding(left=0, top=0, right=12, bottom=12),
                    content=ft.Stack(
                        expand=True,
                        controls=[
                            map_view,
                            ft.Container(
                                right=12,
                                bottom=12,
                                content=my_location_fab,
                            ),
                        ],
                    ),
=======
                ft.Stack(
                    expand=True,
                    controls=[
                        map_view,
                        building_popup,
                    ],
>>>>>>> 3199783 (updated map Ui and building search)
                ),
                build_bottom_nav("home"),
            ],
        )

        show_screen(app_shell(body))

    def show_events_page():
        def event_card(event_item: dict):
            return ft.Container(
                border_radius=18,
                bgcolor=WHITE,
                border=ft.Border.all(1, BORDER),
                padding=16,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text(
                            event_item["title"],
                            size=18,
                            weight=ft.FontWeight.W_800,
                            color=BLACK,
                        ),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.PLACE_OUTLINED, size=16, color=MSU_RED),
                                ft.Text(event_item["location"], size=13, color=BLACK),
                            ],
                        ),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=MSU_RED),
                                ft.Text(event_item["time"], size=13, color=BLACK),
                            ],
                        ),
                        ft.Text(
                            event_item["details"],
                            size=13,
                            color=MUTED,
                        ),
                    ],
                ),
            )

        add_button = ft.Container(
            width=44,
            height=44,
            border_radius=22,
            bgcolor=MSU_RED,
            alignment=ft.Alignment(0, 0),
            ink=True,
            on_click=lambda e: show_add_event_page(),
            content=ft.Icon(ft.Icons.ADD, color=WHITE),
        )

        cards = [event_card(item) for item in events_data]

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header("MSU Events", "Campus events and activities", trailing=add_button),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.ListView(spacing=16, controls=cards),
                ),
                build_bottom_nav("events"),
            ],
        )

        show_screen(app_shell(body))

    def show_add_event_page():
        title_field = ft.TextField(
            label="Event Title",
            border_radius=12,
            focused_border_color=MSU_RED,
        )
        location_field = ft.TextField(
            label="Location",
            border_radius=12,
            focused_border_color=MSU_RED,
        )
        time_field = ft.TextField(
            label="Time",
            hint_text="e.g. 3:00 PM",
            border_radius=12,
            focused_border_color=MSU_RED,
        )
        details_field = ft.TextField(
            label="Details",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_radius=12,
            focused_border_color=MSU_RED,
        )

        def save_event(_):
            title = (title_field.value or "").strip()
            location = (location_field.value or "").strip()
            time_value = (time_field.value or "").strip()
            details = (details_field.value or "").strip()

            if not title or not location or not time_value:
                show_snack("Please fill in title, location, and time.")
                return

            events_data.insert(
                0,
                {
                    "title": title,
                    "location": location,
                    "time": time_value,
                    "details": details or "No details added.",
                },
            )

            show_events_page()
            show_snack("Event added.")

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header(
                    "Add Event",
                    "Create a new MSU event",
                    trailing=ft.IconButton(
                        icon=ft.Icons.CLOSE,
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
                            time_field,
                            details_field,
                            ft.Container(height=8),
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
        map_style_dropdown = ft.Dropdown(
            label="Map Style",
            value=map_style,
            options=[
                ft.dropdown.Option("standard"),
                ft.dropdown.Option("light"),
            ],
            border_radius=12,
        )

        walking_switch = ft.Switch(value=walking_mode, active_color=MSU_RED)
        route_hint_switch = ft.Switch(value=show_route_hint, active_color=MSU_RED)
        markers_switch = ft.Switch(value=show_markers, active_color=MSU_RED)

        def setting_row(icon, title, subtitle, trailing):
            return ft.Container(
                padding=16,
                border_radius=16,
                bgcolor=WHITE,
                border=ft.Border.all(1, BORDER),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=40,
                                    height=40,
                                    border_radius=12,
                                    bgcolor="#FAFAFA",
                                    alignment=ft.Alignment(0, 0),
                                    content=ft.Icon(icon, color=MSU_RED, size=20),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(title, size=15, weight=ft.FontWeight.W_700, color=BLACK),
                                        ft.Text(subtitle, size=12, color=MUTED),
                                    ],
                                ),
                            ],
                        ),
                        trailing,
                    ],
                ),
            )

        def apply_settings(_):
            nonlocal map_style, walking_mode, show_route_hint, show_markers
            map_style = map_style_dropdown.value or "standard"
            walking_mode = walking_switch.value
            show_route_hint = route_hint_switch.value
            show_markers = markers_switch.value

            show_snack("Settings updated.")
            show_home_page()

        def sign_out(_):
            nonlocal current_user_email
            current_user_email = ""
            clear_route()
            clear_markers()
            show_login()

        body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_header("Settings", "Map preferences and app controls"),
                ft.Container(
                    expand=True,
                    padding=20,
                    content=ft.ListView(
                        spacing=14,
                        controls=[
                            setting_row(
                                ft.Icons.MAP_OUTLINED,
                                "Map Style",
                                "Choose how the campus map looks",
                                ft.Container(width=150, content=map_style_dropdown),
                            ),
                            setting_row(
                                ft.Icons.DIRECTIONS_WALK,
                                "Walking Mode",
                                "Use walking route behavior",
                                walking_switch,
                            ),
                            setting_row(
                                ft.Icons.INFO_OUTLINE,
                                "Route Instructions",
                                "Show the route hint on the home screen",
                                route_hint_switch,
                            ),
                            setting_row(
                                ft.Icons.LOCATION_ON_OUTLINED,
                                "Pins on Tap",
                                "Allow map taps to add destination pins",
                                markers_switch,
                            ),
                            ft.Container(height=6),
                            ft.FilledButton(
                                "Apply Settings",
                                height=48,
                                style=ft.ButtonStyle(
                                    bgcolor=MSU_RED,
                                    color=WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                ),
                                on_click=apply_settings,
                            ),
                            ft.OutlinedButton(
                                "Sign Out",
                                height=48,
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
