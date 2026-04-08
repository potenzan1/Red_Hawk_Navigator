import flet as ft
import mysql.connector


db = mysql.connector.connect(
    host="localhost",
    user="MSU_Admin",
    password="MSU",
    database="red_hawk_navigation"
)

cursor = db.cursor()

def main(page: ft.Page):
    page.title = "MSU Event Admin View"

    title_field = ft.TextField(
        label="Event Title",
        label_style=ft.TextStyle(color=ft.Colors.GREY_200),
    )
    
    location_field = ft.TextField(
        label="Event Location",
        label_style=ft.TextStyle(color=ft.Colors.GREY_200),
    )

    description_field = ft.TextField(
        label="Description",
        multiline=True,
        label_style=ft.TextStyle(color=ft.Colors.GREY_200),
    )

    date_field = ft.TextField(
        label="Event Date (YYYY-MM-DD)",
        label_style=ft.TextStyle(color=ft.Colors.GREY_200),
    )

    time_field = ft.TextField(
        label="Event time (HH:MM:SS)",
        label_style=ft.TextStyle(color=ft.Colors.GREY_200),
    )

    email_field = ft.TextField(
        label="User's Email",
        label_style=ft.TextStyle(color=ft.Colors.GREY_200),
    )
    password_field = ft.TextField(
        label="User's Password",
        label_style=ft.TextStyle(color=ft.Colors.GREY_200),
    )
    role_field = ft.Switch(
        label="User's role (0 is student, 1 is faculty)",
    )

    def submit_event(e):
        title = title_field.value
        location = location_field.value
        description = description_field.value
        date = date_field.value
        time = time_field.value

        try:
            sql = """
                INSERT INTO event (title, location, time, date, description)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (title, location, time, date, description)

            cursor.execute(sql, values)
            db.commit()

            page.show_dialog(ft.SnackBar(ft.Text("Event added successfully!")))

            title_field.value = ""
            location_field.value = ""
            description_field.value = ""
            date_field.value = ""
            time_field.value = ""

        except Exception as err:
            page.show_dialog(ft.SnackBar(ft.Text(f"Error: {err}")))

    def submit_user(e):
        email = email_field.value
        password = password_field.value
        role = role_field.value

        try:
            sql = """
                INSERT INTO user (email, password, role)
                VALUES (%s, %s, %s)
            """
            values = (email, password, role)

            cursor.execute(sql, values)
            db.commit()
            
            page.show_dialog(ft.SnackBar(ft.Text("User added successfully!")))

            email_field.value = ""
            password_field.value = ""
            role_field.value = ""

        except Exception as err:
            page.show_dialog(ft.SnackBar(ft.Text(f"Error: {err}")))
    
    page.add(
        ft.SafeArea(
            ft.Row(
                controls=[
                ft.Column(
                    controls=[
                        title_field,
                        location_field,
                        description_field,
                        date_field,
                        time_field,
                        ft.Button(
                            "Submit Event",
                            on_click=submit_event
                            )
                        ],
                        expand=True,
                    ),
                            
                ft.Column(
                    controls=[
                        email_field,
                        password_field,
                        role_field,
                        ft.Button(
                            "Submit User",
                            on_click=submit_user
                            )
                        ],
                        expand=True,
                    ),
                ],
                )
            )
)

ft.run(main)