import reflex as rx

from TrifleSklad import authorithation, routes

def navbar_link(text: str, url: str) -> rx.Component:
    return rx.hstack(
        rx.box(height="0.5em", width="0.5em", background_color=rx.color("accent", 9)),
        rx.button(
            text,

            size="4",
            radius="none",
            variant='ghost',
            height="80%",

            on_click=rx.redirect(url)
        ),

        align="center",
        height="100%",
    )
    
    """return rx.link(
        rx.text(text, size="4", weight="medium"), href=url
    )
"""
def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.heading("Trifle", size="7", color=rx.color("accent", 3), background_color=rx.color("accent", 9), padding="0.1em", padding_left="0.3em", padding_right="0.3em"),
                rx.heading("Склад", size="7", color=rx.color("accent", 9), background_color="transparent", padding="0.1em"),

                align_items="center",
                padding="1em",
            ),
            rx.hstack(
                navbar_link("Администрирование", routes.ADMIN),
                navbar_link("Item 2", "#"),
                navbar_link("Item 3", "#"),

                align_items="center",
                height="100%",
                spacing="5",
            ),
            rx.menu.root(
                rx.menu.trigger(
                    rx.icon_button(
                        rx.icon("user"),
                        size="2",
                        radius="full",
                    )
                ),
                rx.menu.content(
                    rx.menu.separator(),
                    rx.menu.item("Выйти"),
                ),

                justify="end",
                padding="1em",
            ),

            justify="between",
            align_items="center",
            height="100%",
        ),
        
        #bg=rx.color("accent", 5),
        border_bottom=f"1px solid {rx.color('accent', 9)}",

        padding_right="1em",

        #position="fixed",
        #left="0px",
        #top="0px",
        #z_index="5",

        width="100%",
        height="75px",
    )

def auth_page() -> rx.Component:
    return authorithation.frontend.index()

def welcome_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.vstack(
            rx.heading("Приветствую в Trifle Склад!", size="9", color=rx.color("accent", 9)),
            rx.text(
                "Для начала работы, выберите нужный раздел в шапке страницы.",

                size="5",
            ),

            spacing="5",
            justify="center",
            align="center",

            min_height="75vh",
            width="100%",
        ),

        width="100%",
    )

