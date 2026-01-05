import reflex as rx

from app.state import State


def NotificationHolder() -> rx.Component:
    base_classes = "flex items-start gap-3 border rounded-lg shadow-lg p-4"
    container_classes = rx.cond(
        State.notification_type == "success",
        f"{base_classes} bg-emerald-50 border-emerald-300 text-emerald-900",
        rx.cond(
            State.notification_type == "error",
            f"{base_classes} bg-red-50 border-red-300 text-red-900",
            rx.cond(
                State.notification_type == "warning",
                f"{base_classes} bg-amber-50 border-amber-300 text-amber-900",
                f"{base_classes} bg-sky-50 border-sky-300 text-sky-900",
            ),
        ),
    )

    icon = rx.cond(
        State.notification_type == "success",
        rx.icon("check_check", class_name="h-5 w-5 text-emerald-600"),
        rx.cond(
            State.notification_type == "error",
            rx.icon("triangle-alert", class_name="h-5 w-5 text-red-600"),
            rx.cond(
                State.notification_type == "warning",
                rx.icon("triangle-alert", class_name="h-5 w-5 text-amber-600"),
                rx.icon("info", class_name="h-5 w-5 text-sky-600"),
            ),
        ),
    )

    content = rx.el.div(
        icon,
        rx.el.div(
            rx.el.p(
                State.notification_message,
                class_name="text-sm font-medium leading-snug",
            ),
            class_name="flex-1",
        ),
        rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.close_notification,
            class_name="p-1 rounded-md hover:bg-black/5",
        ),
        class_name=container_classes,
    )

    return rx.cond(
        State.is_notification_open,
        rx.el.div(
            content,
            class_name="fixed top-4 right-4 z-[9999] w-[90vw] max-w-sm",
        ),
        rx.fragment(),
    )
