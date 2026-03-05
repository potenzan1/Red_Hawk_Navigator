import flet as ft
import flet_map as ftm
import httpx

GRAPH_HOPPER_API_KEY = "3e19284a-10f0-424f-9add-57bd72967758"

async def get_route(start, end):
    url = "https://graphhopper.com/api/1/route"
    params = {
        "point": [f"{start.latitude},{start.longitude}", f"{end.latitude},{end.longitude}"],
        "profile": "foot",
        "locale": "en",
        "points_encoded": "false",
        "key": GRAPH_HOPPER_API_KEY,
        "calc_points": "true"
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    coords = data["paths"][0]["points"]["coordinates"]
    return [ftm.MapLatitudeLongitude(lat, lon) for lon, lat in coords]

async def main(page: ft.Page):
    page.title = "Red Hawk Navigator"

    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    polyline_layer_ref = ft.Ref[ftm.PolylineLayer]()

    selected_points = []

    async def handle_tap(e: ftm.MapTapEvent):
        if e.name == "tap":
            marker_layer_ref.current.markers.append(
                ftm.Marker(
                    content=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.RED),
                    coordinates=e.coordinates,
                )
            )

            selected_points.append(e.coordinates)

            if len(selected_points) == 2:
                start, end = selected_points

                try:
                    route_points = await get_route(start, end)

                    polyline_layer_ref.current.polylines.clear()
                    polyline_layer_ref.current.polylines.append(
                        ftm.PolylineMarker(
                            coordinates=route_points,
                            color=ft.Colors.BLUE,
                            stroke_width=6,
                        )
                    )

                except Exception as ex:
                    print("Routing error:", ex)
                selected_points.clear()

            page.update()

    page.add(
        ft.Text(
            "Click two points on campus walkways to generate a walking route."
        ),
        ftm.Map(
            expand=True,
            initial_center=ftm.MapLatitudeLongitude(
                40.862147765671764, -74.1981587142951
            ),
            initial_zoom=17,
            interaction_configuration=ftm.InteractionConfiguration(
                flags=ftm.InteractionFlag.ALL
            ),
            on_tap=handle_tap,
            layers=[
                ftm.TileLayer(
                    url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    user_agent_package_name="Red_Hawk_Navigator",
                ),
                ftm.RichAttribution(
                    attributions=[
                        ftm.TextSourceAttribution(text="OpenStreetMap Contributors"),
                        ftm.TextSourceAttribution(text="GraphHopper"),
                        ftm.TextSourceAttribution(text="Flet"),
                    ]
                ),
                ftm.MarkerLayer(
                    ref=marker_layer_ref, 
                    markers=[]
                    ),

                ftm.PolylineLayer(
                    ref=polyline_layer_ref, 
                    polylines=[]
                    ),

                ftm.PolygonLayer(
                    polygons=[
                        ftm.PolygonMarker(
                            coordinates=[
                                ftm.MapLatitudeLongitude(40.862223, -74.197025),
                                ftm.MapLatitudeLongitude(40.861815, -74.197181),
                                ftm.MapLatitudeLongitude(40.861702, -74.196883),
                                ftm.MapLatitudeLongitude(40.862124, -74.196642),
                            ],
                            color=ft.Colors.with_opacity(0.4, ft.Colors.BLUE),
                            border_color=ft.Colors.BLUE,
                            border_stroke_width=3,
                            label="Center for Computing and Information Science"
                        )
                    ]
                ),
            ],
        ),
    )

ft.run(main)