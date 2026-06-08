import reflex as rx


class Logo(rx.ComponentState):
    @classmethod
    def get_component(cls, size="7", *children, **props):
        return rx.center(
            rx.heading("Trifle", size=size, color=rx.color("accent", 1), background_color=rx.color("accent", 9), padding="0.1em", padding_left="0.3em", padding_right="0.3em", border_radius="0.3em"),
            rx.heading("Склад", size=size, color=rx.color("accent", 9), background_color="transparent", padding="0.1em"),

            *children,
            **props,
        )
    
logo = Logo.create