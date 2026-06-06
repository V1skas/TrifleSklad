from typing import Tuple

import reflex as rx

from TrifleSklad.models import Product
from TrifleSklad.movement.products_selector.backend import ProductsSelectorState


def product_detail_line(item: Tuple[int, Product]) -> rx.Component:
    # Для подільного ТМЦ показуємо поточну ємність, для решти — серійний номер.
    return rx.cond(
        item[1].product_catalog.divisible,
        rx.text(f"Ємність: {item[1].count}", size="1", user_select="none"),
        rx.text(f"s/n: {item[1].serial_number}", size="1", user_select="none"),
    )


def selector_item(item: Tuple[int, Product]) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading(item[1].product_catalog.title, size="3", user_select="none"),
            rx.text(f"id: {item[1].id}", size="1", user_select="none"),
            product_detail_line(item),
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
        on_click=ProductsSelectorState.select_item(item[0]),
    )


def selector_item_selected(item: Tuple[int, Product]) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.icon("circle-check-big", color=rx.color("accent", 9), height="100%"),
            rx.vstack(
                rx.heading(
                    item[1].product_catalog.title,
                    color=rx.color("accent", 9),
                    size="3",
                    user_select="none",
                ),
                rx.text(f"id: {item[1].id}", size="1", user_select="none"),
                product_detail_line(item),
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
        on_click=ProductsSelectorState.select_item(item[0]),
    )


def selector_skeleton() -> rx.Component:
    # Скелетон на час завантаження доступного ТМЦ.
    return rx.vstack(
        rx.foreach(
            [0, 1, 2, 3, 4],
            lambda _: rx.skeleton(height="3.5em", width="100%", border_radius="0.5em"),
        ),
        spacing="2",
        width="100%",
        height="100%",
    )


def selector_list() -> rx.Component:
    return rx.scroll_area(
        rx.vstack(
            rx.foreach(
                ProductsSelectorState.get_selected_items, selector_item_selected
            ),
            rx.foreach(ProductsSelectorState.get_unselected_items, selector_item),
            spacing="1",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def selector(*child, **prop) -> rx.Component:
    return rx.vstack(
        rx.heading(
            "Вибір ТМЦ:",
            size="8",
            color=rx.color("accent", 2),
            background_color=rx.color("accent", 9),
            border_radius="0.5em",
            width="100%",
            padding="0.5em",
        ),
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Пошук",
            value=ProductsSelectorState.filter_many,
            width="100%",
            size="3",
            on_change=ProductsSelectorState.change_filter_many,
        ),
        rx.card(
            rx.cond(
                ProductsSelectorState.is_loading,
                selector_skeleton(),
                rx.cond(
                    ProductsSelectorState.has_items,
                    selector_list(),
                    rx.center(
                        rx.text(
                            "ТМЦ не знайдено",
                            color=rx.color("accent", 8),
                            user_select="none",
                            size="3",
                        ),
                        width="100%",
                        height="100%",
                    ),
                ),
            ),
            padding="1em",
            width="100%",
            height="100%",
        ),
        *child,
        **prop,
    )
