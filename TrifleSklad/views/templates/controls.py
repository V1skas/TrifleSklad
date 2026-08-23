import reflex as rx


def button_back(href: str, label: str = "Назад", **prop):
    """Кнопка повернення/скасування — повнотекстова ghost-кнопка (старий
    дизайн: «Скасувати» на формах додавання/редагування, «Повернутись» на
    перегляді, `git show dev:TrifleSklad/administration/workers/frontend.py`).

    `href` — маршрут списку розділу, використовується як fallback, якщо
    власної історії навігації немає (прямий заступ по посиланню/нова
    вкладка). Клас `trifle-back` — маркер для capture-listener'а з
    `_UNSAVED_GUARD_SCRIPT`, який перехоплює клік і підміняє перехід на
    `window.history.back()`, коли історія є (TS-51)."""
    prop["class_name"] = f"trifle-back {prop.get('class_name', '')}".strip()
    return button_secondary(label, on_click=rx.redirect(href), **prop)


def filter_toggle_button(is_open, on_click, active=False, **prop) -> rx.Component:
    """Кнопка-перемикач картки фільтра для шапки підсторінки. Підсвічується
    (solid), коли фільтр застосовано (`active`), інакше ghost — незалежно
    від того, відкрита панель чи згорнута."""
    prop.setdefault("variant", rx.cond(active, "solid", "ghost"))
    prop.setdefault("size", "3")
    return rx.button(
        rx.icon("filter", size=16),
        "Фільтр",
        on_click=on_click,
        **prop,
    )


def filter_shell(is_open, *content) -> rx.Component:
    """Єдина сворачувана картка фільтра/пошуку — завжди присутня в DOM
    (видимість анімується через max-height/opacity/margin-top від `is_open`).
    Оформлення — звичайна `rx.card`, як у фільтрах «Заявок» і «Звітів». Кладеться
    в несоскролливаемий слот `page_wrapper(filter_panel=...)` — між шапкою і тілом
    сторінки, тому не прокручується разом із вмістом."""
    return rx.box(
        rx.card(
            rx.vstack(
                *content,
                spacing="3",
                align="stretch",
                width="100%",
            ),
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


def filter_group(title: str, *content, action=None, wide: bool = False, **prop) -> rx.Component:
    """Візуально відокремлений блок одного критерію фільтра — підпис-заголовок
    (за потреби з контролом `action` праворуч, напр. перемикач «за датою») +
    тонка акцентна рамка з легкою заливкою.

    Тримай вміст в ОДИН рядок контролу (селект, поле пошуку, пара дат поруч) —
    тоді всі блоки в `filter_grid` виходять однакової висоти й сітка лишається
    рівною. Довгі набори прапорців клади не в сітку, а окремою смугою на всю
    ширину (`filter_group(...)` просто наступним дочірнім елементом картки).

    `wide=True` — блок займає дві колонки сітки (для вмісту, що не влазить в
    одну, напр. пара полів дати). Розширення навмисно під медіазапитом: на
    вузькому екрані, де сітка згортається в одну колонку, `span 2` створив би
    другу неявну колонку й спричинив горизонтальне переповнення сторінки."""
    prop.setdefault("width", "100%")
    prop.setdefault("height", "100%")
    if wide:
        span = {"@media (min-width: 52em)": {"grid_column": "span 2"}}
        prop["style"] = {**span, **prop.get("style", {})}
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    title,
                    size="1",
                    weight="bold",
                    color=rx.color("accent", 11),
                    style={"text_transform": "uppercase", "letter_spacing": "0.04em"},
                    white_space="nowrap",
                ),
                rx.spacer(),
                action if action is not None else rx.fragment(),
                spacing="2",
                align="center",
                width="100%",
                min_height="1.5em",
            ),
            *content,
            spacing="2",
            align="stretch",
            width="100%",
        ),
        padding="0.6em 0.75em",
        border=f"1px solid {rx.color('accent', 6)}",
        border_radius="0.5em",
        background_color=rx.color("accent", 2),
        **prop,
    )


