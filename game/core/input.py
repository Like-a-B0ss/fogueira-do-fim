from __future__ import annotations

from dataclasses import dataclass, field

import pygame
from pygame import Vector2


@dataclass
class InputState:
    move: Vector2 = field(default_factory=Vector2)
    mouse_screen: Vector2 = field(default_factory=Vector2)
    mouse_wheel_y: int = 0
    text_input: str = ""
    sprint: bool = False
    attack_pressed: bool = False
    mouse_interact_pressed: bool = False
    interact_pressed: bool = False
    alt_interact_pressed: bool = False
    confirm_pressed: bool = False
    cancel_pressed: bool = False
    backspace_pressed: bool = False
    quit_requested: bool = False
    chat_toggle_pressed: bool = False
    focus_slot: int | None = None
    build_menu_pressed: bool = False
    menu_up: bool = False
    menu_down: bool = False
    menu_left: bool = False
    menu_right: bool = False
    save_pressed: bool = False
    load_pressed: bool = False
    hud_toggle_pressed: bool = False
    runtime_panel_pressed: bool = False
    audio_debug_pressed: bool = False


class InputSystem:
    def poll(self) -> InputState:
        events = pygame.event.get()
        pressed = pygame.key.get_pressed()

        state = InputState(
            move=Vector2(
                pressed[pygame.K_d] - pressed[pygame.K_a],
                pressed[pygame.K_s] - pressed[pygame.K_w],
            ),
            mouse_screen=Vector2(pygame.mouse.get_pos()),
            sprint=bool(pressed[pygame.K_LSHIFT] or pressed[pygame.K_RSHIFT]),
        )

        for event in events:
            if event.type == pygame.QUIT:
                state.quit_requested = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state.cancel_pressed = True
                elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    state.confirm_pressed = True
                elif event.key == pygame.K_BACKSPACE:
                    state.backspace_pressed = True
                elif event.key in {pygame.K_t, pygame.K_SLASH}:
                    state.chat_toggle_pressed = True
                elif event.key in {pygame.K_UP, pygame.K_w}:
                    state.menu_up = True
                elif event.key in {pygame.K_DOWN, pygame.K_s}:
                    state.menu_down = True
                elif event.key in {pygame.K_LEFT, pygame.K_a}:
                    state.menu_left = True
                elif event.key in {pygame.K_RIGHT, pygame.K_d}:
                    state.menu_right = True
                elif event.key == pygame.K_SPACE:
                    state.confirm_pressed = True
                    state.attack_pressed = True
                    state.text_input += " "
                elif event.key == pygame.K_e:
                    state.interact_pressed = True
                elif event.key == pygame.K_q:
                    state.alt_interact_pressed = True
                elif event.key == pygame.K_b:
                    state.build_menu_pressed = True
                elif event.key == pygame.K_TAB:
                    state.hud_toggle_pressed = True
                elif event.key == pygame.K_m:
                    state.runtime_panel_pressed = True
                elif event.key == pygame.K_F10:
                    state.audio_debug_pressed = True
                elif event.key == pygame.K_F5:
                    state.save_pressed = True
                elif event.key == pygame.K_F9:
                    state.load_pressed = True
                elif event.key == pygame.K_1:
                    state.focus_slot = 1
                elif event.key == pygame.K_2:
                    state.focus_slot = 2
                elif event.key == pygame.K_3:
                    state.focus_slot = 3
                elif event.key == pygame.K_4:
                    state.focus_slot = 4
                elif event.key == pygame.K_5:
                    state.focus_slot = 5
                elif event.key == pygame.K_6:
                    state.focus_slot = 6
                elif event.key == pygame.K_7:
                    state.focus_slot = 7
                elif event.key == pygame.K_8:
                    state.focus_slot = 8
                if event.unicode and event.unicode.isprintable() and event.key not in {
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                    pygame.K_ESCAPE,
                    pygame.K_BACKSPACE,
                    pygame.K_TAB,
                    pygame.K_UP,
                    pygame.K_DOWN,
                    pygame.K_LEFT,
                    pygame.K_RIGHT,
                    pygame.K_t,
                    pygame.K_SLASH,
                }:
                    state.text_input += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                state.attack_pressed = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                state.mouse_interact_pressed = True
            elif event.type == pygame.MOUSEWHEEL:
                state.mouse_wheel_y += int(event.y)

        return state







