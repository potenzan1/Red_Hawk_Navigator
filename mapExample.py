import random
import threading
import requests
import flet_map as ftm
import flet as ft
import flet_geolocator as ftg

CAMPUS_CENTER_LAT = 40.862147765671764
CAMPUS_CENTER_LON = -74.1981587142951

CAMPUS_SW_LAT = 40.8555
CAMPUS_SW_LON = -74.2065
CAMPUS_NE_LAT = 40.8690
CAMPUS_NE_LON = -74.1895

MIN_ZOOM = 15.0

ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImY0NDdlNWVkMDQ1MDRhNzhiMjIxNjNmYzIyZmM4YTFmIiwiaCI6Im11cm11cjY0In0="

CATEGORIES = {
    "academic":  (ft.Colors.BLUE,   ft.Icons.SCHOOL,        "Academic"),
    "dining":    (ft.Colors.ORANGE, ft.Icons.RESTAURANT,    "Dining"),
    "residence": (ft.Colors.GREEN,  ft.Icons.HOME,          "Residence"),
    "library":   (ft.Colors.PURPLE, ft.Icons.LOCAL_LIBRARY, "Library"),
    "admin":     (ft.Colors.RED,    ft.Icons.BUSINESS,      "Administrative"),
    "parking":   (ft.Colors.GREY,   ft.Icons.LOCAL_PARKING, "Parking"),
}

CAMPUS_LOCATIONS = [
    ("University Hall",              "academic",  40.8621, -74.1982, "Main academic building. Houses multiple departments including Education, Exercise Science, and the University Cafe."),
    ("Richardson Hall",              "academic",  40.8635, -74.1995, "Home to Physics & Astronomy and Chemistry & Biochemistry departments."),
    ("Dickson Hall",                 "academic",  40.8628, -74.1970, "Houses Humanities departments including English, History, Psychology, and Sociology."),
    ("Schmitt Hall",                 "academic",  40.8618, -74.1960, "Home to Philosophy, Linguistics, Modern Languages, and Applied Mathematics."),
    ("Science Hall",                 "academic",  40.8640, -74.1988, "Houses the Biology department and science labs."),
    ("Chapin Hall",                  "academic",  40.8610, -74.1975, "Home to the John J. Cali School of Music and Leshowitz Recital Hall."),
    ("Life Hall",                    "academic",  40.8605, -74.1968, "Houses the School of Communication and Media, Theatre and Dance, and the Fox Theater."),
    ("Calcia Hall",                  "academic",  40.8600, -74.1980, "Home to the Department of Art and Design. Features Gallery 3 1/2 on the 2nd floor."),
    ("CCIS",                         "academic",  40.8630, -74.1978, "Center for Computing and Information Science. Houses Computer Science and Mathematics departments."),
    ("Feliciano School of Business", "academic",  40.8615, -74.1990, "Houses all business departments. Features the Venture Cafe dining option."),
    ("CELS",                         "academic",  40.8645, -74.1975, "Center for Environmental and Life Sciences. Home to Earth and Environmental Studies."),
    ("Memorial Auditorium",          "academic",  40.8608, -74.1962, "Historic auditorium used for performances and large events."),
    ("Kasser Theater",               "academic",  40.8603, -74.1972, "Alexander Kasser Theater — home to Peak Performances. Features the George Segal Gallery."),
    ("Cole Hall",                    "admin",     40.8622, -74.1965, "Main administrative hub. Houses the President's Office, Provost, Admissions, Red Hawk Central (Registrar, Financial Aid), and Panera Bread."),
    ("Bohn Hall",                    "admin",     40.8612, -74.1958, "Houses the Office of Residence Life."),
    ("Sprague Library",              "library",   40.8625, -74.1985, "Main campus library. Features Starbucks Coffee and Cafe Diem on the 1st floor."),
    ("Student Center",               "dining",    40.8618, -74.1972, "Main student hub. Dining: Wild Blue, Social Grill, Panda Express, Java Love, The Halal Shack, Freshens, Amazon Go, 1908 Bar & Grill, The C-Store."),
    ("Freeman Dining Hall",          "dining",    40.8608, -74.1990, "Residential dining hall. Features Teaching Kitchen, Life, and Grove dining options."),
    ("Blanton Hall Dining",          "dining",    40.8632, -74.2005, "Dining: Jersey Mike's Subs, Dunkin', Chick-n-Bap, Amazon Go, Virtual Kitchen, and Sono."),
    ("Blanton Hall",                 "residence", 40.8632, -74.2005, "Residence hall with on-site dining. Also houses the Red Hawk Pantry on the 1st floor."),
    ("Bohn Hall",                    "residence", 40.8612, -74.1958, "Traditional residence hall. Home to the Office of Residence Life."),
    ("Stone Hall",                   "residence", 40.8638, -74.1960, "Residence hall located near the academic core of campus."),
    ("Sinatra Hall",                 "residence", 40.8642, -74.1968, "Residence hall named after Frank Sinatra, a New Jersey native."),
    ("Freeman Hall",                 "residence", 40.8605, -74.1995, "Residential hall connected to Freeman Dining Hall."),
    ("Russ Hall",                    "residence", 40.8617, -74.1955, "Traditional residence hall. Features Kopps Lounge on the 1st floor."),
    ("Red Hawk Parking Deck",        "parking",   40.8620, -74.2010, "Main parking structure. Houses Parking Services and the George Segal Gallery."),
]


