import reflex as rx
from reflex.app import default_overlay_component

from TrifleSklad.state import AppState
from TrifleSklad.views.templates.layouts import active_section_sidebar, header


def app_shell_wrap(_stateful: bool) -> rx.Component:
    """Персистентний wrapper над <Outlet/>: шапка й бічна панель розділу не
    пересоздаються при навігації між сторінками (підключається через
    `app.app_wraps`). Бічна панель показується лише для розділів, що її
    мають (як у дореформеному TrifleSklad — кожен розділ мав власну панель,
    «Заявки» жодної не мала)."""
    chrome_visible = AppState.is_authenticated
    show_sidebar = chrome_visible & AppState.has_section_sidebar
    return rx.box(
        rx.box(
            header(),
            display=rx.cond(chrome_visible, "flex", "none"),
            grid_area="header",
            width="100%",
            height="100%",
        ),
        rx.box(
            active_section_sidebar(),
            display=rx.cond(show_sidebar, "flex", "none"),
            grid_area="sidebar",
            width="100%",
            height="100%",
            min_height="0",
            overflow="hidden",
        ),
        # Третя дитина (content_area_wrap) додається автоматично через ланцюг app_wraps.
        display="grid",
        grid_template_areas='"header header" "sidebar content"',
        grid_template_columns=rx.cond(show_sidebar, "17em 1fr", "0 1fr"),
        grid_template_rows=rx.cond(chrome_visible, "75px 1fr", "0 1fr"),
        # Горизонтальні gap/padding зменшені вдвічі (0.5vw замість 1vw) —
        # відступи підсторінок зліва/справа були завеликі. Вертикальні (1vh)
        # не чіпали — запит стосувався лише лівого/правого.
        grid_gap=rx.cond(chrome_visible, "1vh 0.5vw", "0 0"),
        padding=rx.cond(chrome_visible, "0 0.5vw 1vh 0.5vw", "0"),
        height="100vh",
        # width="100%", не 100vw — 100vw включає ширину вертикального
        # скролл-бара, через що вся сітка каркасу (і шапка підсторінки в ній)
        # ставала трохи ширшою за видиму область і вилазила за межі справа.
        width="100%",
        overflow="hidden",
        transition="grid-template-columns 0.3s ease-in-out",
    )


def content_area_wrap(_stateful: bool) -> rx.Component:
    """Контейнер, у який роутер вкладає поточну сторінку."""
    return rx.box(
        grid_area="content",
        # min_width=0 — grid-елемент інакше не стискається нижче min-content
        # своїх дітей (широка таблиця розпирала б усю сітку каркасу й
        # «вилазила» за межі viewport замість прокрутки в собі).
        min_width="0",
        # Горизонтальні відступи 12px гасять «звис» ghost-кнопок дій у шапці
        # підсторінки: Radix ghost-варіант (button_primary/secondary,
        # filter_button) має margin: 0 -12px (оптичне вирівнювання тексту під
        # padding), тож border-box крайньої правої/лівої кнопки виступає на
        # 12px за контент. Без цих відступів найправіша кнопка дій вилазила за
        # праву межу область контенту й на КОЖНІЙ підсторінці зʼявлявся
        # горизонтальний скрол. 12px = рівно величина того відʼємного margin.
        padding_left="12px",
        padding_right="12px",
        # overflow=hidden, не auto — це лише нескролляча рамка комірки. Вертикаль
        # і горизонталь тіла сторінки скролить внутрішній бокс page_wrapper
        # (flex=1, overflow auto). Раніше тут дублювався overflow_x/y="auto" —
        # зовнішній скролл-контейнер реагував навіть на суб-піксельний «звис» і
        # малював фантомний горизонтальний скрол на КОЖНІЙ формі add/edit.
        overflow="hidden",
        height="100%",
        width="100%",
    )


def overlay_wrap(stateful: bool) -> rx.Component | None:
    """Заміна штатного app_wrap'у `(5, "Overlay")` — той самий набір
    (значок «немає звʼязку» + тостер), але у власному стекінг-контексті
    з високим z-index.

    Навіщо: `ConnectionPulser` рендериться як `<div position:fixed>` БЕЗ
    z-index, а 9999 стоїть на іконці всередині нього. `position: fixed`
    сам по собі створює стекінг-контекст, тож 9999 замикається в ньому,
    а сам контейнер лишається на рівні `z-index: auto` (= 0). Далі
    вирішує порядок у DOM: штатний Overlay-wrap вкладений у ContentArea
    ПЕРЕД контентом сторінки, а таблиці `rx.table.root(variant="surface")`
    мають `backdrop-filter: blur(64px)` (Radix `--backdrop-filter-panel`
    при `panelBackground=translucent`), який теж створює стекінг-контекст
    на рівні 0, але пізніше в DOM → таблиця малювалась ПОВЕРХ значка.

    Обгортка нульового розміру (діти позиціоновані fixed самі по собі,
    тому розмір контейнера ні на що не впливає, і він нічого не перехоплює
    мишею) з z-index піднімає весь оверлей над контентом сторінки."""
    if not stateful:
        return None
    return rx.fragment(
        rx.box(
            default_overlay_component(),
            position="fixed",
            top="0",
            left="0",
            width="0",
            height="0",
            z_index="9999",
        ),
    )
