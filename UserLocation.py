import flet as ft
import flet_map as ftm
import flet_geolocator as ftg


async def main(page: ft.Page):
    page.title = "Map + Geolocator"
    page.padding = 0
    page.spacing = 0

    user_location = None
    marker_layer_ref = ft.Ref[ftm.MarkerLayer]()
    map_container = ft.Container(expand=True)
    status_text = ft.Text("Ready", size=12, color=ft.Colors.GREY_700)
    map_refresh_token = 0

    def show_snack(msg: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def build_map():
        return ftm.Map(
            key=f"map-{map_refresh_token}",
            expand=True,
            initial_center=user_location
            if user_location is not None
            else ftm.MapLatitudeLongitude(40.862147765671764, -74.1981587142951),
            initial_zoom=18 if user_location is not None else 16,
            interaction_configuration=ftm.InteractionConfiguration(
                flags=ftm.InteractionFlag.ALL
            ),
            layers=[
                ftm.TileLayer(
                    url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    user_agent_package_name="red_hawk_navigator",
                ),
                ftm.RichAttribution(
                    attributions=[
                        ftm.TextSourceAttribution(text="OpenStreetMap Contributors"),
                        ftm.TextSourceAttribution(text="Flet"),
                    ]
                ),
                ftm.MarkerLayer(
                    ref=marker_layer_ref,
                    markers=[
                        ftm.Marker(
                            coordinates=user_location,
                            content=ft.Icon(ft.Icons.MY_LOCATION, color="#1E88E5", size=30),
                        )
                    ]
                    if user_location is not None
                    else [],
                ),
            ],
        )

    def refresh_map():
        nonlocal map_refresh_token
        map_refresh_token += 1
        map_container.content = build_map()
        page.update()

    async def locate_me():
        nonlocal user_location
        pos = None
        status_text.value = "Locating..."
        page.update()

        try:
            # Same working flow as Map+UI_V1.py
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

        if pos is None:
            show_snack("Could not get your location.")
            status_text.value = "Location not available."
            page.update()
            return

        user_location = ftm.MapLatitudeLongitude(pos.latitude, pos.longitude)
        refresh_map()
        show_snack(f"Located: {pos.latitude:.5f}, {pos.longitude:.5f}")
        status_text.value = f"Located: {pos.latitude:.5f}, {pos.longitude:.5f}"
        page.update()

    def on_my_location_click(_):
        show_snack("Locating...")
        page.run_task(locate_me)

    def handle_geo_error(e):
        show_snack(f"Location error: {e.data}")

    geo = ftg.Geolocator(
        configuration=ftg.GeolocatorConfiguration(
            accuracy=ftg.GeolocatorPositionAccuracy.BEST
        ),
        on_error=handle_geo_error,
    )

    map_container.content = build_map()

    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(
                    padding=10,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Geolocator Map", size=18, weight=ft.FontWeight.BOLD),
                            ft.FilledButton(
                                "My Location",
                                icon=ft.Icons.MY_LOCATION,
                                on_click=on_my_location_click,
                            ),
                        ],
                    ),
                ),
                ft.Container(padding=ft.padding.only(left=10, right=10), content=status_text),
                map_container,
            ],
        )
    )

    page.services.append(geo)


if __name__ == "__main__":
    ft.run(main)