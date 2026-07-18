from typing import List, Optional

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.declared.submenu import MAIN, MenuItem
from TrifleSklad.views.templates import controls
from components import decor


# Стилі для вкладеної таблиці деталізації (розгортаний рядок) на СИРОМУ
# rx.el.table. Чому не rx.table.root: Radix Table.Root безумовно загортає
# <table> у ScrollArea (display:flex; height:100%). Всередині <td>
# (display:table-cell, невизначена висота) Safari нестабільно резолвить
# height:100% → 0 по-рядково й переплутує рядки при розгортанні (у Chromium
# працює). Сирий <table> без ScrollArea/flex/відсоткових висот рендериться
# однаково у всіх браузерах. Стилі відтворюють вигляд Radix-таблиці.
NESTED_DETAIL_TABLE = {
    "width": "100%",
    "border_collapse": "collapse",
    "background_color": rx.color("accent", 1),
    "border": f"1px solid {rx.color('accent', 5)}",
    "font_size": "var(--font-size-2)",
}
NESTED_DETAIL_THEAD = {
    "background_color": rx.color("accent", 6),
}
NESTED_DETAIL_TH = {
    "text_align": "left",
    "padding": "0.5em 0.75em",
    "color": rx.color("accent", 2),
    "font_weight": "bold",
}
NESTED_DETAIL_TD = {
    "padding": "0.5em 0.75em",
    "border_top": f"1px solid {rx.color('accent', 5)}",
}


def _item_cond(item: MenuItem):
    """Var-умова видимості пункта меню, або None якщо він завжди видимий."""
    if item.required_action is not None:
        return AppState.get_user_actions.contains(item.required_action)
    if item.required_any:
        cond = AppState.get_user_actions.contains(item.required_any[0])
        for a in item.required_any[1:]:
            cond = cond | AppState.get_user_actions.contains(a)
        return cond
    return None


def _menu_visibility(items: List[MenuItem]):
    """OR за умовами дітей (рекурсивно — врахує видимість вкладених підгруп).
    Повертає None, якщо якась дитина завжди видима."""
    conds = []
    for c in items:
        cond = _item_cond(c)
        if cond is None and c.children:
            cond = _menu_visibility(c.children)
        conds.append(cond)
    if not conds or any(c is None for c in conds):
        return None
    cond = conds[0]
    for c in conds[1:]:
        cond = cond | c
    return cond


# Стилі шапки/бічної панелі відтворюють дореформений TrifleSklad (плоскі
# кольори теми, без градієнтів) — див. `git show dev:components/elements.py`
# та `git show dev:TrifleSklad/frontend.py`. Персистентність (app_wraps, щоб
# шапка/панель не пересоздавались при навігації) і механіка згортання
# підгруп (expanded_groups/toggle_group) — це вже підхід із Dekanat.
_HOVER_UNDERLINE = {
    "color": rx.color("accent", 12),
    "transform": "translateY(-1px)",
    "transition": "all 0.1s ease-in-out",
    "border_bottom": f"4px solid {rx.color('accent', 9)}",
}


def _navbar_button(*children, **prop) -> rx.Component:
    prop.setdefault("variant", "ghost")
    prop.setdefault("color", rx.color("accent", 11))
    prop.setdefault("border_radius", "0")
    prop.setdefault("size", "4")
    prop.setdefault("height", "100%")
    prop.setdefault("_hover", _HOVER_UNDERLINE)
    return rx.button(*children, **prop)


def navbar_link(item: MenuItem) -> rx.Component:
    rendered = rx.link(
        _navbar_button(item.label),
        href=item.url or "#",
        height="70%",
        underline="none",
    )
    cond = _item_cond(item) if not item.children else _menu_visibility(item.children)
    if cond is None:
        return rendered
    return rx.cond(cond, rendered, rx.fragment())


def _user_menu() -> rx.Component:
    return rx.menu.root(
        rx.menu.trigger(
            _navbar_button(
                rx.icon("user"),
                rx.text(AppState.fio, size="3"),
                height="75%",
            ),
        ),
        rx.menu.content(
            rx.menu.separator(),
            rx.menu.item("Вийти", on_click=AppState.logout),
        ),
    )


