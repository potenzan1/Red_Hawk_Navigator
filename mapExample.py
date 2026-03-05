import random
import flet_map as ftm
import flet as ft


def main(page: ft.Page):
    page.title = "Montclair State University Campus Map"

    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    circle_layer_ref = ft.Ref[ftm.CircleLayer]()

    def handle_tap(e: ftm.MapTapEvent):
        if e.name == "tap":
            marker_layer_ref.current.markers.append(
                ftm.Marker(
                    content=ft.Icon(
                        ft.Icons.LOCATION_ON,
                        color=ft.CupertinoColors.DESTRUCTIVE_RED,
                    ),
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

    page.add(
        ft.Text(
            "Montclair State University Campus Map\n"
            "Click to add a Marker, right-click to add a Circle."
        ),
        ftm.Map(
            expand=True,
            initial_center=ftm.MapLatitudeLongitude(40.862147765671764, -74.1981587142951),
            initial_zoom=17,
            interaction_configuration=ftm.InteractionConfiguration(
                flags=ftm.InteractionFlag.ALL
            ),
            on_tap=handle_tap,
            on_secondary_tap=handle_tap,
            on_long_press=handle_tap,
            on_event=print,
            layers=[
                ftm.TileLayer(
                    url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    on_image_error=lambda e: print("TileLayer Error"),
                    user_agent_package_name="red-hawk-navigator",
                ),
                ftm.RichAttribution(
                    attributions=[
                        ftm.TextSourceAttribution(
                            text="OpenStreetMap Contributors",
                            on_click=lambda e: e.page.launch_url(
                                "https://www.openstreetmap.org/copyright"
                            ),
                        ),
                        ftm.TextSourceAttribution(
                            text="Flet",
                            on_click=lambda e: e.page.launch_url(
                                "https://flet.dev"
                            ),
                        ),
                    ]
                ),

                ftm.MarkerLayer(
                    ref=marker_layer_ref,
                    markers=[],
                ),

                ftm.CircleLayer(
                    ref=circle_layer_ref,
                    circles=[],
                ),
            ],
        ),
    )


ft.run(main)