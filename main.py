import flet as ft

MSU_DOMAIN = "@montclair.edu"

# -------- NEW: Building Data --------
buildings_data = [
    {
        "name": "University Hall",
        "hours": "8:00 AM - 10:00 PM",
        "description": "Main academic building with classrooms and offices.",
    },
    {
        "name": "Student Center",
        "hours": "7:00 AM - 11:00 PM",
        "description": "Dining, lounges, and student services.",
    },
    {
        "name": "Sprague Library",
        "hours": "8:00 AM - 12:00 AM",
        "description": "Main campus library with study spaces.",
    },
]


def main(page: ft.Page):
    # ---- Mobile app window ----
    page.title = "Red Hawk Navigator"
    page.window_width = 390
    page.window_height = 844
    page.window_resizable = False
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    # ---- Colors ----
    bg = "#F6F2EC"
    card_bg = "#FFFFFF"
    border = "#E6E0D8"
    msu_red = "#C8102E"
    text_muted = "#555555"

    page.bgcolor = bg

    # Main container we swap
    main_area = ft.Container(expand=True)

    # -------- Helpers --------
    def email_ok(v: str) -> bool:
        v = (v or "").strip().lower()
        return v.endswith(MSU_DOMAIN) and len(v) > len(MSU_DOMAIN)

    def snack(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def app_header(title: str, subtitle: str | None = None):
        return ft.Container(
            bgcolor=bg,
            padding=ft.Padding(left=18, right=18, top=16, bottom=10),
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Text(title, size=22, weight=ft.FontWeight.W_800, color="#111111"),
                    ft.Text(subtitle, size=12, color=text_muted) if subtitle else ft.Container(),
                ],
            ),
        )

    def centered_card(content_controls):
        card = ft.Container(
            width=360,
            bgcolor=card_bg,
            border=ft.border.all(1, border),
            border_radius=18,
            padding=20,
            content=ft.Column(spacing=14, controls=content_controls),
        )
        return ft.Container(
            bgcolor=bg,
            padding=ft.Padding(left=18, right=18, top=8, bottom=18),
            content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[card]),
        )

    def show_screen(header_control, body_control):
        main_area.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header_control,
                ft.Container(expand=True, content=ft.ListView(expand=True, spacing=0, controls=[body_control])),
            ],
        )
        page.update()

    # -------- NEW: Buildings Page --------
    def show_buildings_page(user_email: str):
        def back(_):
            show_dashboard(user_email)

        header = app_header("Campus Buildings", f"Signed in as: {user_email}")

        def building_card(b):
            return ft.Container(
                bgcolor=card_bg,
                border=ft.border.all(1, border),
                border_radius=16,
                padding=14,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text(b["name"], size=16, weight=ft.FontWeight.W_800),
                        ft.Text(f"Hours: {b['hours']}", size=12, color=text_muted),
                        ft.Text(b["description"], size=12),
                    ],
                ),
            )

        cards = [building_card(b) for b in buildings_data]

        body_ui = centered_card(
            cards + [
                ft.Divider(height=8, color="transparent"),
                ft.OutlinedButton("Back to Dashboard", on_click=back),
            ]
        )

        show_screen(header, body_ui)

    # -------- Feature page template --------
    def show_feature_page(user_email: str, title: str, body: str):
        def back(_):
            show_dashboard(user_email)

        header = app_header("Red Hawk Navigator", f"Signed in as: {user_email}")

        body_ui = centered_card(
            [
                ft.Text(title, size=18, weight=ft.FontWeight.W_800),
                ft.Text(body, size=13, color="#222222"),
                ft.Divider(height=8, color="transparent"),
                ft.OutlinedButton("Back to Dashboard", on_click=back),
            ]
        )
        show_screen(header, body_ui)

    # -------- Help page --------
    def show_help():
        def back(_):
            show_login()

        header = app_header("Red Hawk Navigator", "Account help")

        body_ui = centered_card(
            [
                ft.Text("Forgot username or password?", size=18, weight=ft.FontWeight.W_800),
                ft.Text(
                    "Please contact:\n"
                    "netidmanagement@mail.montclair.edu\n\n"
                    "or the IT Service Desk at:\n"
                    "973-655-7971",
                    size=13,
                    color="#222222",
                ),
                ft.Divider(height=8, color="transparent"),
                ft.OutlinedButton("Back to Sign In", on_click=back),
            ]
        )
        show_screen(header, body_ui)

    # -------- Dashboard --------
    def show_dashboard(user_email: str):
        def sign_out(_):
            show_login()

        header = app_header("Red Hawk Navigator", f"Signed in as: {user_email}")

        def tile(title: str, subtitle: str, icon, on_open):
            return ft.Container(
                bgcolor=card_bg,
                border=ft.border.all(1, border),
                border_radius=16,
                padding=14,
                ink=True,
                on_click=lambda e: on_open(),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(title, size=15, weight=ft.FontWeight.W_800, color="#111111"),
                                ft.Text(subtitle, size=12, color=text_muted),
                            ],
                        ),
                        ft.Icon(icon, size=22, color=msu_red),
                    ],
                ),
            )

        dashboard_card = ft.Container(
            width=360,
            bgcolor=bg,
            content=ft.Column(
                spacing=12,
                controls=[
                    tile(
                        "Campus Map",
                        "Locate buildings and routes",
                        ft.Icons.MAP_OUTLINED,
                        lambda: show_feature_page(
                            user_email,
                            "Campus Map",
                            "This is the Campus Map placeholder.\n\n"
                            "Next step (future milestone): embed an interactive map and add markers for campus buildings.",
                        ),
                    ),
                    tile(
                        "Building Information",
                        "Hours, offices, and departments",
                        ft.Icons.APARTMENT_OUTLINED,
                        lambda: show_buildings_page(user_email),
                    ),
                    tile(
                        "Events",
                        "View and share campus events",
                        ft.Icons.EVENT_OUTLINED,
                        lambda: show_feature_page(
                            user_email,
                            "Events",
                            "This is the Events placeholder.\n\n"
                            "Next step: show a list of events and allow users to submit an event (demo form).",
                        ),
                    ),
                    tile(
                        "Resources",
                        "Helpful campus links",
                        ft.Icons.LINK_OUTLINED,
                        lambda: show_feature_page(
                            user_email,
                            "Resources",
                            "This is the Resources placeholder.\n\n"
                            "Next step: add quick links like IT Desk, Library, Canvas, Academic Calendar, etc.",
                        ),
                    ),
                    ft.Divider(height=6, color="transparent"),
                    ft.OutlinedButton("Sign Out", on_click=sign_out),
                ],
            ),
        )

        body_ui = ft.Container(
            bgcolor=bg,
            padding=ft.Padding(left=18, right=18, top=8, bottom=18),
            content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[dashboard_card]),
        )

        show_screen(header, body_ui)

    # -------- Login --------
    def show_login():
        header = app_header("Red Hawk Navigator", "Student project demo — not an official MSU login.")

        branding = ft.Column(
            spacing=2,
            controls=[
                ft.Text("MONTCLAIR", size=30, weight=ft.FontWeight.W_900, color=msu_red),
                ft.Text("STATE UNIVERSITY", size=14, weight=ft.FontWeight.W_700, color=msu_red),
            ],
        )

        email = ft.TextField(
            label="Email address",
            hint_text="you@montclair.edu",
            prefix_icon=ft.Icons.MAIL_OUTLINE,
            keyboard_type=ft.KeyboardType.EMAIL,
            border_color=border,
            focused_border_color=msu_red,
            autocorrect=False,
        )

        password = ft.TextField(
            label="Password (optional)",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            border_color=border,
            focused_border_color=msu_red,
        )

        email_error = ft.Text("", size=11, color="red", visible=False)

        def on_sign_in(_):
            v = (email.value or "").strip().lower()

            if not email_ok(v):
                email_error.value = "Please enter a valid @montclair.edu email to continue."
                email_error.visible = True
                page.update()
                return

            email_error.visible = False
            show_dashboard(email.value.strip())

        forgot = ft.TextButton("Forgot username or password?", on_click=lambda e: show_help())

        sign_in = ft.ElevatedButton(
            "Sign In",
            width=float("inf"),
            on_click=on_sign_in,
            style=ft.ButtonStyle(
                padding=16,
                shape=ft.RoundedRectangleBorder(radius=12),
                elevation=0,
                bgcolor={ft.ControlState.DEFAULT: "#EAE6E0"},
                color={ft.ControlState.DEFAULT: "#6B6B6B"},
            ),
        )

        body_ui = centered_card(
            [
                branding,
                ft.Text("Sign In", size=24, weight=ft.FontWeight.W_900),
                ft.Text("Use your @montclair.edu email to continue.", size=12, color=text_muted),
                email,
                email_error,
                password,
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[forgot]),
                sign_in,
            ]
        )

        show_screen(header, body_ui)

    page.add(main_area)
    show_login()


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)