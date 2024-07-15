from contextlib import contextmanager

from fastapi.responses import RedirectResponse
from loguru import logger
from middleware import AuthMiddleware
from nicegui import app, ui
from otf_api import Otf, OtfUser
from pycognito.exceptions import TokenVerificationException
from storage import LocalStorage, add_otf_to_storage, add_user_to_storage, clear_all_storage

LOCAL_STORAGE = LocalStorage()

app.add_middleware(AuthMiddleware)


def logout() -> None:
    clear_all_storage()
    ui.navigate.to("/login")


async def get_otf() -> Otf:
    await ui.context.client.connected()

    logger.info("getting otf...")

    if "otf" in app.storage.tab:
        logger.info("got otf from tab storage")
        return app.storage.tab["otf"]

    if "otf_hydration_dict" in app.storage.user and "device_key" in app.storage.tab:
        logger.info("got otf from stored hydration dict")
        otf = Otf.hydrate(**app.storage.user["otf_hydration_dict"], device_key=app.storage.tab["device_key"])
        add_otf_to_storage(otf)
        return otf

    logger.info("creating new otf...")
    if user := await get_user():
        otf = await Otf.create(user=user)
        logger.info("created new otf")

        add_otf_to_storage(otf)
        return otf

    ui.navigate.to("/login")
    return None


async def get_user() -> OtfUser:
    await ui.context.client.connected()

    logger.info("getting user...")
    if "user" in app.storage.tab:
        logger.info("got user from tab storage")
        return app.storage.tab["user"]

    logger.info("getting user from stored tokens...")

    try:
        device_key = await LocalStorage.get_item("device_key")
        user = OtfUser.from_token(**app.storage.user["tokens"], device_key=device_key)
        logger.info("got user from stored tokens")
        app.storage.tab["user"] = user
        return app.storage.tab["user"]
    except (TokenVerificationException, KeyError):
        ui.notify("Your token has expired, please log in again", color="negative")
        await logout()


@contextmanager
def header_and_card():
    with ui.header().style("padding: 0"), ui.tabs().classes("w-full"):
        one = ui.tab("Classes")
        one.on("click", lambda: ui.navigate.to("/classes"))
        two = ui.tab("Upcoming CLasses")
        two.on("click", lambda: ui.navigate.to("/upcoming_classes"))
    with ui.footer():
        ui.button(text=app.storage.user.get("username", ""), on_click=logout, icon="logout").classes(
            "absolute top-0 right-0"
        ).props("style: unelevated")
    with ui.card().classes("absolute-top items-center w-full h-full"):
        yield


@ui.page("/")
async def main_page() -> None:
    await ui.context.client.connected()
    with header_and_card(), ui.column().classes("absolute-center items-center"):
        ui.label(f'Hello {app.storage.user["username"]}!').classes("text-2xl")
        ui.button(on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/login")), icon="logout").props(
            "outline round"
        )


@ui.page("/upcoming_classes")
async def upcoming_classes() -> None:
    with header_and_card():
        with ui.spinner() as spinner:
            otf = await get_otf()
            bookings = await otf.get_bookings()

        spinner.delete()

        rows = []
        for booking in bookings.bookings:
            rows.append(
                {
                    "class_name": booking.otf_class.name,
                    "start_date": booking.otf_class.starts_at_local.strftime("%Y-%m-%d"),
                    "start_time": booking.otf_class.starts_at_local.strftime("%H:%M"),
                    "duration": booking.otf_class.duration,
                    "coach_name": booking.otf_class.coach.name,
                    "status": booking.status.value,
                    "id": booking.class_booking_uuid,
                }
            )

        ag_grid_data = {
            "defaultColDef": {"flex": 1},
            "columnDefs": [
                {"headerName": "id", "field": "id", "hide": True},
                {"headerName": "Class Name", "field": "class_name"},
                {"headerName": "Start Date", "field": "start_date"},
                {"headerName": "Start Time", "field": "start_time"},
                {"headerName": "Duration", "field": "duration"},
                {"headerName": "Coach Name", "field": "coach_name"},
                {"headerName": "Status", "field": "status"},
            ],
            "rowData": rows,
        }

        _ = ui.aggrid(options=ag_grid_data)


