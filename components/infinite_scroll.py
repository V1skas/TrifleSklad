"""Прокручуваний контейнер із підвантаженням за вимогою (нескінченний скрол).

Викликає подію `on_load_more`, коли користувач прокручує близько до кінця списку.
Подія дроселюється на фронтенді (один виклик на ~600 мс), а бекенд додатково
захищений прапорцем завантаження — щоб одне прокручування не підтягнуло одразу
кілька сторінок. Реалізовано за зразком reflex AutoScroll (ref + scroll-listener
у add_hooks) і Clipboard (виклик відформатованого ланцюга події з хука)."""

from __future__ import annotations

from reflex.components.el.elements.typography import Div
from reflex.constants.compiler import Hooks
from reflex.event import EventChain, EventHandler, no_args_event_spec
from reflex.utils.format import format_prop, wrap
from reflex.vars.base import Var, VarData, get_unique_variable_name


class InfiniteScroll(Div):
    """Div, що довантажує дані при наближенні до кінця прокрутки."""

    # Викликається, коли прокрутка наближається до кінця контейнера.
    on_load_more: EventHandler[no_args_event_spec]

    @classmethod
    def create(cls, *children, **props):
        props.setdefault("overflow_y", "auto")
        props.setdefault("id", get_unique_variable_name())
        return super().create(*children, **props)

    def add_imports(self):
        return {"react": ["useEffect", "useRef"]}

    def add_hooks(self) -> list[str | Var]:
        on_load_more = self.event_triggers.get("on_load_more")
        if on_load_more is None:
            return []
        if isinstance(on_load_more, EventChain):
            chain = wrap(str(format_prop(on_load_more)).strip("{}"), "(")
        else:
            chain = str(on_load_more)

        ref_name = self.get_ref()
        # Унікальне ім'я прапорця-дроселя на основі ref-а (на одній сторінці може
        # бути кілька екземплярів — інакше JS-змінні конфліктують).
        flag = f"{ref_name}_loadMore"
        return [
            Var(
                f"""
const {flag} = useRef(false);
useEffect(() => {{
    const container = {ref_name}.current;
    if (!container) return;
    const handleScroll = () => {{
        if ({flag}.current) return;
        const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
        if (distanceFromBottom <= 150) {{
            {flag}.current = true;
            ({chain})();
            setTimeout(() => {{ {flag}.current = false; }}, 600);
        }}
    }};
    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
}});
""",
                _var_type="str",
                _var_data=VarData(position=Hooks.HookPosition.POST_TRIGGER),
            ),
        ]


infinite_scroll = InfiniteScroll.create