def header() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.link(
                rx.hstack(decor.logo(), align_items="center", padding="1em", spacing="1"),
                # Завжди веде на головну, незалежно від поточного розділу.
                href=routes.WELCOME,
                underline="none",
                flex_shrink="0",
            ),
            rx.hstack(
                *[navbar_link(item) for item in MAIN],
                align_items="center",
                height="100%",
                spacing="5",
                flex="1",
                min_width="0",
                justify="center",
                overflow_x="auto",
            ),
            _user_menu(),
            justify="between",
            align_items="center",
            height="100%",
            width="100%",
        ),
        border_bottom=f"1px solid {rx.color('accent', 9)}",
        padding_right="1em",
        width="100%",
        height="75px",
    )


def _sidebar_link(item: MenuItem, indent: bool = False) -> rx.Component:
    # Вкладені пункти підгруп (Видача/Повернення) на тон темніше/синіше
    # батьківських — інакше вони виглядають так само, як пункти верхнього
    # рівня, і підгрупа візуально не читається як вкладена.
    bg_scale = 5 if indent else 3
    hover_bg_scale = 6 if indent else 4
    rendered = rx.link(
        rx.button(
            item.label,
            radius="none",
            variant="soft",
            color=rx.color("accent", 11),
            border_radius="0",
            background_color=rx.color("accent", bg_scale),
            _hover={
                "color": rx.color("accent", 12),
                "background_color": rx.color("accent", hover_bg_scale),
                "transform": "translateX(5px)",
                "transition": "all 0.1s ease-in-out",
                "border_left": f"4px solid {rx.color('accent', 9)}",
            },
            size="3",
            width="100%",
            style={"padding_left": "2rem"} if indent else {},
        ),
        href=item.url or "#",
        width="100%",
        underline="none",
    )
    cond = _item_cond(item)
    if cond is None:
        return rendered
    return rx.cond(cond, rendered, rx.fragment())


def _sidebar_subgroup(item: MenuItem) -> rx.Component:
    """Підгрупа всередині панелі розділу (напр. «Видача»/«Повернення» у
    «Рух ТМЦ»): клікабельний заголовок-роздільник + список, що згортається
    (та сама механіка `expanded_groups`, що й у верхньому меню)."""
    expanded = AppState.expanded_groups.contains(item.label)
    header_row = rx.box(
        rx.hstack(
            rx.text(item.label, size="3", weight="medium", color=rx.color("accent", 11)),
            rx.icon(
                "chevron-right",
                size=16,
                color=rx.color("accent", 11),
                transform=rx.cond(expanded, "rotate(90deg)", "rotate(0deg)"),
                transition="transform 0.15s ease",
            ),
            justify="center",
            align="center",
            spacing="2",
            width="100%",
        ),
        padding="0.6em 0.75em",
        background_color=rx.color("accent", 3),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 4)},
        on_click=AppState.toggle_group(item.label),
        width="100%",
    )
    children_box = rx.box(
        rx.vstack(
            *[_sidebar_link(c, indent=True) for c in item.children],
            spacing="0",
            width="100%",
        ),
        max_height=rx.cond(expanded, "500px", "0px"),
        overflow="hidden",
        transition="max-height 0.2s ease",
        width="100%",
    )
    rendered = rx.vstack(header_row, children_box, spacing="0", width="100%")
    visibility = _menu_visibility(item.children)
    if visibility is None:
        return rendered
    return rx.cond(visibility, rendered, rx.fragment())


def _sidebar_entry(item: MenuItem) -> rx.Component:
    if item.children:
        return _sidebar_subgroup(item)
    return _sidebar_link(item)


def section_sidebar(group: MenuItem) -> rx.Component:
    """Бічна панель одного розділу — старий вигляд (`git show
    dev:components/elements.py::sidebar/sidebar_link`): фіксована ширина,
    сіра картка, пункти-кнопки з підсвіткою зсувом при наведенні."""
    return rx.box(
        rx.vstack(
            rx.heading(
                "Меню",
                size="6",
                color=rx.color("accent", 3),
                bg=rx.color("accent", 9),
                height="40px",
                text_align="center",
                line_height="40px",
                width="100%",
            ),
            *[_sidebar_entry(c) for c in group.children],
            spacing="0",
            align_items="stretch",
            width="100%",
        ),
        border_radius="1em 1em 5px 5px",
        background_color=rx.color("gray", 4),
        overflow_y="auto",
        overflow_x="hidden",
        padding="0",
        width="100%",
        # fit-content, а не 100% — інакше сіра картка тягнеться порожнім
        # прямокутником до низу сторінки, коли пунктів менше за висоту вікна.
        height="fit-content",
        max_height="100%",
    )


