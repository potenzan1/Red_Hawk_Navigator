import flet as ft
import flet_map as ftm
import flet_geolocator as ftg
import httpx

GRAPH_HOPPER_API_KEY = "3e19284a-10f0-424f-9add-57bd72967758"
CAMPUS_CENTER = ftm.MapLatitudeLongitude(40.862147765671764, -74.1981587142951)

def _format_distance(meters):
    if not meters or meters < 0: return ""
    return f"{meters/1000:.1f} km" if meters >= 1000 else f"{int(round(meters))} m"

def _format_time(ms):
    if not ms or ms < 0: return ""
    sec = ms // 1000
    return f"{sec // 60} min" if sec >= 60 else f"{sec} sec"

async def get_route(start, end):
    url = "https://graphhopper.com/api/1/route"
    params = {
        "point": [f"{start.latitude},{start.longitude}", f"{end.latitude},{end.longitude}"],
        "profile": "foot", "locale": "en", "points_encoded": "false",
        "key": GRAPH_HOPPER_API_KEY, "calc_points": "true", "instructions": "true",
    }
    async with httpx.AsyncClient() as client:
        data = (await client.get(url, params=params)).json()
    
    path = data["paths"][0]
    coords = path["points"]["coordinates"]
    route_points = [ftm.MapLatitudeLongitude(lat, lon) for lon, lat in coords]
    return route_points, path.get("instructions") or [], path.get("distance"), path.get("time")

async def main(page: ft.Page):
    page.title = "Montclair State University Walking Router"
    
    marker_layer, polyline_layer, instructions_col = ft.Ref(), ft.Ref(), ft.Ref()
    current_location = None
    destination = None
    
    geo = ftg.Geolocator(
        location_settings=ftg.GeolocatorSettings(
            accuracy=ftg.GeolocatorPositionAccuracy.BEST_FOR_NAVIGATION
        )
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
        except Exception as ex:
            print("Location error:", ex)
            current_location = CAMPUS_CENTER
        
        # Update markers after location is set
        markers = []
        if current_location:
            markers.append(ftm.Marker(content=ft.Icon(ft.Icons.MY_LOCATION, color=ft.Colors.GREEN), coordinates=current_location))
        if destination:
            markers.append(ftm.Marker(content=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.RED), coordinates=destination))
        marker_layer.current.markers = markers
        page.update()

    def show_instructions(instructions, total_dist, total_time_ms):
        col = instructions_col.current
        col.controls.clear()
        col.controls.append(ft.Text("Turn-by-turn", weight=ft.FontWeight.BOLD, size=16))
        
        parts = [p for p in [_format_distance(total_dist), _format_time(total_time_ms)] if p]
        if parts:
            col.controls.append(ft.Text(f"Total: {' · '.join(parts)}", size=12, color=ft.Colors.GREY_700))
        
        col.controls.append(ft.Divider(height=1))
        for i, instr in enumerate(instructions, 1):
            text = instr.get("text", "")
            dist = instr.get("distance")
            dist_str = f" — {_format_distance(dist)}" if dist else ""
            col.controls.append(ft.Row([
                ft.Container(content=ft.Text(str(i), size=12, color=ft.Colors.WHITE),
                           bgcolor=ft.Colors.BLUE, border_radius=10, padding=ft.padding.symmetric(4, 8)),
                ft.Expanded(child=ft.Text(text + dist_str, size=13, no_wrap=False))
            ], spacing=8, wrap=True))
        
        if not instructions:
            col.controls.append(ft.Text("No turn instructions for this route.", italic=True, color=ft.Colors.GREY_600))
        page.update()

    async def handle_tap(e: ftm.MapTapEvent):
        if e.name != "tap": return
        nonlocal destination, current_location
        destination = e.coordinates
        
        # Try to get fresh location
        try:
            p = await geo.get_current_position_async(
                accuracy=ftg.GeolocatorPositionAccuracy.BEST_FOR_NAVIGATION,
                wait_timeout=15,
            )
            if p and p.latitude is not None and p.longitude is not None:
                current_location = ftm.MapLatitudeLongitude(p.latitude, p.longitude)
        except Exception:
            pass
        
        # Update markers
        markers = []
        if current_location:
            markers.append(ftm.Marker(content=ft.Icon(ft.Icons.MY_LOCATION, color=ft.Colors.GREEN), coordinates=current_location))
        if destination:
            markers.append(ftm.Marker(content=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.RED), coordinates=destination))
        marker_layer.current.markers = markers
        
        try:
            route_points, instructions, total_dist, total_time_ms = await get_route(
                current_location or CAMPUS_CENTER, destination
            )
            polyline_layer.current.polylines = [
                ftm.PolylineMarker(coordinates=route_points, color=ft.Colors.BLUE, stroke_width=6)
            ]
            show_instructions(instructions, total_dist, total_time_ms)
        except Exception as ex:
            print("Routing error:", ex)
            show_instructions([], None, None)
        page.update()

    instructions_panel = ft.Container(
        content=ft.Column(ref=instructions_col, scroll=ft.ScrollMode.AUTO, expand=True, spacing=6,
                         controls=[ft.Text("Tap a point to get a walking route from your location.", size=12, color=ft.Colors.GREY_700)]),
        padding=12, border=ft.border.all(1, ft.Colors.GREY_400), border_radius=8,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, width=280
    )

    page.add(ft.Row([
        ft.Column([
            ft.Text("Tap a point on the map to get a walking route from your location."),
            ftm.Map(expand=True, initial_center=CAMPUS_CENTER, initial_zoom=17,
                   interaction_configuration=ftm.MapInteractionConfiguration(flags=ftm.MapInteractiveFlag.ALL),
                   on_tap=handle_tap,
                   layers=[
                       ftm.TileLayer(url_template="https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"),
                       ftm.RichAttribution(attributions=[
                           ftm.TextSourceAttribution(text=t) for t in ["© CARTO", "OpenStreetMap Contributors", "GraphHopper", "Flet"]
                       ]),
                       ftm.MarkerLayer(ref=marker_layer, markers=[]),
                       ftm.PolylineLayer(ref=polyline_layer, polylines=[]),
                   ])
        ], expand=True),
        instructions_panel
    ], expand=True, spacing=12))

    await try_get_user_location()

ft.app(target=main)