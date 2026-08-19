import reflex as rx


class SearchFilterMixin(rx.State, mixin=True):
    """Спільний прапорець згорнутої картки пошуку/фільтра для довідникових
    списків (product/supplier/storage) — той самий принцип, що й
    `is_filter_open`/`toggle_filter` у `movement/list_mixin.py::MovementListFilterMixin`,
    але без пагінації/дат/статусів, властивих рухам ТМЦ. Конкретний `has_active_filters`
    (які саме поля вважати «фільтр застосовано») реалізує кожен `List*State` сам —
    набір полів фільтра відрізняється по сутностях."""

    is_filter_open: bool = False

    @rx.event
    def toggle_filter(self):
        self.is_filter_open = not self.is_filter_open