def filter_grid(*groups, min_col: str = "14em") -> rx.Component:
    """Рівна сітка однорядкових блоків фільтра (`filter_group`): однакова ширина
    колонок, вирівняна висота (`align-items: stretch`), автоперенос на новий
    рядок. Разом із правилом «один рядок контролу на блок» дає акуратну сітку
    без дір і різнобою."""
    return rx.box(
        *groups,
        display="grid",
        grid_template_columns=f"repeat(auto-fill, minmax({min_col}, 1fr))",
        gap="0.75em",
        align_items="stretch",
        width="100%",
    )


def filter_actions(*buttons) -> rx.Component:
    """Рядок кнопок картки фільтра — завжди праворуч, однаковий у всіх розділах."""
    return rx.hstack(
        rx.spacer(),
        *buttons,
        spacing="3",
        align="center",
        width="100%",
    )


# Гвард несохранённых изменений + лічильник глибини навігації (TS-51).
# Перехоплює будь-яку навігацію (у т.ч. клієнтську через React Router) і
# оновлення/закриття вкладки, коли на сторінці додавання/редагування є
# незбережені зміни. Відкриття посилання в новій вкладці (target=_blank,
# Ctrl/Cmd/Shift/middle-click) НЕ перехоплюється.
#
# Активність визначається МАРШРУТОМ: сторінки додавання закінчуються на "/add",
# редагування містять "/edit/". Тому гвард автоматично працює на ВСІХ формах
# додавання/редагування без окремого маркера на кожній. Встановлюється один раз
# (ідемпотентно) через page_wrapper. «Брудність» відстежуємо в JS: будь-який ввід у
# нативні поля або вибір у Radix (option/switch/radio/checkbox) виставляє прапорець.
# Прапорець скидається при кожній зміні маршруту (React Router йде через history API).
# Кнопки «Зберегти»/«Скасувати» — це <button> з rx.redirect (клієнтська навігація,
# не <a>), тож не блокуються.
#
# TS-51: `__trifleNavDepth` — глибина ВЛАСНОЇ SPA-історії з моменту повної
# завантаги сторінки (скидається в 0 на кожен реальний reload/новий заступ,
# бо `window.__trifleGuardInit` не переживає reload). `pushState` (форвард-
# навігація, у т.ч. `rx.redirect` без `replace`) — інкремент; `popstate`
# (кнопка "назад" браузера) — декремент з підлогою 0; `replaceState`
# (`rx.redirect(replace=True)`) глибину НЕ змінює — заміна запису історії.
#
# Дублі однакового шляху в стеку історії. Перегляд → Редагувати (push) →
# Зберегти (`replace=True` назад на URL перегляду) лишає в стеку ДВА сусідніх
# записи з однаковим шляхом: той, що був до заходу в редагування, і той,
# що з нього зроблений replace. Один `history.back()` переставляє лише на
# сусідній запис — той самий шлях, візуально нічого не змінюється; при N
# послідовних циклах редагування таких дублів N, і без спеціальної обробки
# довелося б клацати «Назад» N разів. Тому клік по `.trifle-back` не робить
# один `history.back()`, а рекурсивно (через `popstate`) проходить усі
# сусідні записи, чий шлях співпадає зі шляхом ДО кліку, і зупиняється на
# першому, що вже відрізняється, — за один клік користувача.
#
# Кнопка `button_back` (клас `trifle-back`) перехоплюється в capture-фазі:
# якщо власна історія є (`depth > 0`) — підміняємо на описаний прохід через
# дублі; інакше лишаємо штатний `rx.redirect(href)` кнопки — це fallback на
# список розділу (прямий заступ по посиланню/нова вкладка). Document-рівневий
# capture-listener гарантовано спрацьовує РАНІШЕ делегованого React-обробника
# кліка на кореневому DOM-вузлі (він — нащадок document у дереві), тому
# `stopImmediatePropagation()` надійно блокує клієнтський `rx.redirect`
# кнопки — той самий прийом, що вже використаний нижче для перехоплення
# `<a href>`.
_UNSAVED_GUARD_SCRIPT = """
(function(){
  if(window.__trifleGuardInit){ return; }
  window.__trifleGuardInit=true;
  window.__trifleDirty=false;
  window.__trifleNavDepth=0;
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
  var resetDirty=function(){ if(location.pathname!==lastPath){ lastPath=location.pathname; window.__trifleDirty=false; } };
  var origPush=history.pushState;
  history.pushState=function(){ var r=origPush.apply(this, arguments); window.__trifleNavDepth+=1; resetDirty(); return r; };
  var origReplace=history.replaceState;
  history.replaceState=function(){ var r=origReplace.apply(this, arguments); resetDirty(); return r; };
  window.addEventListener('popstate', function(){
    window.__trifleNavDepth=Math.max(0, window.__trifleNavDepth-1);
    resetDirty();
  });
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
  document.addEventListener('click', function(e){
    var btn=e.target.closest ? e.target.closest('.trifle-back') : null;
    if(!btn){ return; }
    if(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || (typeof e.button==='number' && e.button!==0)){ return; }
    if(window.__trifleNavDepth<=0){ return; }
    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
    var fromPath=location.pathname;
    var budget=window.__trifleNavDepth;
    var onPop=function(){
      budget-=1;
      if(location.pathname!==fromPath || window.__trifleNavDepth<=0 || budget<=0){
        window.removeEventListener('popstate', onPop);
        return;
      }
      window.history.back();
    };
    window.addEventListener('popstate', onPop);
    window.history.back();
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


def confirm_with_reason_dialog(
    *,
    open,
    on_open_change,
    value,
    on_change,
    on_confirm,
    title: str,
    confirm_label: str = "Підтвердити",
    confirm_color_scheme: str = "blue",
    placeholder: str = "Необов'язково",
    description: str = "",
) -> rx.Component:
    """Діалог підтвердження дії з необов'язковим текстовим полем причини —
    використовується при збереженні повного редагування руху та при
    скасуванні руху (TS-56). Причина йде в аудит-лог, порожнє значення
    допустиме. Кнопки — стандартні стилі Radix (а не плоскі ghost-хелпери
    проекту): нейтральна `soft gray` «Скасувати» + `solid` кнопка підтвердження
    в обраному акцентному кольорі (`confirm_color_scheme`), обидві однакового
    розміру й вирівняні праворуч — симетричний футер діалогу."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(title),
            rx.vstack(
                *([rx.text(description, size="2", color="gray")] if description else []),
                rx.text("Причина (необов'язково)", size="2", weight="medium"),
                text_area_field(
                    placeholder=placeholder,
                    value=value,
                    on_change=on_change,
                    width="100%",
                ),
                rx.flex(
                    rx.button(
                        "Скасувати",
                        variant="soft",
                        color_scheme="gray",
                        size="2",
                        type="button",
                        on_click=on_open_change(False),
                    ),
                    rx.button(
                        confirm_label,
                        variant="solid",
                        color_scheme=confirm_color_scheme,
                        size="2",
                        type="button",
                        on_click=on_confirm,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=open,
        on_open_change=on_open_change,
    )


def cancel_with_reason(
    *,
    open,
    on_open_change,
    value,
    on_change,
    on_open_trigger,
    on_confirm,
    title: str = "Причина скасування",
    trigger_label: str = "Скасувати",
    confirm_label: str = "Застосувати",
    description: str = "",
) -> rx.Component:
    """Кнопка скасування руху з необов'язковою причиною коригування (TS-56).
    На відміну від `delete_with_confirm` (простий alert_dialog «так/ні»),
    відкриває керований станом діалог із текстовим полем причини — тому
    кнопка лише відкриває діалог (`on_open_trigger`), а не викликає дію
    напряму. Кнопка підтвердження в діалозі («Застосувати») — червона, на
    відміну від тригера («Скасувати»/«Видалити»), який лишається як є."""
    return rx.fragment(
        button_secondary(trigger_label, color_scheme="red", on_click=on_open_trigger),
        confirm_with_reason_dialog(
            open=open,
            on_open_change=on_open_change,
            value=value,
            on_change=on_change,
            on_confirm=on_confirm,
            title=title,
            confirm_label=confirm_label,
            confirm_color_scheme="red",
            description=description,
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