def active_section_sidebar() -> rx.Component:
    """Показує панель розділу, що відповідає поточному шляху (`git show
    dev:TrifleSklad/*/frontend.py::index` — своя панель на кожен розділ;
    «Заявки» — лист без панелі, як і в старому дизайні)."""
    groups_with_sidebar = [g for g in MAIN if g.children]
    return rx.match(
        AppState.active_group_url,
        *[(g.url, section_sidebar(g)) for g in groups_with_sidebar],
        rx.fragment(),
    )


def page_wrapper(
    page_header: rx.Component,
    page_content: rx.Component,
    filter_panel: Optional[rx.Component] = None,
    on_mount=None,
) -> rx.Component:
    """Каркас окремої сторінки.

    Зовнішній chrome (шапка/бічна панель розділу) приходить з app_wraps і не
    пересоздається при навігації.

    Якщо переданий `filter_panel`, він рендериться між шапкою і контентом —
    власну видимість (`rx.cond` на `State.<filter_open>`) панель забезпечує
    сама.

    `on_mount` — подія, що виконується при кожному монтуванні сторінки.
    Reflex не завжди повторно запускає `on_load` при внутрішній навігації
    через `rx.redirect`, через що список лишався застарілим після
    add/edit/delete. `on_mount` спрацьовує надійно на кожен монтаж
    компонента і перечитує дані.
    """
    children: List[rx.Component] = [controls.unsaved_changes_guard(), page_header]
    if filter_panel is not None:
        children.append(filter_panel)
    children.append(
        rx.box(
            page_content,
            flex="1",
            height="100%",
            width="100%",
            # min_width=0 — без цього flex/grid-елемент не стискається нижче
            # ширини свого вмісту (типова причина, чому широкі таблиці
            # «вилазять» за межі сторінки замість прокрутки всередині).
            min_width="0",
            # Це єдиний скролл-контейнер тіла сторінки. padding_right тримає
            # вміст осторонь overlay-скролбара (macOS), який інакше малюється
            # ПОВЕРХ правого краю контенту. scrollbar-gutter не годиться —
            # на overlay-скролбарах він без ефекту; padding працює й для
            # overlay, й для класичного.
            padding_right="12px",
            # Невеликий відступ з решти сторін — інакше поля вводу (фокус-
            # кільце/рамка) стоять впритул до межі overflow-контейнера й
            # крайній піксель рамки зрізається при фокусі/наведенні.
            padding_top="6px",
            padding_bottom="6px",
            padding_left="6px",
            overflow_y="auto",
            overflow_x="auto",
        )
    )
    extra = {"on_mount": on_mount} if on_mount is not None else {}
    return rx.vstack(
        *children,
        flex="1",
        width="100%",
        height="100%",
        min_width="0",
        spacing="3",
        **extra,
    )


def header_subpage(title: str, *args, left: Optional[rx.Component] = None, **prop) -> rx.Component:
    """Шапка підсторінки — старий вигляд (`git show
    dev:components/elements.py::subpage_header`): заголовок кольору акценту,
    тонка лінія знизу, без градієнтів. Заголовок центрується по ширині
    шапки через grid (1fr/auto/1fr) — так центр не залежить від ширини
    лівого/правого блоків, на відміну від hstack+spacer."""
    heading = rx.heading(title, size="7", color=rx.color("accent", 9), white_space="nowrap")

    return rx.box(
        rx.box(left or rx.fragment(), justify_self="start", min_width="0"),
        rx.box(heading, justify_self="center", min_width="0"),
        rx.box(
            rx.hstack(*args, spacing="4", align="center", wrap="wrap", justify="end"),
            justify_self="end",
            min_width="0",
        ),
        display="grid",
        grid_template_columns="1fr auto 1fr",
        column_gap="1rem",
        align_items="center",
        padding="0.5em",
        style={"border_bottom": f"1px solid {rx.color('accent', 9)}"},
        **prop,
    )
