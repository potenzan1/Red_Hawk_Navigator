import flet as ft
import flet_map as ftm
import flet_geolocator as ftg
import httpx

GRAPH_HOPPER_API_KEY = "3e19284a-10f0-424f-9add-57bd72967758"
CAMPUS_CENTER = ftm.MapLatitudeLongitude(40.862147765671764, -74.1981587142951)

def _format_distance(meters):
    if meters is None or meters < 0:
        return ""
    if meters >= 1000:
        return f"{meters / 1000:.1f} km"
    return f"{int(round(meters))} m"

def _format_time(ms):
    if ms is None or ms < 0:
        return ""
    sec = ms // 1000
    if sec >= 60:
        return f"{sec // 60} min"
    return f"{sec} sec"

async def get_route(start, end):
    """Returns (route_points, instructions, total_distance_m, total_time_ms)."""
    url = "https://graphhopper.com/api/1/route"
    params = {
        "point": [f"{start.latitude},{start.longitude}", f"{end.latitude},{end.longitude}"],
        "profile": "foot",
        "locale": "en",
        "points_encoded": "false",
        "key": GRAPH_HOPPER_API_KEY,
        "calc_points": "true",
        "instructions": "true",
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    path = data["paths"][0]
    coords = path["points"]["coordinates"]
    route_points = [ftm.MapLatitudeLongitude(lat, lon) for lon, lat in coords]
    instructions = path.get("instructions") or []
    dist = path.get("distance")
    time_ms = path.get("time")
    return route_points, instructions, dist, time_ms

def update_markers(marker_layer, current_location, destination):
    """Show green 'you are here' marker and red destination marker."""
    markers = []
    if current_location:
        markers.append(
            ftm.Marker(
                content=ft.Icon(ft.Icons.MY_LOCATION, color=ft.Colors.GREEN),
                coordinates=current_location,
            )
        )
    if destination:
        markers.append(
            ftm.Marker(
                content=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.RED),
                coordinates=destination,
            )
        )
    marker_layer.markers = markers

async def main(page: ft.Page):
    page.title = "Montclair State University Walking Router"

    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    polyline_layer_ref = ft.Ref[ftm.PolylineLayer]()
    instructions_column_ref = ft.Ref[ft.Column]()

    current_location = None
    destination = None

    geo = ftg.Geolocator(
        location_settings=ftg.GeolocatorSettings(
            accuracy=ftg.GeolocatorPositionAccuracy.BEST_FOR_NAVIGATION,
        ),
    )
    page.overlay.append(geo)

    async def try_get_user_location():
        nonlocal current_location
        try:
            await geo.request_permission(timeout=10)
            p = await geo.get_current_position_async(
                accuracy=ftg.GeolocatorPositionAccuracy.BEST_FOR_NAVIGATION,
                wait_timeout=35,
            )
            if p and p.latitude is not None and p.longitude is not None:
                current_location = ftm.MapLatitudeLongitude(p.latitude, p.longitude)
                update_markers(marker_layer_ref.current, current_location, destination)
                page.update()
        except Exception as ex:
            print("Location error:", ex)
            current_location = CAMPUS_CENTER
            update_markers(marker_layer_ref.current, current_location, destination)
            page.update()

    def show_instructions(instructions, total_dist, total_time_ms):
        """Update the instructions panel with turn-by-turn steps."""
        col = instructions_column_ref.current
        if not col:
            return
        col.controls.clear()
        col.controls.append(
            ft.Text("Turn-by-turn", weight=ft.FontWeight.BOLD, size=16),
        )
        if total_dist is not None or total_time_ms is not None:
            parts = []
            if total_dist is not None:
                parts.append(_format_distance(total_dist))
            if total_time_ms is not None:
                parts.append(_format_time(total_time_ms))
            col.controls.append(ft.Text(f"Total: {' · '.join(parts)}", size=12, color=ft.Colors.GREY_700))
        col.controls.append(ft.Divider(height=1))
        for i, instr in enumerate(instructions, 1):
            text = instr.get("text") or ""
            dist = instr.get("distance")
            dist_str = f" — {_format_distance(dist)}" if dist is not None else ""
            col.controls.append(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(str(i), size=12, color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.BLUE,
                            border_radius=10,
                            padding=ft.padding.symmetric(4, 8),
                            alignment=ft.alignment.center,
                        ),
                        ft.Expanded(
                            child=ft.Text(text + dist_str, size=13, no_wrap=False),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                )
            )
        if not instructions:
            col.controls.append(ft.Text("No turn instructions for this route.", italic=True, color=ft.Colors.GREY_600))
        page.update()

    async def handle_tap(e: ftm.MapTapEvent):
        if e.name != "tap":
            return
        nonlocal destination, current_location
        destination = e.coordinates
        # Optional: refetch position for a fresher start when routing
        try:
            p = await geo.get_current_position_async(
                accuracy=ftg.GeolocatorPositionAccuracy.BEST_FOR_NAVIGATION,
                wait_timeout=15,
            )
            if p and p.latitude is not None and p.longitude is not None:
                current_location = ftm.MapLatitudeLongitude(p.latitude, p.longitude)
        except Exception:
            pass
        start = current_location if current_location else CAMPUS_CENTER
        update_markers(marker_layer_ref.current, current_location, destination)

        try:
            route_points, instructions, total_dist, total_time_ms = await get_route(start, destination)
            polyline_layer_ref.current.polylines.clear()
            polyline_layer_ref.current.polylines.append(
                ftm.PolylineMarker(
                    coordinates=route_points,
                    color=ft.Colors.BLUE,
                    stroke_width=6,
                )
            )
            show_instructions(instructions, total_dist, total_time_ms)
        except Exception as ex:
            print("Routing error:", ex)
            show_instructions([], None, None)

        page.update()

    instructions_panel = ft.Container(
        content=ft.Column(
            ref=instructions_column_ref,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=6,
            controls=[
                ft.Text("Tap a point to get a walking route from your location.", size=12, color=ft.Colors.GREY_700),
            ],
        ),
        padding=12,
        border=ft.border.all(1, ft.Colors.GREY_400),
        border_radius=8,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        width=280,
    )

    page.add(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            "Tap a point on the map to get a walking route from your location."
                        ),
                        ftm.Map(
                            expand=True,
                            initial_center=ftm.MapLatitudeLongitude(
                                40.862147765671764, -74.1981587142951
                            ),
                            initial_zoom=17,
                            interaction_configuration=ftm.MapInteractionConfiguration(
                                flags=ftm.MapInteractiveFlag.ALL
                            ),
                            on_tap=handle_tap,
                            layers=[
                                ftm.TileLayer(
                                    url_template="https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
                                ),
                                ftm.RichAttribution(
                                    attributions=[
                                        ftm.TextSourceAttribution(text="© CARTO"),
                                        ftm.TextSourceAttribution(text="OpenStreetMap Contributors"),
                                        ftm.TextSourceAttribution(text="GraphHopper"),
                                        ftm.TextSourceAttribution(text="Flet"),
                                    ]
                                ),
                                ftm.MarkerLayer(ref=marker_layer_ref, markers=[]),
                                ftm.PolylineLayer(ref=polyline_layer_ref, polylines=[]),
                            ],
                        ),
                    ],
                    expand=True,
                ),
                instructions_panel,
            ],
            expand=True,
            spacing=12,
        ),
    )
    await try_get_user_location()

ft.app(target=main)