def get_walking_route(start_lat, start_lon, end_lat, end_lon):
    url = "https://api.openrouteservice.org/v2/directions/foot-walking/geojson"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
        "instructions": False,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=10)
    resp.raise_for_status()
    coords = resp.json()["features"][0]["geometry"]["coordinates"]
    return [(lat, lon) for lon, lat in coords]


def main(page: ft.Page):
    page.title = "Montclair State University Campus Map"

    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    circle_layer_ref = ft.Ref[ftm.CircleLayer]()
    poi_layer_ref = ft.Ref[ftm.MarkerLayer]()
    route_layer_ref = ft.Ref[ftm.PolylineLayer]()
    user_marker_ref = ft.Ref[ftm.MarkerLayer]()
    map_ref = ft.Ref[ftm.Map]()

    selected_categories = {cat: True for cat in CATEGORIES}
    user_location = [None, None]

    # --- Info Panel ---
    info_name = ft.Text("", weight=ft.FontWeight.BOLD, size=14, expand=True)
    info_desc = ft.Text("", size=12, color=ft.Colors.GREY_700)
    route_btn = ft.ElevatedButton(
        "Get Directions",
        icon=ft.Icons.DIRECTIONS_WALK,
        visible=False,
    )

    def close_info():
        info_panel.visible = False
        page.update()

    info_panel = ft.Container(
        visible=False,
        bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.WHITE),
        border_radius=10,
        padding=14,
        width=270,
        right=10,
        top=10,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        info_name,
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16, on_click=lambda e: close_info()),
                    ]
                ),
                info_desc,
                route_btn,
            ],
            spacing=8,
            tight=True,
        ),
    )

    # --- Status bar ---
    status_text = ft.Text("", size=11, color=ft.Colors.BLUE_700, italic=True)
    status_bar = ft.Container(
        content=status_text,
        bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
        border_radius=6,
        padding=ft.Padding(8, 4, 8, 4),
        right=10,
        bottom=10,
        visible=False,
    )

    def show_status(msg):
        status_text.value = msg
        status_bar.visible = True
        page.update()

    def hide_status():
        status_bar.visible = False
        page.update()

    current_destination = [None, None, None]

    def show_info(name, description, dest_lat, dest_lon):
        info_name.value = name
        info_desc.value = description
        current_destination[0] = name
        current_destination[1] = dest_lat
        current_destination[2] = dest_lon
        route_btn.visible = True
        info_panel.visible = True
        page.update()

    def fetch_and_draw_route(dest_lat, dest_lon, dest_name):
        ulat, ulon = user_location
        if ulat is None:
            show_status("Location not available. Enable GPS and try again.")
            return
        show_status("Calculating route...")
        try:
            coords = get_walking_route(ulat, ulon, dest_lat, dest_lon)
            route_layer_ref.current.polylines.clear()
            route_layer_ref.current.polylines.append(
                ftm.Polyline(
                    coordinates=[ftm.MapLatitudeLongitude(lat, lon) for lat, lon in coords],
                    color=ft.Colors.BLUE,
                    stroke_width=4,
                )
            )
            page.update()
            show_status(f"Route to {dest_name} ready. Walking directions shown.")
        except Exception as ex:
            show_status(f"Could not get route: {ex}")

    def on_get_directions(e):
        dest_lat = current_destination[1]
        dest_lon = current_destination[2]
        dest_name = current_destination[0]
        if dest_lat is None:
            return
        close_info()
        threading.Thread(
            target=fetch_and_draw_route,
            args=(dest_lat, dest_lon, dest_name),
            daemon=True,
        ).start()

    route_btn.on_click = on_get_directions

    # --- Geolocator ---
    geo = ftg.Geolocator(
        on_error=lambda e: show_status(f"GPS error: {e.data}"),
    )
    page.overlay.append(geo)

    def try_get_location():
        try:
            geo.request_permission()
            p = geo.get_current_position()
            user_location[0] = p.latitude
            user_location[1] = p.longitude
            update_user_marker(p.latitude, p.longitude)
            map_ref.current.move_to(
                destination=ftm.MapLatitudeLongitude(p.latitude, p.longitude),
                zoom=17,
            )
            page.update()
        except Exception as ex:
            show_status(f"Could not get location: {ex}")
            user_location[0] = CAMPUS_CENTER_LAT
            user_location[1] = CAMPUS_CENTER_LON

    def update_user_marker(lat, lon):
        user_marker_ref.current.markers.clear()
        user_marker_ref.current.markers.append(
            ftm.Marker(
                coordinates=ftm.MapLatitudeLongitude(lat, lon),
                content=ft.Stack(
                    controls=[
                        ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.BLUE_200, size=26),
                        ft.Icon(ft.Icons.MY_LOCATION, color=ft.Colors.BLUE, size=26),
                    ]
                ),
            )
        )
        page.update()

    def handle_position_change(e: ftg.GeolocatorPositionChangeEvent):
        try:
            lat = e.latitude
            lon = e.longitude
        except AttributeError:
            return
        user_location[0] = lat
        user_location[1] = lon
        update_user_marker(lat, lon)

    geo.on_position_change = handle_position_change

    # --- POI Markers ---
    def build_poi_markers():
        markers = []
        for name, cat, lat, lon, desc in CAMPUS_LOCATIONS:
            if not selected_categories.get(cat, True):
                continue
            color, icon, _ = CATEGORIES[cat]

            def make_click(n, d, la, lo):
                def on_click(e):
                    show_info(n, d, la, lo)
                return on_click

            markers.append(
                ftm.Marker(
                    coordinates=ftm.MapLatitudeLongitude(lat, lon),
                    content=ft.IconButton(
                        icon=icon,
                        icon_color=color,
                        icon_size=22,
                        tooltip=name,
                        on_click=make_click(name, desc, lat, lon),
                        style=ft.ButtonStyle(padding=ft.Padding(0, 0, 0, 0)),
                    ),
                )
            )
        return markers

    def refresh_poi():
        poi_layer_ref.current.markers.clear()
        poi_layer_ref.current.markers.extend(build_poi_markers())
        page.update()

    # --- Map position constraint (disabled - open map) ---
    # def handle_map_position_change(e: ftm.MapPositionChangeEvent):
    #     lat = e.coordinates.latitude
    #     lon = e.coordinates.longitude
    #     clamped_lat = max(CAMPUS_SW_LAT, min(CAMPUS_NE_LAT, lat))
    #     clamped_lon = max(CAMPUS_SW_LON, min(CAMPUS_NE_LON, lon))
    #     if lat != clamped_lat or lon != clamped_lon:
    #         map_ref.current.move_to(
    #             destination=ftm.MapLatitudeLongitude(clamped_lat, clamped_lon),
    #         )
    #         page.update()
    def handle_map_position_change(e: ftm.MapPositionChangeEvent):
        pass

    def handle_tap(e: ftm.MapTapEvent):
        if e.name == "tap":
            marker_layer_ref.current.markers.append(
                ftm.Marker(
                    content=ft.Icon(ft.Icons.LOCATION_ON, color=ft.CupertinoColors.DESTRUCTIVE_RED),
                    coordinates=e.coordinates,
                )
            )
        elif e.name == "secondary_tap":
            circle_layer_ref.current.circles.append(
                ftm.CircleMarker(
                    radius=random.randint(5, 10),
                    coordinates=e.coordinates,
                    color=ft.Colors.random(),
                    border_color=ft.Colors.random(),
                    border_stroke_width=4,
                )
            )
        page.update()

    # --- Legend ---
    def make_legend_toggle(cat_key):
        color, icon, label = CATEGORIES[cat_key]

        def on_toggle(e):
            selected_categories[cat_key] = e.control.value
            refresh_poi()

        return ft.Row(
            controls=[
                ft.Checkbox(value=True, on_change=on_toggle),
                ft.Icon(icon, color=color, size=16),
                ft.Text(label, size=12),
            ],
            spacing=4,
        )

    legend = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Legend", weight=ft.FontWeight.BOLD, size=13),
                *[make_legend_toggle(k) for k in CATEGORIES],
            ],
            spacing=4,
            tight=True,
        ),
        bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.WHITE),
        border_radius=8,
        padding=10,
        left=10,
        bottom=10,
    )

    # --- Locate button ---
    def handle_locate(e):
        threading.Thread(target=try_get_location, daemon=True).start()

    locate_btn = ft.Container(
        content=ft.FloatingActionButton(
            icon=ft.Icons.MY_LOCATION,
            tooltip="Go to my location",
            on_click=handle_locate,
            bgcolor=ft.Colors.WHITE,
            foreground_color=ft.Colors.BLUE,
        ),
        right=16,
        bottom=60,
    )

    # --- Clear route button ---
    def clear_route(e):
        route_layer_ref.current.polylines.clear()
        hide_status()
        page.update()

    clear_btn = ft.Container(
        content=ft.FloatingActionButton(
            icon=ft.Icons.CLEAR,
            tooltip="Clear route",
            on_click=clear_route,
            bgcolor=ft.Colors.WHITE,
            foreground_color=ft.Colors.RED,
        ),
        right=16,
        bottom=120,
    )

    page.add(
        ft.Stack(
            expand=True,
            controls=[
                ftm.Map(
                    ref=map_ref,
                    expand=True,
                    initial_center=ftm.MapLatitudeLongitude(CAMPUS_CENTER_LAT, CAMPUS_CENTER_LON),
                    initial_zoom=17,
                    # min_zoom=MIN_ZOOM,
                    on_tap=handle_tap,
                    on_secondary_tap=handle_tap,
                    on_long_press=handle_tap,
                    on_position_change=handle_map_position_change,
                    layers=[
                        ftm.TileLayer(
                            url_template="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
                            on_image_error=lambda e: print("TileLayer Error"),
                        ),
                        ftm.RichAttribution(
                            attributions=[
                                ftm.TextSourceAttribution(
                                    text="OpenStreetMap Contributors",
                                    on_click=lambda e: e.page.launch_url(
                                        "https://www.openstreetmap.org/copyright"
                                    ),
                                ),
                            ]
                        ),
                        ftm.PolylineLayer(ref=route_layer_ref, polylines=[]),
                        ftm.MarkerLayer(ref=marker_layer_ref, markers=[]),
                        ftm.CircleLayer(ref=circle_layer_ref, circles=[]),
                        ftm.MarkerLayer(ref=poi_layer_ref, markers=build_poi_markers()),
                        ftm.MarkerLayer(ref=user_marker_ref, markers=[]),
                    ],
                ),
                legend,
                info_panel,
                locate_btn,
                clear_btn,
                status_bar,
            ],
        )
    )

    threading.Thread(target=try_get_location, daemon=True).start()


ft.app(main)