import reflex as rx

from typing import List, Tuple

from TrifleSklad.administration.actions.backend import *

def list_item(item: Tuple[int, Action]) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading(item[1].title, size="3", user_select="none"),
            rx.text(item[1].description, size="1", user_select="none"),

            spacing="0",
            width="100%",
        ),

        background_color=rx.color("accent", 2),
        border_color=rx.color("accent", 4),
        border_width="1px",

        padding="calc(0.7em + 2px)",

        width="100%",

        _hover={
            "background_color": rx.color("accent", 6),
            "border_color": rx.color("accent", 8),
            "border_width": "1px",
            "padding": "calc(0.7em + 2px)",
        },
        _active={
            "background_color": rx.color("accent", 8),
            "border_color": rx.color("accent", 8),
            "border_width": "3px",
            "padding": "0.7em",
        },

        on_click=ActionsState.select_item(item[0]),
    )

def list_item_selected(item: Tuple[int, Action]) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.icon("circle-check-big", color=rx.color("accent", 9), height="100%"),

            rx.vstack(
                rx.heading(item[1].title, color=rx.color("accent", 9), size="3", user_select="none"),
                rx.text(item[1].description, size="1", user_select="none"),

                flex="1",
                spacing="0",
                height="100%",
            ),

            align="center",
            width="100%",
        ),

        background_color=rx.color("accent", 4),
        border_color=rx.color("accent", 9),
        border_width="2px",

        padding="calc(0.7em + 1px)",

        width="100%",

        _hover={
            "background_color": rx.color("accent", 6),
            "border_color": rx.color("accent", 8),
            "border_width": "2px",
            "padding": "calc(0.7em + 1px)",
        },
        _active={
            "background_color": rx.color("accent", 8),
            "border_color": rx.color("accent", 8),
            "border_width": "3px",
            "padding": "0.7em",
        },

        on_click=ActionsState.select_item(item[0]),
    )

def list() -> rx.Component:
    return rx.scroll_area(
        rx.vstack(
            rx.foreach(ActionsState.get_selected_items, list_item_selected),
            rx.foreach(ActionsState.get_unselected_items, list_item),

            spacing="1",
        ),

        width="100%",
        height="100%",
    )

def index(*child, **prop) -> rx.Component:
    return rx.vstack(
        rx.heading("Выбор действий:", size="8", color=rx.color("accent", 2), background_color=rx.color("accent", 9), width="100%", padding="0.5em"),
        rx.vstack(
            rx.input(
                rx.input.slot(rx.icon("search")),

                placeholder="Поиск",
                value=ActionsState.filter,

                width="100%",
                size="3",

                on_change=ActionsState.set_filter,
            ),
            rx.card(
                list(),

                width="100%",
                height="100%",
            ),
            *child,

            padding="1em",
            width="100%",
            height="100%",
        ),

        **prop,
    )