@ui.page("/classes")
async def classes() -> None:
    with header_and_card():
        with ui.spinner() as spinner:
            otf = await get_otf()
            assert isinstance(otf, Otf)
            classes = await otf.get_classes()

        spinner.delete()

        rows = []
        for class_ in classes.classes:
            rows.append(
                {
                    "Day Of Week": class_.day_of_week,
                    "Start Date": class_.starts_at_local.strftime("%Y-%m-%d"),
                    "Start Time": class_.starts_at_local.strftime("%H:%M"),
                    "Duration": class_.duration,
                    "Class Name": class_.name,
                    "Coach Name": class_.coach.first_name,
                    "Studio Name": class_.studio.name,
                    "Class Type": class_.class_type.name,
                    "Is Booked": class_.is_booked,
                    "Waitlist Available": class_.waitlist_available,
                    "Home Studio": class_.is_home_studio,
                }
            )

        ag_grid_data = {
            "defaultColDef": {"flex": 1},
            "columnDefs": [
                {
                    "headerName": "Day Of Week",
                    "field": "Day Of Week",
                    "filter": "agTextColumnFilter",
                    "floatingFilter": True,
                },
                {"headerName": "Start Date", "field": "Start Date"},
                {"headerName": "Start Time", "field": "Start Time"},
                {"headerName": "Duration", "field": "Duration"},
                {
                    "headerName": "Class Name",
                    "field": "Class Name",
                    "filter": "agTextColumnFilter",
                    "floatingFilter": True,
                },
                {
                    "headerName": "Coach Name",
                    "field": "Coach Name",
                    "filter": "agTextColumnFilter",
                    "floatingFilter": True,
                },
                {
                    "headerName": "Studio Name",
                    "field": "Studio Name",
                    "filter": "agTextColumnFilter",
                    "floatingFilter": True,
                },
                {
                    "headerName": "Class Type",
                    "field": "Class Type",
                    "filter": "agTextColumnFilter",
                    "floatingFilter": True,
                },
                {"headerName": "Is Booked", "field": "Is Booked"},
                {"headerName": "Waitlist Available", "field": "Waitlist Available"},
                {"headerName": "Home Studio", "field": "Home Studio"},
            ],
            "rowData": rows,
            # "domLayout": "autoHeight",
        }

        _ = ui.aggrid(options=ag_grid_data)


@ui.page("/login")
async def login() -> RedirectResponse | None:
    async def try_login() -> None:
        try:
            if not app.storage.user.get("authenticated"):
                with ui.spinner():
                    logger.info("logging in")
                    user = OtfUser.login(username.value, password.value)
                    logger.info("logged in")
                    app.storage.user.update({"username": username.value, "authenticated": True})
                    logger.info("updated username")
                    await add_user_to_storage(user)
                    logger.info("updated storage")
                    ui.navigate.to(app.storage.user.get("referrer_path", "/upcoming_classes"))

        except TokenVerificationException:
            ui.notify("Your token has expired, please log in again", color="negative")
            app.storage.user["authenticated"] = False
        except Exception:
            logger.exception("Exception attempting to log in")
            ui.notify("Wrong username or password", color="negative")

    with header_and_card():
        if app.storage.user.get("authenticated", False):
            logger.info(app.storage.user.get("authenticated"))
            logger.info(app.storage.user.get("referrer_path", "/upcoming_classes"))
            return RedirectResponse("/upcoming_classes")

        username = ui.input("Username", value=app.storage.user.get("username", "")).classes("mb-4")
        password = ui.input("Password", password=True, password_toggle_button=True).classes("mb-4")
        ui.button("Log in", on_click=try_login)

    return None


ui.run(storage_secret="d9894965-7697-47d0-bb96-b33f959d70fb")
