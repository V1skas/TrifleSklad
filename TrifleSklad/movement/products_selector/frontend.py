from typing import Tuple

import reflex as rx

from components.infinite_scroll import infinite_scroll
from TrifleSklad.models import Product
from TrifleSklad.movement.products_selector.backend import ALL, ProductsSelectorState


def product_detail_line(item: Tuple[int, Product]) -> rx.Component:
    # Показуємо лише поля, доречні для типу позиції каталогу:
    # подільне → залишок «count/capacity unit» + прогрес-бар заповненості;
    # унікальне → серійний номер;
    # звичайне (неподільне неунікальне) → без додаткових полів.
    return rx.cond(
        item[1].product_catalog.divisible,
        rx.vstack(
            rx.text(
                f"Залишок: {item[1].count}/{item[1].product_catalog.capacity} "
                f"{item[1].product_catalog.unit}",
                size="1",
                user_select="none",
            ),
            rx.progress(
                value=item[1].count,
                max=item[1].product_catalog.capacity,
                color_scheme="green",
                height="0.5em",
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        rx.cond(
            item[1].product_catalog.uniq,
            rx.text(f"s/n: {item[1].serial_number}", size="1", user_select="none"),
        ),
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
        on_click=ProductsSelectorState.deselect_item(item[0]),
    )


def selector_skeleton() -> rx.Component:
    # Скелетон на час первинного завантаження / після застосування фільтра.
    return rx.vstack(
        rx.foreach(
            [0, 1, 2, 3, 4, 5],
            lambda _: rx.skeleton(height="3.5em", width="100%", border_radius="0.5em"),
        ),
        spacing="2",
        width="100%",
        height="100%",
    )


def selector_list() -> rx.Component:
    # Список: спершу обрані (лишаються при фільтрації), далі доступні; внизу —
    # міні-скелетон під час довантаження наступної порції. Прокрутка контейнера
    # підтягує дані за вимогою (infinite_scroll → load_more).
    return infinite_scroll(
        rx.vstack(
            rx.foreach(
                ProductsSelectorState.get_selected_items, selector_item_selected
            ),
            rx.foreach(ProductsSelectorState.get_available_items, selector_item),
            rx.cond(
                ProductsSelectorState.is_loading_more,
                rx.vstack(
                    rx.skeleton(height="3.5em", width="100%", border_radius="0.5em"),
                    width="100%",
                ),
            ),
            spacing="1",
            width="100%",
        ),
        on_load_more=ProductsSelectorState.load_more,
        width="100%",
        height="100%",
        padding_right="0.5em",
    )


def mass_select_panel() -> rx.Component:
    # Масовий вибір — доступний лише після вибору позиції каталогу.
    return rx.cond(
        ProductsSelectorState.catalog_chosen,
        rx.vstack(
            rx.divider(),
            rx.text("Масовий вибір", size="2", weight="bold"),
            rx.text("Кількість одиниць:", size="2"),
            rx.hstack(
                rx.input(
                    type="number",
                    min=0,
                    placeholder="0",
                    size="2",
                    flex="1",
                    value=ProductsSelectorState.mass_count,
                    on_change=ProductsSelectorState.set_mass_count,
                ),
                rx.button(
                    "Застосувати",
                    type="button",
                    size="2",
                    on_click=ProductsSelectorState.apply_mass_count,
                ),
                spacing="2",
                width="100%",
                align="center",
            ),
            rx.cond(
                ProductsSelectorState.sel_divisible,
                rx.vstack(
                    rx.text(
                        f"Обсяг ({ProductsSelectorState.sel_unit}):", size="2"
                    ),
                    rx.hstack(
                        rx.input(
                            type="number",
                            min=0,
                            placeholder="0",
                            size="2",
                            flex="1",
                            value=ProductsSelectorState.mass_measure,
                            on_change=ProductsSelectorState.set_mass_measure,
                        ),
                        rx.button(
                            "Застосувати",
                            type="button",
                            size="2",
                            color_scheme="grass",
                            on_click=ProductsSelectorState.apply_mass_measure,
                        ),
                        spacing="2",
                        width="100%",
                        align="center",
                    ),
                    spacing="1",
                    width="100%",
                ),
            ),
            spacing="2",
            width="100%",
        ),
    )


def filters_panel() -> rx.Component:
    return rx.vstack(
        rx.heading("Фільтри", size="4", width="100%"),
        rx.text("Категорія:", size="2"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть категорію", width="100%"),
            rx.select.content(
                rx.select.item("Усі категорії", value=ALL),
                rx.foreach(
                    ProductsSelectorState.category_options,
                    lambda o: rx.select.item(o[0], value=o[1]),
                ),
            ),
            value=ProductsSelectorState.filter_category,
            on_change=ProductsSelectorState.change_filter_category,
            width="100%",
            size="2",
        ),
        rx.text("Позиція каталогу:", size="2"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть позицію", width="100%"),
            rx.select.content(
                rx.select.item("Усі позиції", value=ALL),
                rx.foreach(
                    ProductsSelectorState.catalog_options,
                    lambda o: rx.select.item(o[0], value=o[1]),
                ),
            ),
            value=ProductsSelectorState.filter_catalog,
            on_change=ProductsSelectorState.change_filter_catalog,
            disabled=ProductsSelectorState.filter_category == ALL,
            width="100%",
            size="2",
        ),
        rx.text("Пошук (s/n / ID):", size="2"),
        rx.debounce_input(
            rx.input(
                rx.input.slot(rx.icon("search")),
                placeholder="Введіть текст",
                width="100%",
                size="2",
                disabled=~ProductsSelectorState.catalog_chosen,
                value=ProductsSelectorState.filter_search,
                on_change=ProductsSelectorState.change_filter_search,
            ),
            debounce_timeout=400,
        ),
        mass_select_panel(),
        rx.button(
            "Скинути фільтри",
            type="button",
            variant="soft",
            color_scheme="gray",
            on_click=ProductsSelectorState.reset_filters,
            width="100%",
        ),
        spacing="2",
        width="100%",
        height="100%",
        align="stretch",
    )


def selector(*child, **prop) -> rx.Component:
    prop.setdefault("width", "100%")
    prop.setdefault("height", "100%")
    # Сам діалог не повинен прокручуватися — прокрутка лише всередині списку праворуч.
    prop.setdefault("min_height", "0")
    prop.setdefault("overflow", "hidden")
    return rx.vstack(
        rx.heading(
            "Вибір ТМЦ:",
            size="7",
            color=rx.color("accent", 2),
            background_color=rx.color("accent", 9),
            border_radius="0.5em",
            width="100%",
            padding="0.5em",
            flex_shrink="0",
        ),
        rx.hstack(
            # Ліворуч — параметри фільтрації.
            rx.card(
                filters_panel(),
                padding="1em",
                flex="1",
                height="100%",
                min_width="14em",
                min_height="0",
                overflow_y="auto",
            ),
            # Праворуч — список одиниць ТМЦ.
            rx.card(
                rx.cond(
                    ProductsSelectorState.catalog_chosen,
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
                    rx.center(
                        rx.text(
                            "Оберіть категорію та позицію каталогу",
                            color=rx.color("accent", 8),
                            user_select="none",
                            size="3",
                        ),
                        width="100%",
                        height="100%",
                    ),
                ),
                padding="1em",
                flex="2",
                height="100%",
                min_width="0",
                min_height="0",
            ),
            # Середній ряд забирає лишню висоту (flex=1) і дозволяє внутрішню
            # прокрутку (min_height=0), а не розпирає діалог.
            spacing="3",
            width="100%",
            flex="1",
            min_height="0",
            align="stretch",
        ),
        rx.cond(
            ProductsSelectorState.selected_total_units > 0,
            rx.hstack(
                rx.text(
                    f"Обрано: {ProductsSelectorState.selected_total_units}",
                    size="2",
                    weight="bold",
                ),
                rx.foreach(
                    ProductsSelectorState.selected_summary,
                    lambda s: rx.badge(f"{s[0]}: {s[1]}", variant="soft"),
                ),
                spacing="2",
                wrap="wrap",
                width="100%",
                flex_shrink="0",
            ),
        ),
        *child,
        **prop,
    )
