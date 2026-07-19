import reflex as rx


def button_back(href: str, label: str = "Назад", **prop):
    """Кнопка повернення/скасування — повнотекстова ghost-кнопка (старий
    дизайн: «Скасувати» на формах додавання/редагування, «Повернутись» на
    перегляді, `git show dev:TrifleSklad/administration/workers/frontend.py`)."""
    return button_secondary(label, on_click=rx.redirect(href), **prop)


def button_filter_toggle(is_open, on_click, **prop):
    """Кнопка-перемикач панелі фільтрів. Підсвічується (primary) коли панель відкрита."""
    return rx.cond(
        is_open,
        button_image_primary(name_icon="funnel", on_click=on_click, **prop),
        button_image_secondary(name_icon="funnel", on_click=on_click, **prop),
    )


def filter_panel(is_open, *fields, on_clear=None) -> rx.Component:
    """Контейнер панелі фільтрів. Завжди присутній у DOM, видимість анімується через
    `max-height` та `opacity` від `is_open` (Var[bool])."""
    actions = rx.fragment()
    if on_clear is not None:
        actions = rx.hstack(
            rx.spacer(),
            button_secondary("Очистити", on_click=on_clear),
            width="100%",
        )
    return rx.box(
        rx.box(
            rx.vstack(
                *fields,
                actions,
                spacing="3",
                align="stretch",
                width="100%",
            ),
            padding="1rem",
            border_radius="0.6rem",
            background_color=rx.color("gray", 2),
            border=f"1px solid {rx.color('gray', 5)}",
            width="100%",
        ),
        # max-height як проксі для анімації висоти: 0 → велике значення.
        max_height=rx.cond(is_open, "60rem", "0"),
        opacity=rx.cond(is_open, "1", "0"),
        margin_top=rx.cond(is_open, "0", "-0.75rem"),
        overflow="hidden",
        transition="max-height 0.3s ease, opacity 0.25s ease, margin-top 0.3s ease",
        width="100%",
    )


# Гвард несохранённых изменений. Перехоплює будь-яку навігацію (у т.ч.
# клієнтську через React Router) і оновлення/закриття вкладки, коли на
# сторінці додавання/редагування є незбережені зміни. Відкриття посилання в
# новій вкладці (target=_blank, Ctrl/Cmd/Shift/middle-click) НЕ перехоплюється.
#
# Активність визначається МАРШРУТОМ: сторінки додавання закінчуються на "/add",
# редагування містять "/edit/". Тому гвард автоматично працює на ВСІХ формах
# додавання/редагування без окремого маркера на кожній. Встановлюється один раз
# (ідемпотентно) через page_wrapper. «Брудність» відстежуємо в JS: будь-який ввід у
# нативні поля або вибір у Radix (option/switch/radio/checkbox) виставляє прапорець.
# Прапорець скидається при кожній зміні маршруту (React Router йде через history API).
# Кнопки «Зберегти»/«Скасувати» — це <button> з rx.redirect (клієнтська навігація,
# не <a>), тож не блокуються.
_UNSAVED_GUARD_SCRIPT = """
(function(){
  if(window.__trifleGuardInit){ return; }
  window.__trifleGuardInit=true;
  window.__trifleDirty=false;
  var onForm=function(){ var p=location.pathname; return /\\/add\\/?$/.test(p) || /\\/edit\\//.test(p); };
  var mark=function(){ if(onForm()){ window.__trifleDirty=true; } };
  document.addEventListener('input', function(e){
    var t=e.target;
    if(t && t.matches && t.matches('input,textarea,select,[contenteditable="true"]')){ mark(); }
  }, true);
  document.addEventListener('change', function(e){
    var t=e.target;
    if(t && t.matches && t.matches('input,textarea,select')){ mark(); }
  }, true);
  document.addEventListener('pointerdown', function(e){
    var t=e.target;
    if(t && t.closest && t.closest('[role="option"],[role="switch"],[role="radio"],[role="checkbox"]')){ mark(); }
  }, true);
  // Скидаємо прапорець при реальній зміні маршруту (React Router — history API).
  var lastPath=location.pathname;
  var reset=function(){ if(location.pathname!==lastPath){ lastPath=location.pathname; window.__trifleDirty=false; } };
  ['pushState','replaceState'].forEach(function(m){
    var orig=history[m];
    history[m]=function(){ var r=orig.apply(this, arguments); reset(); return r; };
  });
  window.addEventListener('popstate', reset);
  document.addEventListener('click', function(e){
    if(!onForm() || window.__trifleDirty!==true){ return; }
    var a=e.target.closest ? e.target.closest('a[href]') : null;
    if(!a){ return; }
    if(a.target==='_blank' || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || (typeof e.button==='number' && e.button!==0)){ return; }
    var href=a.getAttribute('href')||'';
    if(!href || href==='#'){ return; }
    if(!window.confirm('Внесені зміни не буде збережено. Ви впевнені, що бажаєте залишити сторінку?')){
      e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
    } else {
      window.__trifleDirty=false;
    }
  }, true);
  window.addEventListener('beforeunload', function(e){
    if(onForm() && window.__trifleDirty===true){ e.preventDefault(); e.returnValue=''; }
  });
})();
"""


