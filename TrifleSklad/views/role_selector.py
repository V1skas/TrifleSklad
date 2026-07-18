from typing import Tuple

import reflex as rx

from TrifleSklad.models import Role
from TrifleSklad.states.role_selector import RoleSelectorState
from TrifleSklad.views.templates import controls


def _selector_item(item: Tuple[int, Role]) -> rx.Component:
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
        on_click=RoleSelectorState.select_item(item[0]),
    )


def _selector_item_selected(item: Tuple[int, Role]) -> rx.Component:
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
        on_click=RoleSelectorState.select_item(item[0]),
    )


def _selector_list() -> rx.Component:
    return rx.scroll_area(
        rx.vstack(
            rx.foreach(RoleSelectorState.get_selected_items, _selector_item_selected),
            rx.foreach(RoleSelectorState.get_unselected_items, _selector_item),
            spacing="1",
        ),
        width="100%",
        height="100%",
    )


def role_selector(*child, **prop) -> rx.Component:
    return rx.vstack(
        rx.heading("Вибір ролей:", size="8", color=rx.color("accent", 2), background_color=rx.color("accent", 9), width="100%", padding="0.5em"),
        controls.input_field(
            rx.input.slot(rx.icon("search")),
            placeholder="Пошук",
            value=RoleSelectorState.filter,
            width="100%",
            on_change=RoleSelectorState.set_filter,
        ),
        rx.card(_selector_list(), width="100%", height="100%"),
        *child,
        padding="1em",
        width="100%",
        **prop,
    )
