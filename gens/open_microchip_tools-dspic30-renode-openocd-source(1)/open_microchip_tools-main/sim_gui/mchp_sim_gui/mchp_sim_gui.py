from __future__ import annotations

import reflex as rx

from .state import SimState


def index() -> rx.Component:
    return rx.vstack(
        rx.heading("MCHP Firmware Simulator (MVP)"),
        rx.hstack(
            rx.vstack(
                rx.text("Device (dsPIC33 focus)"),
                rx.select(
                    SimState.devices,
                    value=SimState.device,
                    on_change=SimState.set_device,
                    placeholder="Select device",
                    width="380px",
                ),
                rx.button("Init Session", on_click=SimState.init, width="380px"),
                spacing="2",
                align_items="start",
            ),
            rx.vstack(
                rx.text("Firmware path (.hex or .elf)"),
                rx.input(
                    value=SimState.firmware_path,
                    on_change=SimState.set_firmware_path,
                    placeholder=r"C:\path\to\firmware.hex",
                    width="520px",
                ),
                rx.hstack(
                    rx.button("Load", on_click=SimState.load),
                    rx.button("Reset", on_click=SimState.reset),
                    rx.button("Step", on_click=SimState.step),
                    rx.button("Run", on_click=SimState.run),
                    rx.button("Halt", on_click=SimState.halt),
                    rx.button("Refresh", on_click=SimState.refresh),
                    spacing="2",
                ),
                rx.hstack(
                    rx.input(
                        value=SimState.run_steps_count,
                        on_change=SimState.set_run_steps_count,
                        placeholder="Steps (e.g. 1000)",
                        width="180px",
                    ),
                    rx.button("Run N Steps", on_click=SimState.run_steps),
                    spacing="2",
                ),
                rx.hstack(
                    rx.input(
                        value=SimState.breakpoint_addr,
                        on_change=SimState.set_breakpoint_addr,
                        placeholder="Breakpoint addr (e.g. 0x100)",
                        width="260px",
                    ),
                    rx.button("Add BP", on_click=SimState.add_breakpoint),
                    rx.button("Clear BPs", on_click=SimState.clear_breakpoints),
                    spacing="2",
                ),
                spacing="2",
                align_items="start",
            ),
            spacing="4",
            align_items="start",
        ),
        rx.divider(),
        rx.text(f"PC: {SimState.pc}"),
        rx.text(f"IPS: {SimState.ips}"),
        rx.text(f"Firmware loaded: {SimState.firmware_loaded}"),
        rx.hstack(
            rx.vstack(
                rx.text("Breakpoints"),
                rx.text_area(
                    value=SimState.breakpoints_text,
                    is_read_only=True,
                    width="240px",
                    height="160px",
                ),
                spacing="2",
                align_items="start",
            ),
            rx.vstack(
                rx.text("Memory viewer"),
                rx.hstack(
                    rx.select(
                        ["program", "sfr", "nmmr", "file", "peripheral"],
                        value=SimState.mem_space,
                        on_change=SimState.set_mem_space,
                        width="160px",
                    ),
                    rx.input(
                        value=SimState.mem_addr,
                        on_change=SimState.set_mem_addr,
                        placeholder="Address (e.g. 0x0)",
                        width="160px",
                    ),
                    rx.input(
                        value=SimState.mem_size,
                        on_change=SimState.set_mem_size,
                        placeholder="Size (e.g. 64)",
                        width="120px",
                    ),
                    rx.button("Read", on_click=SimState.read_memory),
                    spacing="2",
                ),
                rx.text_area(
                    value=SimState.mem_dump,
                    is_read_only=True,
                    width="720px",
                    height="160px",
                ),
                spacing="2",
                align_items="start",
            ),
            spacing="4",
            align_items="start",
        ),
        rx.text("Program bytes @ PC"),
        rx.text_area(
            value=SimState.mem_at_pc,
            is_read_only=True,
            width="100%",
            height="96px",
        ),
        rx.text("Trace (latest first-to-last)"),
        rx.text_area(
            value=SimState.trace_text,
            is_read_only=True,
            width="100%",
            height="360px",
        ),
        rx.cond(SimState.error != "", rx.text(SimState.error), rx.spacer()),
        spacing="4",
        padding="16px",
        width="100%",
    )


app = rx.App()
app.add_page(index, route="/")