def unsaved_changes_guard() -> rx.Component:
    """Встановлення JS-гварда несохранённых змін. Ідемпотентне; рендериться
    з page_wrapper на кожній сторінці, а гвард сам вмикається лише на маршрутах
    додавання/редагування."""
    return rx.box(
        display="none",
        on_mount=rx.call_script(_UNSAVED_GUARD_SCRIPT),
    )


def empty_placeholder(message: str = "Записи відсутні") -> rx.Component:
    """Заглушка для порожньої таблиці/списку. Стилізована під картку з пунктирною межею."""
    return rx.box(
        rx.text(message, color="gray", size="3", text_align="center"),
        padding="1.5rem",
        border=f"1px dashed {rx.color('gray', 7)}",
        border_radius="0.5rem",
        width="100%",
    )


def delete_with_confirm(
    on_confirm,
    title: str = "Підтвердження видалення",
    description: str = "Ви впевнені, що бажаєте видалити цей запис? Цю дію не можна буде скасувати.",
    trigger: rx.Component | None = None,
    trigger_label: str = "Видалити",
):
    """Кнопка видалення з підтвердженням через rx.alert_dialog.

    За замовчуванням trigger — повнотекстова ghost-кнопка (старий дизайн не
    мав самого діалогу підтвердження, але й не мав іконок-кнопок — тому
    підтвердження лишили як безпечнішу практику, а вигляд кнопки — старий).
    `on_confirm` — обробник, який викликається лише після підтвердження користувачем.
    """
    if trigger is None:
        trigger = button_secondary(trigger_label, color_scheme="red")
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(trigger),
        rx.alert_dialog.content(
            rx.alert_dialog.title(title),
            rx.alert_dialog.description(description),
            rx.flex(
                rx.alert_dialog.cancel(button_secondary("Скасувати")),
                rx.alert_dialog.action(button_primary(trigger_label, color_scheme="red", on_click=on_confirm)),
                spacing="3",
                justify="end",
                margin_top="1rem",
            ),
            max_width="32rem",
        ),
    )


def button_primary(*args, **prop):
    # Старий дизайн не розрізняв «primary»/«secondary» — усі кнопки дій
    # (Створити/Зберегти/Редагувати тощо) були простими ghost-кнопками без
    # заливки (`git show dev:TrifleSklad/administration/workers/frontend.py`).
    prop.setdefault("variant", "ghost")
    prop.setdefault("size", "3")
    return rx.button(*args, **prop)


def button_secondary(*args, **prop):
    prop.setdefault("variant", "ghost")
    prop.setdefault("size", "3")
    return rx.button(*args, **prop)


def input_field(*args, **prop):
    """Єдиний розмір полів уводу по всій програмі (size=2 — той самий
    дефолт, на якому вже стоять усі rx.select, тож форми стають внутрішньо
    узгодженими). setdefault дозволяє перевизначити на місці (щільні поля
    в таблицях лишають свій size=1/фіксовану ширину)."""
    prop.setdefault("size", "2")
    prop.setdefault("width", "100%")
    return rx.input(*args, **prop)


def text_area_field(*args, **prop):
    prop.setdefault("size", "2")
    prop.setdefault("width", "100%")
    return rx.text_area(*args, **prop)


# Затримка «гарячого» пошуку (мс): поле фільтрує по вводу, але з паузою, щоб
# не смикати фільтрацію/запити на кожне натискання клавіші.
SEARCH_DEBOUNCE_MS = 800


def search_field(*args, debounce_timeout: int = SEARCH_DEBOUNCE_MS, **prop):
    """Поле «гарячого» пошуку: input_field, обгорнутий у debounce з паузою.
    Використовуй скрізь, де пошук/фільтрація має спрацьовувати по вводу, а не
    по натисканню кнопки."""
    return rx.debounce_input(
        input_field(*args, **prop),
        debounce_timeout=debounce_timeout,
    )


def button_image_primary(name_icon: str = "package", icon_size: int = 20, *args, **prop):
    return button_primary(
        rx.icon(name_icon, size=icon_size),
        *args,
        padding="0",
        width="2rem",
        height="2rem",
        **prop,
    )


def button_image_secondary(name_icon: str = "package", icon_size: int = 20, *args, **prop):
    return button_secondary(
        rx.icon(name_icon, size=icon_size),
        *args,
        padding="0",
        width="2rem",
        height="2rem",
        **prop,
    )
