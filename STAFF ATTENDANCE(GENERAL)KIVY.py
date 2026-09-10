"""
Schools Staff Attendance Management System - Kivy Version

A professional cross-platform staff attendance tracking application with:
- Secure password hashing
- SQLite-backed persistent data storage
- Attendance tracking with late detection
- Term summary reports
- Data export functionality
- Responsive UI design
"""

import os
import re
import sys
import json
import hashlib
import hmac
import shutil
import threading
import urllib.error
import urllib.request
import webbrowser
from functools import partial
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pycountry

from db import Database, DB_FILENAME

try:
    from supabase_db import SupabaseDatabase
except ImportError:
    SupabaseDatabase = None


from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform
from kivy.graphics import Color, RoundedRectangle

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
except ImportError:
    A4 = None
    pdf_canvas = None

# ---------------------------------------------------------------------------
# Platform-specific configuration
# ---------------------------------------------------------------------------
if platform != "android":
    Window.size = (900, 600)

Window.clearcolor = (0.96, 0.97, 0.98, 1)


# ---------------------------------------------------------------------------
# Constants and Configuration
# ---------------------------------------------------------------------------
class AppColors:
    """Centralized color palette for the application."""

    PRIMARY = (0.1176, 0.2275, 0.3725, 1)  # #1E3A5F
    SECONDARY = (0.1451, 0.3882, 0.9216, 1)  # #2563EB
    SUCCESS = (0.0863, 0.6392, 0.2902, 1)  # #16A34A
    WARNING = (0.9608, 0.6196, 0.0431, 1)  # #F59E0B
    DANGER = (0.8627, 0.1098, 0.1098, 1)  # #DC2626
    MUTED = (0.55, 0.55, 0.55, 1)
    ACCENT_BLUE = SECONDARY
    TEXT = (0.1216, 0.1608, 0.2157, 1)  # #1F2937
    BLUE = (1, 1, 1, 1)  # #FFFFFF
    BACKGROUND = (0.9608, 0.9686, 0.9804, 1)  # #F5F7FA
    CARD = (1, 1, 1, 1)  # #FFFFFF
    STRENGTH_COLORS = {
        0: (0.8, 0.2, 0.2, 1),
        1: (0.8, 0.6, 0.2, 1),
        2: (0.8, 0.8, 0.2, 1),
        3: (0.2, 0.8, 0.4, 1),
        4: (0.2, 0.8, 0.2, 1),
    }


class AppConstants:
    """Application constants."""

    APP_TITLE = "Staff Attendance Application"
    APP_VERSION = "1.0.0"
    RELEASE_REPOSITORY = "KeyxDavis/APP-FIXER"
    LOGO_FILENAME = ""
    EXPORT_DIR = "exports"
    LATE_THRESHOLD_HOUR = 7
    LATE_THRESHOLD_MINUTE = 30
    PASSWORD_MIN_SCORE = 2


COUNTRY_TIMEZONES = {
    "Uganda": "Africa/Kampala",
    "Kenya": "Africa/Nairobi",
    "Nigeria": "Africa/Lagos",
    "Ghana": "Africa/Accra",
    "South Africa": "Africa/Johannesburg",
    "United Kingdom": "Europe/London",
    "United Arab Emirates": "Asia/Dubai",
    "India": "Asia/Kolkata",
    "China": "Asia/Shanghai",
    "Japan": "Asia/Tokyo",
    "Australia (Sydney)": "Australia/Sydney",
    "United States (Eastern)": "America/New_York",
    "United States (Pacific)": "America/Los_Angeles",
}

COUNTRY_NAMES = sorted(
    country.name for country in pycountry.countries if getattr(country, "name", "")
)


# ---------------------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------------------
def make_button(
    text: str,
    bg_color: Tuple[float, float, float, float] = AppColors.PRIMARY,
    fg_color: Tuple[float, float, float, float] = AppColors.BLUE,
    height: int = 50,
    font_size: str = "14sp",
    radius: int = 10,
    size_hint_x: Optional[float] = None,
    bold: bool = False,
) -> Button:
    """
    Create a styled button with consistent appearance.

    Args:
        text: Button text
        bg_color: Background color
        fg_color: Text color
        height: Button height in dp
        font_size: Font size
        radius: Corner radius
        size_hint_x: Width hint (None for default)
        bold: Whether text is bold

    Returns:
        Configured Button widget
    """
    btn = Button(
        text=text,
        font_size=font_size,
        bold=bold,
        color=fg_color,
        background_normal="",
        background_down="",
        background_color=(0, 0, 0, 0),
        size_hint_y=None,
        height=dp(height),
    )
    if size_hint_x is not None:
        btn.size_hint_x = size_hint_x

    with btn.canvas.before:
        Color(*bg_color)
        btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(radius)])

    def update_rect(instance, *args) -> None:
        """Update the background rectangle position and size."""
        if hasattr(instance, "_bg_rect"):
            instance._bg_rect.pos = instance.pos
            instance._bg_rect.size = instance.size

    btn.bind(pos=update_rect, size=update_rect)
    return btn


def make_input(
    hint_text: str = "",
    password: bool = False,
    height: int = 45,
    text: str = "",
    multiline: bool = False,
) -> TextInput:
    """
    Create a styled text input field.

    Args:
        hint_text: Placeholder text
        password: Whether to mask input
        height: Input height in dp
        text: Default text
        multiline: Whether to allow multiple lines

    Returns:
        Configured TextInput widget
    """
    return TextInput(
        text=text,
        hint_text=hint_text,
        password=password,
        multiline=multiline,
        font_size="14sp",
        size_hint_y=None,
        height=dp(height),
        padding=(dp(10), dp(10)),
        background_color=(1, 1, 1, 1),
    )


def make_password_row(
    hint_text: str = "Password",
) -> Tuple[BoxLayout, TextInput, Button]:
    """Create a password field with an eye toggle to show or hide the text."""
    row = BoxLayout(
        orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(45)
    )
    text_input = make_input(hint_text=hint_text, password=True)
    eye_btn = Button(
        text="👁",
        size_hint=(None, None),
        width=dp(42),
        height=dp(45),
        font_size="18sp",
        background_color=(0, 0, 0, 0),
        background_normal="",
        background_down="",
        color=AppColors.MUTED,
    )

    def toggle_password_visibility(instance: Any) -> None:
        text_input.password = not text_input.password
        # When password is now hidden (masked), show the "eye" icon to
        # invite the user to reveal it; when visible, show "🙈" to
        # invite them to hide it again. The icon must reflect the new
        # state, not the state before the toggle.
        instance.text = "👁" if text_input.password else "🙈"

    eye_btn.bind(on_press=toggle_password_visibility)
    row.add_widget(text_input)
    row.add_widget(eye_btn)
    return row, text_input, eye_btn


def info_popup(title: str, message: str) -> Popup:
    """
    Display an informational popup.

    Args:
        title: Popup title
        message: Popup message

    Returns:
        Popup instance
    """
    content_box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))

    # Give the content a solid yellow background so the black message text
    # is always readable, regardless of Kivy's default popup theme.
    with content_box.canvas.before:
        Color(1, 0.85, 0.1, 1)  # yellow
        content_box._bg_rect = RoundedRectangle(
            pos=content_box.pos, size=content_box.size, radius=[dp(10)]
        )

    def _update_content_bg(instance, *args) -> None:
        if hasattr(instance, "_bg_rect"):
            instance._bg_rect.pos = instance.pos
            instance._bg_rect.size = instance.size

    content_box.bind(pos=_update_content_bg, size=_update_content_bg)

    content_box.add_widget(
        Label(
            text=message,
            text_size=(dp(400), None),
            color=(0, 0, 0, 1),  # black text
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(100),
        )
    )
    close_btn = make_button(
        "OK", bg_color=AppColors.PRIMARY, height=40, font_size="12sp"
    )
    content_box.add_widget(close_btn)

    popup = Popup(
        title=title,
        content=content_box,
        size_hint=(0.85, 0.45),
        auto_dismiss=True,
        separator_height=0,
    )
    close_btn.bind(on_press=popup.dismiss)
    popup.open()
    return popup


def confirm_popup(
    title: str,
    message: str,
    on_yes: Callable,
    confirm_text: str = "Yes",
    cancel_text: str = "Cancel",
) -> Popup:
    """
    Display a confirmation popup with yes/no buttons.

    Args:
        title: Popup title
        message: Popup message
        on_yes: Callback for confirmation
        confirm_text: Text for confirm button
        cancel_text: Text for cancel button

    Returns:
        Popup instance
    """
    box = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(12))

    # Same fix as info_popup: give the content a solid white background so
    # AppColors.TEXT (near-black) is readable against Kivy's dark popup skin.
    with box.canvas.before:
        Color(1, 1, 1, 1)
        box._bg_rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(10)])

    def _update_box_bg(instance, *args) -> None:
        if hasattr(instance, "_bg_rect"):
            instance._bg_rect.pos = instance.pos
            instance._bg_rect.size = instance.size

    box.bind(pos=_update_box_bg, size=_update_box_bg)

    box.add_widget(
        Label(
            text=message,
            text_size=(dp(280), None),
            color=AppColors.TEXT,
            halign="center",
        )
    )

    btn_row = BoxLayout(
        orientation="horizontal",
        spacing=dp(8),
        size_hint_y=None,
        height=dp(48),
    )
    popup = Popup(
        title=title,
        content=box,
        size_hint=(0.8, 0.35),
        auto_dismiss=True,
        separator_height=0,
    )

    def confirm(*args) -> None:
        """Handle confirmation."""
        popup.dismiss()
        on_yes()

    yes_btn = make_button(confirm_text, bg_color=AppColors.DANGER)
    yes_btn.bind(on_press=confirm)
    cancel_btn = make_button(cancel_text, bg_color=AppColors.MUTED)
    cancel_btn.bind(on_press=lambda *_: popup.dismiss())

    btn_row.add_widget(yes_btn)
    btn_row.add_widget(cancel_btn)
    box.add_widget(btn_row)
    popup.open()
    return popup


def hash_password(password: str) -> str:
    """
    Hash a password using salted scrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return "scrypt$16384$8$1${}${}".format(salt.hex(), digest.hex())


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify scrypt passwords and support legacy SHA-256 hashes."""
    if stored_hash.startswith("scrypt$"):
        try:
            _, n, r, p, salt_hex, digest_hex = stored_hash.split("$")
            digest = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=int(n),
                r=int(r),
                p=int(p),
            )
            return hmac.compare_digest(digest.hex(), digest_hex)
        except (TypeError, ValueError):
            return False

    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, stored_hash)


def get_logo_path() -> str:
    """
    Get the path to the logo image file.

    Works both running from source and when packaged with PyInstaller.
    Under PyInstaller's --onefile mode, bundled data files are extracted
    to a temp folder at sys._MEIPASS at runtime, NOT next to the .exe, so
    __file__ alone is not reliable once the app is packaged.

    Returns:
        Absolute path to logo file
    """
    app = App.get_running_app()
    configured_path = getattr(app, "branding_logo_path", "") if app else ""
    if configured_path and os.path.isfile(configured_path):
        return configured_path

    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        AppConstants.LOGO_FILENAME,
        "asolo.png",
        "logo.png",
        "crnps_logo.png",
    ]
    for filename in candidates:
        candidate = os.path.join(base_dir, filename)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(base_dir, AppConstants.LOGO_FILENAME)


def add_logo_if_present(
    parent: BoxLayout, size: Tuple[int, int] = (90, 90)
) -> Optional[Image]:
    """
    Add logo to parent layout if logo file exists.

    Args:
        parent: Parent layout to add logo to
        size: Logo size in dp

    Returns:
        Image widget if logo found, None otherwise
    """
    logo_path = get_logo_path()
    if not os.path.exists(logo_path):
        return None

    try:
        img = Image(
            source=logo_path,
            size_hint=(None, None),
            size=(dp(size[0]), dp(size[1])),
            fit_mode="contain",
            pos_hint={"center_x": 0.5},
        )
        parent.add_widget(img)
        return img
    except (OSError, ValueError, TypeError):
        return None


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email string to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


# ---------------------------------------------------------------------------
# Base Screen Class
# ---------------------------------------------------------------------------
class BaseScreen(Screen):
    """Base class for all screens with common functionality."""

    def add_widget(self, widget: Any, *args: Any, **kwargs: Any) -> None:
        """Place each screen's root layout in a vertical scroll container."""
        if not isinstance(widget, ScrollView):
            content = widget
            scroll = ScrollView(do_scroll_x=False, bar_width=dp(8))
            content.size_hint_y = None

            def update_content_height(*_args: Any) -> None:
                content.height = max(content.minimum_height, scroll.height)

            content.bind(minimum_height=update_content_height)
            scroll.bind(size=update_content_height)
            scroll.add_widget(content)
            widget = scroll
        super().add_widget(widget, *args, **kwargs)

    def get_app(self) -> "AsoloAttendanceApp":
        """Get the application instance."""
        return App.get_running_app()

    def navigate_to(self, screen_name: str) -> None:
        """Navigate to a different screen."""
        self.manager.current = screen_name

    def show_error(self, message: str) -> None:
        """Show an error popup."""
        info_popup("Error", message)

    def show_success(self, message: str) -> None:
        """Show a success popup."""
        info_popup("Success", message)

    def show_info(self, message: str) -> None:
        """Show an information popup."""
        info_popup("Information", message)

    def require_admin(self) -> bool:
        """Return whether the signed-in user may perform admin actions."""
        if self.is_admin():
            return True
        self.show_error("Administrator permission is required for this action.")
        return False

    def is_admin(self) -> bool:
        """Return whether the signed-in user has the administrator role."""
        app = self.get_app()
        account = (
            app.db.get_user(app.current_user) if app.current_user and app.db else None
        )
        return bool(account and account.get("role") == "admin")

    def clear_text_inputs(self, *inputs: Optional[TextInput]) -> None:
        """Clear multiple text input fields."""
        for text_input in inputs:
            if text_input:
                text_input.text = ""


# ---------------------------------------------------------------------------
# Branding Setup Screen
# ---------------------------------------------------------------------------
class BrandingSetupScreen(BaseScreen):
    """Collect the school name and compulsory logo before authentication."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.school_name_input: Optional[TextInput] = None
        self.logo_path = ""
        self.logo_label: Optional[Label] = None
        self.build_ui()

    def build_ui(self) -> None:
        layout = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(12))
        layout.add_widget(
            Label(
                text="Set Up or Update Your School",
                font_size="24sp",
                bold=True,
                color=AppColors.PRIMARY,
                size_hint_y=None,
                height=dp(42),
            )
        )
        layout.add_widget(
            Label(
                text="Enter your school name and choose its logo to continue.",
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(30),
            )
        )
        self.school_name_input = make_input(hint_text="School name")
        layout.add_widget(self.school_name_input)

        choose_btn = make_button("Choose School Logo", bg_color=AppColors.SECONDARY)
        choose_btn.bind(on_press=self.choose_logo)
        layout.add_widget(choose_btn)
        self.logo_label = Label(
            text="No logo selected (required)",
            color=AppColors.DANGER,
            size_hint_y=None,
            height=dp(30),
        )
        layout.add_widget(self.logo_label)

        continue_btn = make_button("Continue to Sign In", bg_color=AppColors.SUCCESS)
        continue_btn.bind(on_press=self.save_setup)
        layout.add_widget(continue_btn)
        self.add_widget(layout)

    def on_pre_enter(self, *args: Any) -> None:
        """Load the saved school branding when setup is opened."""
        app = self.get_app()
        if self.school_name_input:
            self.school_name_input.text = app.school_name
        self.logo_path = app.branding_logo_path
        if self.logo_label:
            if self.logo_path and os.path.isfile(self.logo_path):
                self.logo_label.text = os.path.basename(self.logo_path)
                self.logo_label.color = AppColors.SUCCESS
            else:
                self.logo_label.text = "No logo selected (required)"
                self.logo_label.color = AppColors.DANGER

    def choose_logo(self, instance: Any) -> None:
        chooser = FileChooserListView(
            path=os.path.expanduser("~"),
            filters=["*.png", "*.jpg", "*.jpeg", "*.webp"],
        )
        buttons = BoxLayout(
            orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(48)
        )
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(chooser)
        select_btn = make_button("Use Selected Logo", bg_color=AppColors.SUCCESS)
        cancel_btn = make_button("Cancel", bg_color=AppColors.MUTED)
        buttons.add_widget(select_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)
        popup = Popup(
            title="Choose School Logo",
            content=content,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        def select_logo(*args: Any) -> None:
            if not chooser.selection:
                self.show_error("Please select a logo image.")
                return
            self.logo_path = chooser.selection[0]
            if self.logo_label:
                self.logo_label.text = os.path.basename(self.logo_path)
                self.logo_label.color = AppColors.SUCCESS
            popup.dismiss()

        select_btn.bind(on_press=select_logo)
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        popup.open()

    def save_setup(self, instance: Any) -> None:
        school_name = (
            self.school_name_input.text.strip() if self.school_name_input else ""
        )
        if not school_name:
            self.show_error("Please enter your school name.")
            return
        if not self.logo_path or not os.path.isfile(self.logo_path):
            self.show_error("A school logo is required before continuing.")
            return

        app = self.get_app()
        if not app.save_branding(school_name, self.logo_path):
            self.show_error(
                "Unable to save the school branding. Check that the image "
                "is a valid PNG, JPG, JPEG, or WEBP file."
            )
            return
        app._set_window_icon()
        app.refresh_branding_screens()
        self.navigate_to("login")


# ---------------------------------------------------------------------------
# Login Screen
# ---------------------------------------------------------------------------
class LoginScreen(BaseScreen):
    """Login screen for user authentication."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.username_input: Optional[TextInput] = None
        self.password_input: Optional[TextInput] = None
        self.school_spinner: Optional[Spinner] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the login UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))

        add_logo_if_present(layout, size=(90, 90))
        app = self.get_app()

        layout.add_widget(
            Label(
                text=app.school_name,
                font_size="22sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(36),
            )
        )
        layout.add_widget(
            Label(
                text="Staff Attendance Management System",
                font_size="14sp",
                color=AppColors.MUTED,
                size_hint_y=None,
                height=dp(26),
            )
        )

        layout.add_widget(Label(size_hint_y=None, height=dp(10)))

        card = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(320),
        )

        self.username_input = make_input(hint_text="Username")
        card.add_widget(self.username_input)

        if app.school_ids:
            self.school_spinner = Spinner(
                text=app.school_ids[0],
                values=app.school_ids,
                font_size="14sp",
                color=AppColors.TEXT,
                background_normal="",
                background_color=(1, 1, 1, 1),
                size_hint_y=None,
                height=dp(45),
            )
            card.add_widget(self.school_spinner)

        password_row, self.password_input, _ = make_password_row(hint_text="Password")
        card.add_widget(password_row)

        login_btn = make_button("Sign In", bg_color=AppColors.ACCENT_BLUE, bold=True)
        login_btn.bind(on_press=self.handle_login)
        card.add_widget(login_btn)

        register_btn = make_button(
            "Create New Account",
            bg_color=AppColors.WARNING,
            height=42,
            font_size="12sp",
        )
        register_btn.bind(on_press=self.go_register)
        card.add_widget(register_btn)

        forgot_btn = Button(
            text="Forgot Password?",
            font_size="12sp",
            background_color=(0, 0, 0, 0),
            background_normal="",
            color=AppColors.ACCENT_BLUE,
            size_hint_y=None,
            height=dp(30),
        )
        forgot_btn.bind(on_press=self.show_forgot_password)
        card.add_widget(forgot_btn)

        update_branding_btn = Button(
            text="Update School Name & Logo",
            font_size="12sp",
            background_color=(0, 0, 0, 0),
            background_normal="",
            color=AppColors.PRIMARY,
            size_hint_y=None,
            height=dp(30),
        )
        update_branding_btn.bind(on_press=self.open_branding_setup)
        card.add_widget(update_branding_btn)

        layout.add_widget(card)
        layout.add_widget(Label(size_hint_y=None, height=dp(10)))

        exit_btn = make_button("Exit", bg_color=AppColors.DANGER)
        exit_btn.bind(on_press=lambda _: App.get_running_app().stop())
        layout.add_widget(exit_btn)

        self.add_widget(layout)

    def on_pre_enter(self, *args) -> None:
        """Clear password field when entering screen."""
        if self.password_input:
            self.password_input.text = ""

    def go_register(self, instance: Any) -> None:
        """Navigate to registration screen."""
        self.navigate_to("register")

    def handle_login(self, instance: Any) -> None:
        """Handle login button press."""
        if not self.username_input or not self.password_input:
            return

        username = self.username_input.text.strip()
        password = self.password_input.text

        if not username or not password:
            self.show_error("Please enter both username and password")
            return

        app = self.get_app()
        if SupabaseDatabase is not None and isinstance(app.db, SupabaseDatabase):
            selected_school = (
                self.school_spinner.text if self.school_spinner else app.school_ids[0]
            )
            app.select_school(selected_school)
            account = app.db.authenticate_user(username, password)
            if not account:
                self.show_error("Invalid credentials")
                return
            app.current_user = username
            self.navigate_to("dashboard")
            self.show_success(f"Welcome {username}!")
            return

        account = app.db.get_user(username)

        is_valid = bool(account and verify_password(password, account["password_hash"]))

        if not is_valid:
            self.show_error("Invalid credentials")
            return

        if account and not account["password_hash"].startswith("scrypt$"):
            app.db.update_user(
                username,
                username,
                hash_password(password),
                account["email"],
            )

        app.current_user = username
        self.navigate_to("dashboard")
        self.show_success(f"Welcome {username}!")

    def show_forgot_password(self, instance: Any) -> None:
        """Display forgot password help."""
        self.show_info(
            "Please contact the system administrator to reset your password."
        )

    def open_branding_setup(self, instance: Any) -> None:
        """Open the school branding editor from the login page."""
        self.navigate_to("setup")


# ---------------------------------------------------------------------------
# Register Screen
# ---------------------------------------------------------------------------
class RegisterScreen(BaseScreen):
    """User registration screen."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.reg_username: Optional[TextInput] = None
        self.reg_email: Optional[TextInput] = None
        self.reg_password: Optional[TextInput] = None
        self.reg_confirm: Optional[TextInput] = None
        self.strength_label: Optional[Label] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the registration UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))

        layout.add_widget(
            Label(
                text="Create Account",
                font_size="22sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(50),
            )
        )

        scroll = ScrollView()
        form = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(10),
            size_hint_y=None,
        )
        form.bind(minimum_height=form.setter("height"))

        self.reg_username = make_input(hint_text="Username")
        form.add_widget(self.reg_username)

        self.reg_email = make_input(hint_text="Email Address")
        form.add_widget(self.reg_email)

        password_row, self.reg_password, _ = make_password_row(hint_text="Password")
        form.add_widget(password_row)

        confirm_row, self.reg_confirm, _ = make_password_row(
            hint_text="Confirm Password"
        )
        form.add_widget(confirm_row)

        self.strength_label = Label(
            text="Password strength: ",
            font_size="12sp",
            color=AppColors.MUTED,
            size_hint_y=None,
            height=dp(25),
        )
        form.add_widget(self.strength_label)
        if self.reg_password:
            self.reg_password.bind(text=self.update_strength)

        register_btn = make_button(
            "Create Account", bg_color=AppColors.SUCCESS, bold=True
        )
        register_btn.bind(on_press=self.handle_register)
        form.add_widget(register_btn)

        scroll.add_widget(form)
        layout.add_widget(scroll)

        back_btn = make_button("Back to Login", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def on_pre_enter(self, *args) -> None:
        """Clear all input fields when entering screen."""
        self.clear_text_inputs(
            self.reg_username,
            self.reg_email,
            self.reg_password,
            self.reg_confirm,
        )
        if self.strength_label:
            self.strength_label.text = "Password strength: "

    def go_back(self) -> None:
        """Navigate back to login screen."""
        self.navigate_to("login")

    def update_strength(self, instance: Any, value: str) -> None:
        """Update password strength indicator."""
        if not self.strength_label:
            return

        score = self._password_strength(value)
        labels = {
            0: "Very weak",
            1: "Weak",
            2: "Fair",
            3: "Strong",
            4: "Very strong",
        }
        self.strength_label.text = (
            f"Password strength: {labels.get(score, 'Very weak')}"
        )
        self.strength_label.color = AppColors.STRENGTH_COLORS.get(
            score, (0.8, 0.2, 0.2, 1)
        )

    @staticmethod
    def _password_strength(password: str) -> int:
        """
        Calculate password strength score.

        Args:
            password: Password to evaluate

        Returns:
            Score from 0 to 4
        """
        score = 0
        if len(password) >= 8:
            score += 1
        if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
            score += 1
        if re.search(r"\d", password):
            score += 1
        if re.search(r"[^A-Za-z0-9]", password):
            score += 1
        return score

    def handle_register(self, instance: Any) -> None:
        """Handle registration button press."""
        if not all(
            [
                self.reg_username,
                self.reg_email,
                self.reg_password,
                self.reg_confirm,
            ]
        ):
            return

        username = self.reg_username.text.strip()
        email = self.reg_email.text.strip().lower()
        password = self.reg_password.text
        confirm = self.reg_confirm.text

        if not all([username, email, password, confirm]):
            self.show_error("Please fill all fields")
            return

        if not validate_email(email):
            self.show_error("Please enter a valid email address")
            return

        if password != confirm:
            self.show_error("Passwords do not match")
            return

        if self._password_strength(password) < AppConstants.PASSWORD_MIN_SCORE:
            self.show_error("Password too weak. Use mixed case, numbers and symbols.")
            return

        app = self.get_app()
        # create_user checks uniqueness and inserts atomically -- no separate
        # "does it exist" check needed, which also avoids a race condition
        # between checking and inserting.
        if SupabaseDatabase is not None and isinstance(app.db, SupabaseDatabase):
            self.show_error(
                "Cloud accounts must be created in Supabase Auth and added "
                "to the school's membership list."
            )
            return
        else:
            created = app.db.create_user(username, hash_password(password), email)
        if not created:
            self.show_error("Username already exists")
            return

        self.show_success(f"Account created for {username}")
        self.navigate_to("login")


# ---------------------------------------------------------------------------
# Change Information Screen
# ---------------------------------------------------------------------------
class ChangeInfoScreen(BaseScreen):
    """Screen for updating the signed-in user's information."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current_password_input: Optional[TextInput] = None
        self.username_input: Optional[TextInput] = None
        self.email_input: Optional[TextInput] = None
        self.new_password_input: Optional[TextInput] = None
        self.confirm_password_input: Optional[TextInput] = None
        self.strength_label: Optional[Label] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the change information UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))

        layout.add_widget(
            Label(
                text="Change Information",
                font_size="22sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(45),
            )
        )

        scroll = ScrollView()
        form = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(10),
            size_hint_y=None,
        )
        form.bind(minimum_height=form.setter("height"))

        current_password_row, self.current_password_input, _ = make_password_row(
            hint_text="Current Password"
        )
        form.add_widget(current_password_row)

        self.username_input = make_input(hint_text="New Username")
        form.add_widget(self.username_input)

        self.email_input = make_input(hint_text="New Email Address")
        form.add_widget(self.email_input)

        new_password_row, self.new_password_input, _ = make_password_row(
            hint_text="New Password"
        )
        form.add_widget(new_password_row)

        confirm_password_row, self.confirm_password_input, _ = make_password_row(
            hint_text="Confirm New Password"
        )
        form.add_widget(confirm_password_row)

        self.strength_label = Label(
            text="Password strength: ",
            font_size="12sp",
            color=AppColors.MUTED,
            size_hint_y=None,
            height=dp(25),
        )
        form.add_widget(self.strength_label)
        if self.new_password_input:
            self.new_password_input.bind(text=self.update_strength)

        save_btn = make_button(
            "Update Information", bg_color=AppColors.SUCCESS, bold=True
        )
        save_btn.bind(on_press=self.handle_update)
        form.add_widget(save_btn)

        scroll.add_widget(form)
        layout.add_widget(scroll)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def on_pre_enter(self, *args) -> None:
        """Pre-fill values for the current user."""
        app = self.get_app()
        current_user = app.current_user
        current_account = app.db.get_user(current_user) if current_user else None
        current_account = current_account or {}

        if self.username_input:
            self.username_input.text = current_user or ""
        if self.email_input:
            self.email_input.text = current_account.get("email", "")
        self.clear_text_inputs(
            self.current_password_input,
            self.new_password_input,
            self.confirm_password_input,
        )
        if self.strength_label:
            self.strength_label.text = "Password strength: "

    def go_back(self) -> None:
        """Navigate back to the dashboard."""
        self.navigate_to("dashboard")

    def update_strength(self, instance: Any, value: str) -> None:
        """Update password strength indicator."""
        if not self.strength_label:
            return

        score = RegisterScreen._password_strength(value)
        labels = {
            0: "Very weak",
            1: "Weak",
            2: "Fair",
            3: "Strong",
            4: "Very strong",
        }
        self.strength_label.text = (
            f"Password strength: {labels.get(score, 'Very weak')}"
        )
        self.strength_label.color = AppColors.STRENGTH_COLORS.get(
            score, (0.8, 0.2, 0.2, 1)
        )

    def handle_update(self, instance: Any) -> None:
        """Update the current user information."""
        app = self.get_app()
        current_user = app.current_user

        if not current_user:
            self.show_error("No active user session found")
            return

        current_record = app.db.get_user(current_user)
        if not current_record:
            self.show_error("No active user session found")
            return

        if not all(
            [
                self.current_password_input,
                self.username_input,
                self.email_input,
                self.new_password_input,
                self.confirm_password_input,
            ]
        ):
            return

        current_password = self.current_password_input.text
        new_username = self.username_input.text.strip()
        new_email = self.email_input.text.strip().lower()
        new_password = self.new_password_input.text
        confirm_password = self.confirm_password_input.text

        if not current_password:
            self.show_error("Please enter your current password")
            return

        if SupabaseDatabase is not None and isinstance(app.db, SupabaseDatabase):
            if not app.db.authenticate_user(current_user, current_password):
                self.show_error("Current password is incorrect")
                return
        elif not verify_password(current_password, current_record["password_hash"]):
            self.show_error("Current password is incorrect")
            return

        if not new_username or not new_email:
            self.show_error("Username and email are required")
            return

        if not validate_email(new_email):
            self.show_error("Please enter a valid email address")
            return

        if new_password or confirm_password:
            if new_password != confirm_password:
                self.show_error("New passwords do not match")
                return
            if (
                RegisterScreen._password_strength(new_password)
                < AppConstants.PASSWORD_MIN_SCORE
            ):
                self.show_error(
                    "Password too weak. Use mixed case, numbers and symbols."
                )
                return

        if SupabaseDatabase is not None and isinstance(app.db, SupabaseDatabase):
            updated = app.db.update_account(
                current_user, new_username, new_password or None, new_email
            )
        else:
            new_password_hash = (
                hash_password(new_password)
                if new_password
                else current_record["password_hash"]
            )
            updated = app.db.update_user(
                current_user, new_username, new_password_hash, new_email
            )
        if not updated:
            self.show_error("Username already exists")
            return

        app.current_user = new_username
        self.show_success("Your information has been updated successfully")
        self.navigate_to("dashboard")


# ---------------------------------------------------------------------------
# Dashboard Screen
# ---------------------------------------------------------------------------
class DashboardScreen(BaseScreen):
    """Main dashboard screen with menu and statistics."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.user_label: Optional[Label] = None
        self.staff_count_label: Optional[Label] = None
        self.present_label: Optional[Label] = None
        self.absent_label: Optional[Label] = None
        self.rate_label: Optional[Label] = None
        self.late_label: Optional[Label] = None
        self.rate_progress: Optional[ProgressBar] = None
        self.activity_label: Optional[Label] = None
        self.clock_label: Optional[Label] = None
        self.country_spinner: Optional[Button] = None
        self.school_spinner: Optional[Spinner] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the dashboard UI."""
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(8),
        )

        self._add_header(layout)
        self._add_stats(layout)
        self._add_overview(layout)
        self._add_quick_actions(layout)
        self._add_menu(layout)

        self.add_widget(layout)
        Clock.schedule_once(self.update_stats, 0.1)
        Clock.schedule_interval(self.update_stats, 60)
        Clock.schedule_interval(self.update_clock, 1)

    def _add_header(self, parent: BoxLayout) -> None:
        """Add header section."""
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(82))
        header_text_col = BoxLayout(orientation="vertical", size_hint_x=0.3)
        header_text_col.add_widget(
            Label(
                text="Dashboard",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                halign="left",
            )
        )
        self.user_label = Label(
            text="",
            font_size="12sp",
            color=AppColors.MUTED,
            halign="left",
        )
        header_text_col.add_widget(self.user_label)
        app = self.get_app()
        if len(app.school_ids) > 1:
            self.school_spinner = Spinner(
                text=app.active_school_id,
                values=app.school_ids,
                font_size="11sp",
                color=AppColors.TEXT,
                background_normal="",
                background_color=(1, 1, 1, 1),
                size_hint_y=None,
                height=dp(34),
            )
            self.school_spinner.bind(text=self.change_school)
            header_text_col.add_widget(self.school_spinner)
        header.add_widget(header_text_col)
        clock_area = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            padding=(0, dp(4)),
            size_hint_x=0.38,
        )
        self.clock_label = Label(
            text="",
            font_size="12sp",
            color=AppColors.TEXT,
            halign="center",
            valign="middle",
        )
        self.clock_label.bind(
            size=lambda instance, value: setattr(
                instance, "text_size", (value[0], None)
            )
        )
        clock_area.add_widget(self.clock_label)

        self.country_spinner = make_button(
            "Select Country",
            bg_color=(1, 1, 1, 1),
            fg_color=AppColors.TEXT,
            height=34,
            font_size="11sp",
        )
        self.country_spinner.bind(on_press=self.open_country_selector)
        clock_area.add_widget(self.country_spinner)
        header.add_widget(clock_area)

        button_area = BoxLayout(
            orientation="horizontal",
            spacing=dp(6),
            size_hint_x=0.32,
        )

        change_info_btn = make_button(
            "Change Information",
            bg_color=AppColors.PRIMARY,
            font_size="11sp",
            height=40,
        )
        change_info_btn.bind(on_press=self.go_change_info)
        button_area.add_widget(change_info_btn)

        logout_btn = make_button(
            "Logout",
            bg_color=AppColors.DANGER,
            font_size="12sp",
            height=40,
        )
        logout_btn.bind(on_press=self.handle_logout)
        button_area.add_widget(logout_btn)

        header.add_widget(button_area)
        parent.add_widget(header)
        self.update_clock()

    def open_country_selector(self, *args: Any) -> None:
        """Show every ISO country in a scrollable selection popup."""
        country_list = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        country_list.bind(minimum_height=country_list.setter("height"))
        popup = Popup(
            title="Select Country",
            size_hint=(0.86, 0.86),
            auto_dismiss=True,
        )
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(country_list)
        popup.content = scroll

        for country in COUNTRY_NAMES:
            country_button = Button(
                text=country,
                color=AppColors.TEXT,
                background_normal="",
                background_color=(1, 1, 1, 1),
                size_hint_y=None,
                height=dp(38),
                halign="left",
                padding=(dp(12), 0),
            )
            country_button.bind(
                on_press=lambda _button, selected=country: self.change_country(
                    selected, popup
                )
            )
            country_list.add_widget(country_button)

        popup.open()

    def change_country(self, country: str, popup: Popup) -> None:
        """Set the dashboard clock timezone for the selected country."""
        if self.country_spinner:
            self.country_spinner.text = country
        self.get_app().selected_timezone = COUNTRY_TIMEZONES.get(country, "UTC")
        self.update_clock()
        popup.dismiss()

    def change_school(self, spinner: Spinner, school_id: str) -> None:
        """Switch the dashboard to another authorized school."""
        app = self.get_app()
        if app.select_school(school_id):
            app.refresh_staff_list()
            app.refresh_attendance_data()
            self.update_stats()
            self.user_label.text = f"Signed in as {app.current_user}"
        else:
            spinner.text = app.active_school_id
            self.show_error("You do not have access to that school")

    def update_clock(self, *args) -> None:
        """Refresh the dashboard date and time for the selected timezone."""
        if not self.clock_label:
            return

        app = self.get_app()
        try:
            current = datetime.now(ZoneInfo(app.selected_timezone))
        except ZoneInfoNotFoundError:
            current = datetime.now().astimezone()

        self.clock_label.text = (
            f"{current.strftime('%A, %d %B %Y')}\n" f"{current.strftime('%I:%M:%S %p')}"
        )

    def _add_stats(self, parent: BoxLayout) -> None:
        """Add statistics section."""
        stats = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            spacing=dp(10),
        )
        self.staff_count_label = Label(
            text="Staff: 0",
            font_size="14sp",
            bold=True,
            color=(0.2, 0.6, 0.2, 1),
        )
        stats.add_widget(self.staff_count_label)
        self.present_label = Label(
            text="Present: 0",
            font_size="14sp",
            bold=True,
            color=(0.2, 0.4, 0.8, 1),
        )
        stats.add_widget(self.present_label)
        self.absent_label = Label(
            text="Absent: 0",
            font_size="14sp",
            bold=True,
            color=(0.8, 0.2, 0.2, 1),
        )
        stats.add_widget(self.absent_label)
        parent.add_widget(stats)

    def _add_overview(self, parent: BoxLayout) -> None:
        """Add the attendance rate and today's operational summary."""
        overview = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(6),
            size_hint_y=None,
            height=dp(112),
        )
        self.rate_label = Label(
            text="Attendance rate: 0%",
            color=AppColors.TEXT,
            font_size="14sp",
            bold=True,
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )
        overview.add_widget(self.rate_label)
        self.rate_progress = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(12),
        )
        overview.add_widget(self.rate_progress)
        self.late_label = Label(
            text="Late arrivals: 0",
            color=AppColors.WARNING,
            font_size="12sp",
            halign="left",
            size_hint_y=None,
            height=dp(22),
        )
        overview.add_widget(self.late_label)
        self.activity_label = Label(
            text="No attendance recorded today.",
            color=AppColors.MUTED,
            font_size="12sp",
            halign="left",
            size_hint_y=None,
            height=dp(22),
        )
        overview.add_widget(self.activity_label)
        parent.add_widget(overview)

    def _add_quick_actions(self, parent: BoxLayout) -> None:
        """Add fast access buttons for the most common daily actions."""
        actions = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(46),
        )
        for text, callback, color in (
            ("Take Attendance", self.go_attendance, AppColors.SUCCESS),
            ("View Attendance", self.go_view_attendance, AppColors.SECONDARY),
            ("Register Staff", self.go_register_staff, AppColors.PRIMARY),
        ):
            button = make_button(text, bg_color=color, font_size="11sp", height=42)
            button.bind(on_press=callback)
            actions.add_widget(button)
        parent.add_widget(actions)

    def _add_menu(self, parent: BoxLayout) -> None:
        """Add menu buttons."""
        menu_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        menu_grid.bind(minimum_height=menu_grid.setter("height"))

        menu_items = [
            ("Register Staff", self.go_register_staff, AppColors.PRIMARY),
            ("Register Staff Exit", self.go_exit_attendance, AppColors.WARNING),
            ("View Staff", self.go_view_staff, AppColors.PRIMARY),
            ("Take Attendance", self.go_attendance, AppColors.SUCCESS),
            ("View Attendance", self.go_view_attendance, AppColors.PRIMARY),
            ("Absent Staff", self.go_absent_staff, AppColors.WARNING),
            ("Report", self.go_report, AppColors.PRIMARY),
            ("Activity Log", self.go_activity_log, AppColors.ACCENT_BLUE),
            ("Print Report", self.go_print_report, AppColors.SUCCESS),
            ("Delete Staff", self.go_delete_staff, AppColors.DANGER),
            ("Export Data", self.go_pdf_report, AppColors.PRIMARY),
        ]

        for text, callback, color in menu_items:
            btn = make_button(text, bg_color=color, font_size="13sp")
            btn.bind(on_press=callback)
            menu_grid.add_widget(btn)

        parent.add_widget(menu_grid)

    def on_pre_enter(self, *args) -> None:
        """Update user label and stats when entering screen."""
        app = self.get_app()
        if self.user_label:
            self.user_label.text = (
                f"Signed in as {app.current_user}" if app.current_user else ""
            )
        self.update_stats()

    def update_stats(self, *args) -> None:
        """Update statistics on dashboard. Pulls fresh data from the DB."""
        app = self.get_app()
        app.refresh_staff_list()
        app.refresh_attendance_data()

        staff_count = len(app.staff_list)
        present_count = len(
            [staff for staff in app.staff_list if app.attendance_data.get(staff["id"])]
        )
        absent_count = staff_count - present_count
        late_count = sum(
            1
            for record in app.attendance_data.values()
            if isinstance(record, dict) and record.get("late")
        )
        attendance_rate = (
            round((present_count / staff_count) * 100) if staff_count else 0
        )

        if self.staff_count_label:
            self.staff_count_label.text = f"Staff: {staff_count}"
        if self.present_label:
            self.present_label.text = f"Present: {present_count}"
        if self.absent_label:
            self.absent_label.text = f"Absent: {absent_count}"
        if self.rate_label:
            self.rate_label.text = f"Attendance rate: {attendance_rate}%"
        if self.rate_progress:
            self.rate_progress.value = attendance_rate
        if self.late_label:
            self.late_label.text = f"Late arrivals: {late_count}"
        if self.activity_label:
            if present_count:
                self.activity_label.text = (
                    f"{present_count} of {staff_count} staff recorded today."
                )
            else:
                self.activity_label.text = "No attendance recorded today."

    def handle_logout(self, instance: Any) -> None:
        """Handle logout."""
        self.get_app().current_user = None
        self.navigate_to("login")

    def go_change_info(self, instance: Any) -> None:
        """Navigate to the change information screen."""
        self.navigate_to("change_info")

    def go_register_staff(self, instance: Any) -> None:
        """Navigate to register staff screen."""
        self.navigate_to("register_staff")

    def go_view_staff(self, instance: Any) -> None:
        """Navigate to view staff screen."""
        screen = self.manager.get_screen("view_staff")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("view_staff")

    def go_attendance(self, instance: Any) -> None:
        """Navigate to attendance screen."""
        screen = self.manager.get_screen("attendance")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("attendance")

    def go_exit_attendance(self, instance: Any) -> None:
        """Navigate to the staff exit attendance screen."""
        screen = self.manager.get_screen("exit_attendance")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("exit_attendance")

    def go_view_attendance(self, instance: Any) -> None:
        """Navigate to view attendance screen."""
        screen = self.manager.get_screen("view_attendance")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("view_attendance")

    def go_absent_staff(self, instance: Any) -> None:
        """Navigate to absent staff screen."""
        screen = self.manager.get_screen("absent_staff")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("absent_staff")

    def go_report(self, instance: Any) -> None:
        """Navigate to report screen."""
        screen = self.manager.get_screen("report")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("report")

    def go_print_report(self, instance: Any) -> None:
        """Navigate to the printable report screen."""
        self.navigate_to("print_report")

    def go_activity_log(self, instance: Any) -> None:
        """Navigate to the cloud activity log screen."""
        screen = self.manager.get_screen("activity_log")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("activity_log")

    def go_delete_staff(self, instance: Any) -> None:
        """Navigate to delete staff screen."""
        if not self.require_admin():
            return
        screen = self.manager.get_screen("delete_staff")
        if hasattr(screen, "update_data"):
            screen.update_data()
        self.navigate_to("delete_staff")

    def go_pdf_report(self, instance: Any) -> None:
        """Navigate to PDF report screen."""
        if not self.require_admin():
            return
        self.navigate_to("pdf_report")


# ---------------------------------------------------------------------------
# Activity Log Screen
# ---------------------------------------------------------------------------
class ActivityLogScreen(BaseScreen):
    """Display recent cloud activity for the selected school."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.activity_container: Optional[GridLayout] = None
        self.build_ui()

    def build_ui(self) -> None:
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(8),
        )
        layout.add_widget(
            Label(
                text="Recent Activity",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(38),
            )
        )
        self.activity_container = GridLayout(
            cols=1,
            spacing=dp(6),
            size_hint_y=None,
        )
        self.activity_container.bind(
            minimum_height=self.activity_container.setter("height")
        )
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.activity_container)
        layout.add_widget(scroll)
        back_btn = make_button("Back to Dashboard", bg_color=AppColors.MUTED)
        back_btn.bind(on_press=lambda *_: self.navigate_to("dashboard"))
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def on_pre_enter(self, *args: Any) -> None:
        self.update_data()

    def update_data(self) -> None:
        if not self.activity_container:
            return
        self.activity_container.clear_widgets()
        app = self.get_app()
        if SupabaseDatabase is None or not isinstance(app.db, SupabaseDatabase):
            self._add_message("Activity logs are available in cloud mode only.")
            return
        profile = app.db.get_user(app.current_user) if app.current_user else None
        if not profile or profile.get("role") not in ("admin", "builder"):
            self._add_message(
                "Administrator or builder permission is required to view activity."
            )
            return
        try:
            activity = app.db.recent_activity()
        except Exception:
            self._add_message("Unable to load activity right now.")
            return
        if not activity:
            self._add_message("No activity has been recorded yet.")
            return
        for event in activity:
            details = event.get("details") or {}
            detail_text = json.dumps(details, sort_keys=True)
            self._add_message(
                f"{event.get('created_at', 'Unknown time')} | "
                f"{event.get('username', 'Unknown user')} | "
                f"{event.get('action', 'Unknown action')} | {detail_text}"
            )

    def _add_message(self, message: str) -> None:
        self.activity_container.add_widget(
            Label(
                text=message,
                color=AppColors.TEXT,
                halign="left",
                valign="middle",
                text_size=(None, None),
                size_hint_y=None,
                height=dp(42),
            )
        )


# ---------------------------------------------------------------------------
# Register Staff Screen
# ---------------------------------------------------------------------------
class RegisterStaffScreen(BaseScreen):
    """Screen for registering new staff members."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name_input: Optional[TextInput] = None
        self.id_input: Optional[TextInput] = None
        self.number_input: Optional[TextInput] = None
        self.department_input: Optional[TextInput] = None
        self.email_input: Optional[TextInput] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the register staff UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="Register Staff",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )

        scroll = ScrollView()
        form = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            size_hint_y=None,
        )
        form.bind(minimum_height=form.setter("height"))

        self.name_input = make_input(hint_text="Staff Name")
        form.add_widget(self.name_input)

        self.id_input = make_input(hint_text="Staff ID")
        form.add_widget(self.id_input)

        self.number_input = make_input(hint_text="Staff Number")
        form.add_widget(self.number_input)

        self.department_input = make_input(hint_text="Department")
        form.add_widget(self.department_input)

        self.email_input = make_input(hint_text="Email Address")
        form.add_widget(self.email_input)

        save_btn = make_button("Save Staff", bg_color=AppColors.SUCCESS, bold=True)
        save_btn.bind(on_press=self.save_staff)
        form.add_widget(save_btn)

        scroll.add_widget(form)
        layout.add_widget(scroll)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def on_pre_enter(self, *args) -> None:
        """Clear input fields when entering screen."""
        self.clear_text_inputs(
            self.name_input,
            self.id_input,
            self.number_input,
            self.department_input,
            self.email_input,
        )

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def save_staff(self, instance: Any) -> None:
        """Save a new staff member."""
        if not self.require_admin():
            return
        if not all(
            [
                self.name_input,
                self.id_input,
                self.number_input,
                self.department_input,
                self.email_input,
            ]
        ):
            return

        name = self.name_input.text.strip()
        staff_id = self.id_input.text.strip()
        number = self.number_input.text.strip()
        department = self.department_input.text.strip()
        email = self.email_input.text.strip().lower()

        if not all([name, staff_id, number, department, email]):
            self.show_error("Please fill all fields")
            return

        if not validate_email(email):
            self.show_error("Please enter a valid email address")
            return

        app = self.get_app()
        # add_staff enforces the unique staff_id constraint atomically.
        added = app.db.add_staff(staff_id, name, number, department, email)
        if not added:
            self.show_error(f"Staff ID {staff_id} already exists")
            return

        app.log_activity(
            "staff_registered",
            {"staff_id": staff_id, "name": name, "department": department},
        )
        app.refresh_staff_list()

        self.show_success(f"Staff {name} registered successfully")
        self.clear_text_inputs(
            self.name_input,
            self.id_input,
            self.number_input,
            self.department_input,
            self.email_input,
        )

        dashboard = self.manager.get_screen("dashboard")
        if hasattr(dashboard, "update_stats"):
            dashboard.update_stats()


# ---------------------------------------------------------------------------
# View Staff Screen
# ---------------------------------------------------------------------------
class ViewStaffScreen(BaseScreen):
    """Screen for viewing all registered staff."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.staff_container: Optional[BoxLayout] = None
        self._attendance_date = datetime.now().date()
        self.build_ui()
        Clock.schedule_interval(self._refresh_for_new_day, 30)

    def build_ui(self) -> None:
        """Build the view staff UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="View Staff",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )

        staff_list_view = ScrollView()
        self.staff_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(5),
        )
        self.staff_container.bind(minimum_height=self.staff_container.setter("height"))
        staff_list_view.add_widget(self.staff_container)
        layout.add_widget(staff_list_view)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def _refresh_for_new_day(self, *args) -> None:
        """Refresh the attendance list when the local calendar day changes."""
        current_date = datetime.now().date()
        if current_date != self._attendance_date:
            self._attendance_date = current_date
            self.update_data()

    def update_data(self) -> None:
        """Update the staff list display."""
        app = self.get_app()
        app.refresh_staff_list()
        if not self.staff_container:
            return

        self.staff_container.clear_widgets()

        if not app.staff_list:
            self.staff_container.add_widget(
                Label(
                    text="No staff registered yet",
                    color=AppColors.MUTED,
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        for staff in app.staff_list:
            row = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(80),
                padding=dp(5),
            )
            row.add_widget(
                Label(
                    text=f"Name: {staff['name']}",
                    font_size="12sp",
                    color=AppColors.TEXT,
                )
            )
            row.add_widget(
                Label(
                    text=f"ID: {staff['id']} | Dept: {staff['department']}",
                    font_size="11sp",
                    color=AppColors.MUTED,
                )
            )
            row.add_widget(
                Label(
                    text=f"Email: {staff['email']}",
                    font_size="11sp",
                    color=AppColors.MUTED,
                )
            )
            self.staff_container.add_widget(row)


# ---------------------------------------------------------------------------
# Attendance Screen
# ---------------------------------------------------------------------------
class AttendanceScreen(BaseScreen):
    """Screen for taking attendance."""

    attendance_mode = "entry"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.staff_container: Optional[BoxLayout] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the attendance UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="Take Attendance",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )

        staff_list_view = ScrollView()
        self.staff_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(5),
        )
        self.staff_container.bind(minimum_height=self.staff_container.setter("height"))
        staff_list_view.add_widget(self.staff_container)
        layout.add_widget(staff_list_view)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def update_data(self) -> None:
        """Update the attendance list display."""
        app = self.get_app()
        app.refresh_staff_list()
        app.refresh_attendance_data()
        if not self.staff_container:
            return

        self.staff_container.clear_widgets()

        if not app.staff_list:
            self.staff_container.add_widget(
                Label(
                    text="No staff registered yet",
                    color=AppColors.MUTED,
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        for staff in app.staff_list:
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(50),
                padding=dp(5),
                spacing=dp(5),
            )

            status = app.attendance_data.get(staff["id"])
            status_text = "Not recorded"
            if status and isinstance(status, dict):
                time_val = status.get("time", "N/A")
                time_str = time_val.split(" ")[1] if " " in time_val else "N/A"
                status_text = f"In: {time_str}"
                exit_time = status.get("exit_time")
                if exit_time:
                    exit_str = (
                        exit_time.split(" ")[1] if " " in exit_time else exit_time
                    )
                    status_text += f"\nOut: {exit_str}"
                if status.get("late"):
                    status_text += " (Late)"

            row.add_widget(
                Label(
                    text=staff["name"],
                    size_hint_x=0.5,
                    font_size="12sp",
                    color=AppColors.TEXT,
                )
            )
            row.add_widget(
                Label(
                    text=status_text,
                    size_hint_x=0.25,
                    font_size="10sp",
                    color=AppColors.MUTED,
                )
            )

            button_text = "Enter" if self.attendance_mode == "entry" else "Exit"
            button_color = (
                AppColors.SUCCESS
                if self.attendance_mode == "entry"
                else AppColors.WARNING
            )
            already_entered = bool(status)
            already_exited = bool(status and status.get("exit_time"))
            is_disabled = (
                already_entered
                if self.attendance_mode == "entry"
                else not already_entered or already_exited
            )
            if is_disabled:
                button_text = (
                    "Recorded" if self.attendance_mode == "entry" else "Exited"
                )
                button_color = AppColors.MUTED
            attend_btn = make_button(
                button_text,
                bg_color=button_color,
                size_hint_x=0.25,
                height=44,
                font_size="10sp",
            )
            attend_btn.disabled = is_disabled
            if not is_disabled:
                callback = (
                    self.record_entry
                    if self.attendance_mode == "entry"
                    else self.record_exit
                )
                attend_btn.bind(on_press=lambda _, sid=staff["id"]: callback(sid))
            row.add_widget(attend_btn)

            self.staff_container.add_widget(row)

    def record_entry(self, staff_id: str) -> None:
        """
        Record attendance entry for a staff member.

        Args:
            staff_id: Staff ID to record attendance for
        """
        app = self.get_app()

        try:
            result = app.db.record_entry(staff_id)
        except (ValueError, OSError) as exc:
            self.show_error(f"Attendance could not be saved: {exc}")
            return

        app.refresh_attendance_data()
        self.update_data()

        app.log_activity("attendance_entry", {"staff_id": staff_id})

        dashboard = self.manager.get_screen("dashboard")
        if hasattr(dashboard, "update_stats"):
            dashboard.update_stats()

        message = f"Recorded {result['time']} for staff ID {staff_id}"
        if result["late"]:
            message += "\nStatus: Late"
        info_popup("Attendance Recorded", message)

    def record_exit(self, staff_id: str) -> None:
        """Record the exit time for a staff member."""
        app = self.get_app()

        try:
            exit_time = app.db.record_exit(staff_id)
        except (ValueError, OSError) as exc:
            self.show_error(f"Staff exit could not be saved: {exc}")
            return

        if exit_time is None:
            self.show_error("Record the staff entry before recording an exit.")
            return

        app.refresh_attendance_data()
        self.update_data()
        app.log_activity("attendance_exit", {"staff_id": staff_id})
        info_popup(
            "Staff Exit Recorded",
            f"Recorded exit at {exit_time} for staff ID {staff_id}",
        )


class ExitAttendanceScreen(AttendanceScreen):
    """Screen for recording staff exit times."""

    attendance_mode = "exit"


# ---------------------------------------------------------------------------
# View Attendance Screen
# ---------------------------------------------------------------------------
class ViewAttendanceScreen(BaseScreen):
    """Screen for viewing attendance data."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data_container: Optional[BoxLayout] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the view attendance UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="Attendance Data",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )

        data_view = ScrollView()
        self.data_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(5),
        )
        self.data_container.bind(minimum_height=self.data_container.setter("height"))
        data_view.add_widget(self.data_container)
        layout.add_widget(data_view)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def update_data(self) -> None:
        """Update the attendance data display."""
        app = self.get_app()
        app.refresh_staff_list()
        app.refresh_attendance_data()
        if not self.data_container:
            return

        self.data_container.clear_widgets()

        if not app.attendance_data:
            self.data_container.add_widget(
                Label(
                    text="No attendance data available",
                    color=AppColors.MUTED,
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        for staff in app.staff_list:
            record = app.attendance_data.get(staff["id"])
            if record and isinstance(record, dict):
                status = "Late" if record.get("late") else "On time"
                clock_in = record.get("time", "N/A")
            else:
                status = "Absent"
                clock_in = "N/A"

            row = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(70),
                padding=dp(5),
            )
            row.add_widget(
                Label(
                    text=f"{staff['name']} (ID: {staff['id']})",
                    font_size="12sp",
                    color=AppColors.TEXT,
                )
            )
            row.add_widget(
                Label(
                    text=f"Clock-In: {clock_in}",
                    font_size="11sp",
                    color=AppColors.MUTED,
                )
            )
            row.add_widget(
                Label(
                    text=(
                        f"Clock-Out: {record.get('exit_time', 'N/A')}"
                        if record
                        else "Clock-Out: N/A"
                    ),
                    font_size="11sp",
                    color=AppColors.MUTED,
                )
            )
            row.add_widget(
                Label(
                    text=f"Status: {status}",
                    font_size="11sp",
                    color=AppColors.MUTED,
                )
            )
            self.data_container.add_widget(row)


# ---------------------------------------------------------------------------
# Absent Staff Screen
# ---------------------------------------------------------------------------
class AbsentStaffScreen(BaseScreen):
    """Screen for viewing absent staff."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.absent_container: Optional[BoxLayout] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the absent staff UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="Absent Staff",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )

        absent_view = ScrollView()
        self.absent_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(5),
        )
        self.absent_container.bind(
            minimum_height=self.absent_container.setter("height")
        )
        absent_view.add_widget(self.absent_container)
        layout.add_widget(absent_view)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def update_data(self) -> None:
        """Update the absent staff display."""
        app = self.get_app()
        app.refresh_staff_list()
        app.refresh_attendance_data()
        if not self.absent_container:
            return

        self.absent_container.clear_widgets()

        absent = [
            staff
            for staff in app.staff_list
            if not app.attendance_data.get(staff["id"])
        ]

        if not absent:
            self.absent_container.add_widget(
                Label(
                    text="No absent staff",
                    color=AppColors.MUTED,
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        for staff in absent:
            row = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(85),
                padding=dp(5),
            )
            row.add_widget(
                Label(
                    text=f"{staff['name']} (ID: {staff['id']})",
                    font_size="12sp",
                    color=AppColors.TEXT,
                )
            )
            row.add_widget(
                Label(
                    text=f"Department: {staff['department']}",
                    font_size="11sp",
                    color=AppColors.MUTED,
                )
            )
            self.absent_container.add_widget(row)


# ---------------------------------------------------------------------------
# Report Screen
# ---------------------------------------------------------------------------
class ReportScreen(BaseScreen):
    """Screen for generating attendance reports."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.report_label: Optional[Label] = None
        self.term_days_input: Optional[TextInput] = None
        self.term_start_input: Optional[TextInput] = None
        self.term_end_input: Optional[TextInput] = None
        self.term_summary_data: Optional[Dict[str, Any]] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the report UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="Attendance Report",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )

        controls = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(8),
        )
        controls.add_widget(
            Label(text="Term days:", size_hint_x=0.25, color=AppColors.TEXT)
        )
        self.term_days_input = make_input(
            hint_text="e.g. 90",
            height=44,
        )
        if self.term_days_input:
            self.term_days_input.size_hint_x = 0.3
        controls.add_widget(self.term_days_input)

        save_days_btn = make_button(
            "Save Days",
            bg_color=AppColors.PRIMARY,
            size_hint_x=0.2,
            height=44,
        )
        save_days_btn.bind(on_press=self.save_term_days)
        controls.add_widget(save_days_btn)

        term_btn = make_button(
            "Term Summary",
            bg_color=AppColors.SUCCESS,
            size_hint_x=0.3,
            height=44,
        )
        term_btn.bind(on_press=self.generate_term_summary)
        controls.add_widget(term_btn)
        layout.add_widget(controls)

        date_controls = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(8),
        )
        date_controls.add_widget(
            Label(text="Term start:", size_hint_x=0.2, color=AppColors.TEXT)
        )
        self.term_start_input = make_input(hint_text="YYYY-MM-DD", height=44)
        self.term_start_input.size_hint_x = 0.3
        date_controls.add_widget(self.term_start_input)
        date_controls.add_widget(
            Label(text="Term end:", size_hint_x=0.2, color=AppColors.TEXT)
        )
        self.term_end_input = make_input(hint_text="YYYY-MM-DD", height=44)
        self.term_end_input.size_hint_x = 0.3
        date_controls.add_widget(self.term_end_input)
        layout.add_widget(date_controls)

        export_box = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(45),
            spacing=dp(8),
        )
        json_btn = make_button(
            "Export JSON",
            bg_color=AppColors.PRIMARY,
            height=40,
            font_size="12sp",
        )
        json_btn.bind(on_press=lambda *_: self.export_term_summary("json"))
        txt_btn = make_button(
            "Export TXT",
            bg_color=AppColors.MUTED,
            height=40,
            font_size="12sp",
        )
        txt_btn.bind(on_press=lambda *_: self.export_term_summary("txt"))
        export_box.add_widget(json_btn)
        export_box.add_widget(txt_btn)
        layout.add_widget(export_box)

        self.report_label = Label(
            text="",
            font_size="12sp",
            color=AppColors.TEXT,
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        self.report_label.bind(
            width=lambda inst, w: setattr(inst, "text_size", (w, None)),
            texture_size=lambda inst, ts: setattr(inst, "height", ts[1]),
        )
        scroll = ScrollView()
        scroll.add_widget(self.report_label)
        layout.add_widget(scroll)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def on_pre_enter(self, *args) -> None:
        """Load the saved term-day setting whenever the report opens."""
        app = self.get_app()
        saved_days = app.db.get_term_days()
        if self.term_days_input:
            self.term_days_input.text = str(saved_days) if saved_days else ""
        end_date = date.today()
        start_date = end_date - timedelta(days=(saved_days or 1) - 1)
        if self.term_start_input:
            self.term_start_input.text = start_date.isoformat()
        if self.term_end_input:
            self.term_end_input.text = end_date.isoformat()
        self.term_summary_data = None

    def _read_term_days(self) -> Optional[int]:
        """Validate and return the number of school days entered by the user."""
        if not self.term_days_input:
            return None

        term_days_text = (self.term_days_input.text or "").strip()
        if not term_days_text:
            self.show_error("Enter the number of school days in the term.")
            return None

        try:
            term_days = int(term_days_text)
        except ValueError:
            self.show_error("Term days must be a whole number.")
            return None

        if term_days <= 0:
            self.show_error("Term days must be greater than zero.")
            return None
        return term_days

    def _read_term_range(self) -> Optional[Tuple[str, str]]:
        """Validate the explicit inclusive report date range."""
        if not self.term_start_input or not self.term_end_input:
            return None
        try:
            start = date.fromisoformat(self.term_start_input.text.strip())
            end = date.fromisoformat(self.term_end_input.text.strip())
        except ValueError:
            self.show_error("Term dates must use YYYY-MM-DD format.")
            return None
        if start > end:
            self.show_error("Term start date must be on or before the end date.")
            return None
        return start.isoformat(), end.isoformat()

    def save_term_days(self, instance: Any) -> None:
        """Save the term-day setting permanently in the SQLite database."""
        if not self.require_admin():
            return
        term_days = self._read_term_days()
        if term_days is None:
            return

        self.get_app().db.set_term_days(term_days)
        self.term_summary_data = None
        self.show_success(f"Term days saved: {term_days}")

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def update_data(self) -> None:
        """Update the report display."""
        app = self.get_app()
        app.refresh_staff_list()
        app.refresh_attendance_data()
        if not self.report_label:
            return

        staff_count = len(app.staff_list)
        present_count = len(
            [staff for staff in app.staff_list if app.attendance_data.get(staff["id"])]
        )
        absent_count = staff_count - present_count

        report = (
            f"Attendance Summary\n\n"
            f"Total Staff: {staff_count}\n"
            f"Present: {present_count}\n"
            f"Absent: {absent_count}\n"
        )
        if staff_count > 0:
            rate = round((present_count / staff_count) * 100, 1)
            report += f"Attendance Rate: {rate}%\n"

        report += (
            "\nUse 'Term Summary' to calculate per-staff attendance "
            "over a term (uses recorded days by default).\n"
        )
        self.report_label.text = report

    def generate_term_summary(self, instance: Any) -> None:
        """Generate term summary report for all staff, computed in SQL."""
        app = self.get_app()
        if not self.term_days_input or not self.report_label:
            return

        term_days = self._read_term_days()
        if term_days is None:
            return

        term_range = self._read_term_range()
        if term_range is None:
            return
        range_days = (
            date.fromisoformat(term_range[1]) - date.fromisoformat(term_range[0])
        ).days + 1
        if range_days != term_days:
            self.show_error(
                f"The selected date range contains {range_days} days; "
                f"enter {range_days} as term days."
            )
            return

        if self.is_admin():
            app.db.set_term_days(term_days)

        self.term_summary_data = app.db.term_summary(
            term_days, term_range[0], term_range[1]
        )
        data = self.term_summary_data

        lines = [
            f"Term Summary (term days = {term_days})",
            f"Date range: {data['start_date']} to {data['end_date']}",
            f"Generated: {data['generated_at']}",
            "",
            "Overall School Summary",
            f"Total Staff: {data['total_staff']}",
            f"Total present days across staff: {data['total_present_days']}",
            f"Overall attendance rate: {data['overall_attendance_percentage']}%",
            f"Top attendance: {data['top_staff']}",
            "",
            "Department Summary",
        ]

        for dept in data["department_summary"]:
            lines.append(
                f"{dept['department']}: {dept['total_present_days']} present days "
                f"across {dept['staff_count']} staff ({dept['attendance_percentage']}%)"
            )

        lines.extend(["", "Per Staff Attendance"])

        for row in data["staff"]:
            lines.append(
                f"{row['name']} (ID: {row['staff_id']}): "
                f"{row['days_present']}/{row['total_days']} days "
                f"({row['attendance_percentage']}%) | "
                f"Early/On time: {row['early_days']} | Late: {row['late_days']}"
            )

        self.report_label.text = "\n".join(lines)

    def export_term_summary(self, format_type: str) -> None:
        """Export the current term summary to JSON or TXT."""
        app = self.get_app()
        if not self.require_admin():
            return
        if not self.term_summary_data:
            self.generate_term_summary(None)

        if not self.term_summary_data:
            self.show_error("Generate a term summary before exporting.")
            return

        export_dir = os.path.join(app.user_data_dir, AppConstants.EXPORT_DIR)
        os.makedirs(export_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        file_name = f"term_summary_{timestamp}"
        path = os.path.join(export_dir, f"{file_name}.{format_type}")

        try:
            if format_type == "json":
                with open(path, "w", encoding="utf-8") as file:
                    json.dump(self.term_summary_data, file, indent=2)
            else:
                data = self.term_summary_data
                lines = [
                    f"{app.school_name.upper()} - TERM SUMMARY",
                    f"Generated: {data['generated_at']}",
                    f"Term days: {data['term_days']}",
                    "",
                    "OVERALL SCHOOL SUMMARY",
                    f"Total Staff: {data['total_staff']}",
                    f"Total present days across staff: {data['total_present_days']}",
                    f"Overall attendance rate: {data['overall_attendance_percentage']}%",
                    f"Top attendance: {data['top_staff']}",
                    "",
                    "DEPARTMENT SUMMARY",
                ]
                for dept in data["department_summary"]:
                    lines.append(
                        f"{dept['department']}: {dept['total_present_days']} present days "
                        f"across {dept['staff_count']} staff ({dept['attendance_percentage']}%)"
                    )
                lines.extend(["", "PER STAFF ATTENDANCE"])
                for row in data["staff"]:
                    lines.append(
                        f"{row['name']} (ID: {row['staff_id']}): "
                        f"{row['days_present']}/{row['total_days']} days "
                        f"({row['attendance_percentage']}%) | "
                        f"Early/On time: {row['early_days']} | "
                        f"Late: {row['late_days']}"
                    )
                with open(path, "w", encoding="utf-8") as file:
                    file.write("\n".join(lines))
        except OSError as exc:
            self.show_error(f"Unable to save report: {exc}")
            return

        self.report_label.text = (
            f"{self.report_label.text}\n\nReport exported to:\n{path}"
        )
        self.show_success(f"Report saved to:\n{path}")


# ---------------------------------------------------------------------------
# Delete Staff Screen
# ---------------------------------------------------------------------------
class DeleteStaffScreen(BaseScreen):
    """Screen for deleting staff members."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.delete_container: Optional[BoxLayout] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the delete staff UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="Delete Staff",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )

        delete_view = ScrollView()
        self.delete_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(5),
        )
        self.delete_container.bind(
            minimum_height=self.delete_container.setter("height")
        )
        delete_view.add_widget(self.delete_container)
        layout.add_widget(delete_view)

        btn_box = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(5),
        )

        delete_all_btn = make_button(
            "Delete All",
            bg_color=AppColors.DANGER,
            font_size="12sp",
        )
        delete_all_btn.bind(on_press=self.delete_all_staff)
        btn_box.add_widget(delete_all_btn)

        back_btn = make_button(
            "Back to Dashboard",
            bg_color=AppColors.PRIMARY,
            font_size="12sp",
        )
        back_btn.bind(on_press=lambda _: self.go_back())
        btn_box.add_widget(back_btn)

        layout.add_widget(btn_box)
        self.add_widget(layout)

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def update_data(self) -> None:
        """Update the staff list display."""
        app = self.get_app()
        app.refresh_staff_list()
        if not self.delete_container:
            return

        self.delete_container.clear_widgets()

        if not app.staff_list:
            self.delete_container.add_widget(
                Label(
                    text="No staff registered yet",
                    color=AppColors.MUTED,
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        for staff in app.staff_list:
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(50),
                padding=dp(5),
                spacing=dp(5),
            )
            row.add_widget(
                Label(
                    text=f"{staff['name']} (ID: {staff['id']})",
                    size_hint_x=0.7,
                    font_size="12sp",
                    color=AppColors.TEXT,
                )
            )

            delete_btn = make_button(
                "Delete",
                bg_color=AppColors.DANGER,
                size_hint_x=0.3,
                height=44,
                font_size="10sp",
            )
            delete_btn.bind(
                on_press=lambda _, sid=staff["id"], name=staff[
                    "name"
                ]: self.delete_staff(sid, name)
            )
            row.add_widget(delete_btn)

            self.delete_container.add_widget(row)

    def delete_staff(self, staff_id: str, name: str) -> None:
        """
        Delete a staff member by ID.

        Args:
            staff_id: Staff ID to delete
            name: Staff name for confirmation
        """
        if not self.require_admin():
            return

        def do_delete() -> None:
            app = self.get_app()
            try:
                app.db.delete_staff(staff_id)
            except Exception as exc:
                self.show_error(f"Could not delete {name}: {exc}")
                return

            app.log_activity("staff_deleted", {"staff_id": staff_id, "name": name})
            app.refresh_staff_list()
            app.refresh_attendance_data()

            dashboard = self.manager.get_screen("dashboard")
            if hasattr(dashboard, "update_stats"):
                dashboard.update_stats()
            self.update_data()
            self.show_success(f"Deleted {name}")

        confirm_popup(
            "Confirm Delete",
            f"Delete {name}?",
            do_delete,
            confirm_text="Yes, Delete",
        )

    def delete_all_staff(self, instance: Any) -> None:
        """Delete all staff members."""
        if not self.require_admin():
            return
        app = self.get_app()
        app.refresh_staff_list()
        if not app.staff_list:
            self.show_info("No staff to delete")
            return

        def do_delete_all() -> None:
            try:
                app.db.delete_all_staff()
            except Exception as exc:
                self.show_error(f"Could not delete all staff: {exc}")
                return

            app.refresh_staff_list()
            app.refresh_attendance_data()

            dashboard = self.manager.get_screen("dashboard")
            if hasattr(dashboard, "update_stats"):
                dashboard.update_stats()
            self.update_data()
            self.show_success("All staff deleted")

        confirm_popup(
            "Confirm Delete All",
            "Delete all staff? This cannot be undone.",
            do_delete_all,
            confirm_text="Yes, Delete All",
        )


# ---------------------------------------------------------------------------
# Print Report Screen
# ---------------------------------------------------------------------------
class PrintReportScreen(BaseScreen):
    """Create day, week, term, and cumulative reports in Downloads."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.selected_format = "txt"
        self.format_label: Optional[Label] = None
        self.result_label: Optional[Label] = None
        self.build_ui()

    def build_ui(self) -> None:
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))
        layout.add_widget(
            Label(
                text="Print Report",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )
        layout.add_widget(
            Label(
                text="Choose report:",
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(28),
            )
        )
        report_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        report_grid.bind(minimum_height=report_grid.setter("height"))
        report_options = [
            ("Print Report for the Day", "day"),
            ("Print Report for the Week", "week"),
            ("Print Result for the Term", "term"),
            ("Cumulative Report", "cumulative"),
        ]
        for text, report_type in report_options:
            button = make_button(text, bg_color=AppColors.PRIMARY)
            button.bind(on_press=lambda _, kind=report_type: self.choose_report(kind))
            report_grid.add_widget(button)
        layout.add_widget(report_grid)

        term_grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(50))
        for text, report_type in (
            ("First Term", "first"),
            ("Second Term", "second"),
            ("Third Term", "third"),
        ):
            button = make_button(text, bg_color=AppColors.WARNING, height=44)
            button.bind(on_press=lambda _, kind=report_type: self.choose_report(kind))
            term_grid.add_widget(button)
        layout.add_widget(term_grid)

        format_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(8)
        )
        format_row.add_widget(
            Label(text="Format:", color=AppColors.TEXT, size_hint_x=0.2)
        )
        txt_button = make_button("TXT", bg_color=AppColors.SUCCESS, height=40)
        txt_button.bind(on_press=lambda *_: self.select_format("txt"))
        pdf_button = make_button("PDF", bg_color=AppColors.MUTED, height=40)
        pdf_button.bind(on_press=lambda *_: self.select_format("pdf"))
        format_row.add_widget(txt_button)
        format_row.add_widget(pdf_button)
        layout.add_widget(format_row)

        self.format_label = Label(
            text="Selected format: TXT",
            color=AppColors.MUTED,
            size_hint_y=None,
            height=dp(25),
        )
        layout.add_widget(self.format_label)
        self.result_label = Label(
            text="Reports are saved automatically in your Downloads folder.",
            color=AppColors.MUTED,
            size_hint_y=None,
            height=dp(45),
        )
        layout.add_widget(self.result_label)
        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.navigate_to("dashboard"))
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def select_format(self, format_type: str) -> None:
        """Select TXT or PDF for the next generated report."""
        self.selected_format = format_type
        if self.format_label:
            self.format_label.text = f"Selected format: {format_type.upper()}"

    def choose_report(self, report_type: str) -> None:
        """Generate the selected report and save it to Downloads."""
        if not self.require_admin():
            return
        app = self.get_app()
        app.refresh_staff_list()
        if not app.staff_list:
            self.show_info("No staff data to print")
            return
        ranges = self._report_ranges(app)
        if report_type not in ranges:
            self.show_error("Set the term days in the Report section first.")
            return
        start_date, end_date, title = ranges[report_type]
        records = app.db.attendance_records_between(start_date, end_date)
        text = self._format_report(app.staff_list, records, start_date, end_date, title)
        self._save_report(text, report_type)

    def _report_ranges(
        self, app: "AsoloAttendanceApp"
    ) -> Dict[str, Tuple[str, str, str]]:
        """Build date ranges for day, week, and three term windows."""
        end = date.today()
        ranges = {
            "day": (end.isoformat(), end.isoformat(), "Daily Attendance Report"),
            "week": (
                (end - timedelta(days=6)).isoformat(),
                end.isoformat(),
                "Weekly Attendance Report",
            ),
        }
        term_days = app.db.get_term_days()
        if not term_days or term_days <= 0:
            return ranges
        third_start = end - timedelta(days=term_days - 1)
        second_end = third_start - timedelta(days=1)
        second_start = second_end - timedelta(days=term_days - 1)
        first_end = second_start - timedelta(days=1)
        first_start = first_end - timedelta(days=term_days - 1)

        def values(start: date, finish: date, title: str):
            return start.isoformat(), finish.isoformat(), title

        ranges.update(
            {
                "first": values(first_start, first_end, "First Term Attendance Report"),
                "second": values(
                    second_start, second_end, "Second Term Attendance Report"
                ),
                "third": values(third_start, end, "Third Term Attendance Report"),
                "term": values(third_start, end, "Term Attendance Report"),
                "cumulative": values(first_start, end, "Cumulative Attendance Report"),
            }
        )
        return ranges

    def _format_report(
        self,
        staff_list: List[Dict[str, Any]],
        records: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        title: str,
    ) -> str:
        """Format all staff and attendance records as plain text."""
        records_by_staff: Dict[str, List[Dict[str, Any]]] = {}
        for record in records:
            records_by_staff.setdefault(record["staff_id"], []).append(record)
        period_days = (
            date.fromisoformat(end_date) - date.fromisoformat(start_date)
        ).days + 1
        lines = [
            self.get_app().school_name.upper(),
            title,
            f"Period: {start_date} to {end_date}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        for staff in staff_list:
            staff_records = records_by_staff.get(staff["id"], [])
            lines.append(f"{staff['name']} (ID: {staff['id']})")
            lines.append(f"Department: {staff['department']}")
            if not staff_records:
                lines.append(f"Days present: 0/{period_days} days")
            else:
                lines.append(f"Days present: {len(staff_records)}/{period_days} days")
                for record in staff_records:
                    status = "Late" if record["is_late"] else "On time"
                    lines.append(
                        f"  {record['date']}: In {record['time_in'] or 'N/A'}; "
                        f"Out {record['time_out'] or 'N/A'}; {status}"
                    )
            lines.append("")
        return "\n".join(lines)

    def _save_report(self, text: str, report_type: str) -> None:
        """Save the report as TXT or PDF in Downloads."""
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(
            downloads, f"attendance_{report_type}_{timestamp}.{self.selected_format}"
        )
        try:
            os.makedirs(downloads, exist_ok=True)
            if self.selected_format == "txt":
                with open(path, "w", encoding="utf-8") as file:
                    file.write(text)
            elif pdf_canvas is None or A4 is None:
                self.show_error("PDF support is unavailable. Install reportlab first.")
                return
            else:
                pdf = pdf_canvas.Canvas(path, pagesize=A4)
                _, height = A4
                y = height - dp(40)
                for line in text.splitlines():
                    if y < dp(40):
                        pdf.showPage()
                        y = height - dp(40)
                    pdf.drawString(dp(40), y, line[:115])
                    y -= dp(14)
                pdf.save()
        except (OSError, ValueError) as exc:
            self.show_error(f"Unable to save report: {exc}")
            return
        if self.result_label:
            self.result_label.text = f"Saved to Downloads:\n{path}"
        self.show_success(f"Report saved to:\n{path}")


# ---------------------------------------------------------------------------
# Full Data Export Screen
# ---------------------------------------------------------------------------
class PDFReportScreen(BaseScreen):
    """Screen for exporting attendance data."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.selected_format: str = "json"
        self.filename_input: Optional[TextInput] = None
        self.directory_input: Optional[TextInput] = None
        self.result_label: Optional[Label] = None
        self.json_btn: Optional[Button] = None
        self.txt_btn: Optional[Button] = None
        self.build_ui()

    def build_ui(self) -> None:
        """Build the export UI."""
        layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(8))

        layout.add_widget(
            Label(
                text="Export Attendance Data",
                font_size="20sp",
                bold=True,
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(40),
            )
        )
        layout.add_widget(
            Label(
                text="Select file format:",
                font_size="14sp",
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(30),
            )
        )

        format_box = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10),
        )
        self.json_btn = make_button("JSON", bg_color=AppColors.SUCCESS)
        self.json_btn.bind(on_press=lambda _: self.select_format("json"))
        format_box.add_widget(self.json_btn)

        self.txt_btn = make_button("TXT", bg_color=AppColors.MUTED)
        self.txt_btn.bind(on_press=lambda _: self.select_format("txt"))
        format_box.add_widget(self.txt_btn)
        layout.add_widget(format_box)

        layout.add_widget(
            Label(
                text="File name (without extension):",
                font_size="13sp",
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(25),
            )
        )
        self.filename_input = make_input(hint_text="Enter file name")
        layout.add_widget(self.filename_input)

        layout.add_widget(
            Label(
                text="Save location:",
                font_size="13sp",
                color=AppColors.TEXT,
                size_hint_y=None,
                height=dp(25),
            )
        )
        location_box = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(45),
            spacing=dp(8),
        )
        self.directory_input = make_input(height=44)
        self.directory_input.readonly = True
        location_box.add_widget(self.directory_input)
        browse_btn = make_button(
            "Browse",
            bg_color=AppColors.PRIMARY,
            size_hint_x=None,
            height=44,
        )
        browse_btn.width = dp(110)
        browse_btn.bind(on_press=self.browse_directory)
        location_box.add_widget(browse_btn)
        layout.add_widget(location_box)

        generate_btn = make_button(
            "Generate Report",
            bg_color=AppColors.SUCCESS,
            bold=True,
        )
        generate_btn.bind(on_press=self.generate_report)
        layout.add_widget(generate_btn)

        self.result_label = Label(
            text="",
            font_size="11sp",
            color=AppColors.MUTED,
            size_hint_y=None,
            height=dp(50),
        )
        layout.add_widget(self.result_label)

        back_btn = make_button("Back to Dashboard", bg_color=AppColors.PRIMARY)
        back_btn.bind(on_press=lambda _: self.go_back())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def on_pre_enter(self, *args) -> None:
        """Set default filename when entering screen."""
        if self.filename_input:
            self.filename_input.text = (
                f'attendance_data_{datetime.now().strftime("%Y-%m-%d")}'
            )
        if self.directory_input:
            default_dir = os.path.join(
                self.get_app().user_data_dir, AppConstants.EXPORT_DIR
            )
            self.directory_input.text = default_dir
        if self.result_label:
            self.result_label.text = ""

    def browse_directory(self, instance: Any) -> None:
        """Open a folder chooser for selecting the export directory."""
        current_dir = self.directory_input.text if self.directory_input else ""
        if not current_dir or not os.path.isdir(current_dir):
            current_dir = os.path.expanduser("~")

        chooser = FileChooserListView(
            path=current_dir,
            dirselect=True,
            multiselect=False,
        )
        chooser_box = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
        )
        chooser_box.add_widget(chooser)
        button_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(45),
            spacing=dp(8),
        )
        popup = Popup(
            title="Choose Save Folder",
            content=chooser_box,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        select_btn = make_button("Select Folder", bg_color=AppColors.SUCCESS)
        select_btn.bind(on_press=lambda *_: self.select_directory(chooser, popup))
        cancel_btn = make_button("Cancel", bg_color=AppColors.MUTED)
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        button_row.add_widget(select_btn)
        button_row.add_widget(cancel_btn)
        chooser_box.add_widget(button_row)
        popup.open()

    def select_directory(self, chooser: FileChooserListView, popup: Popup) -> None:
        """Use the selected folder as the export destination."""
        selected = chooser.selection[0] if chooser.selection else chooser.path
        if not os.path.isdir(selected):
            self.show_error("Please select a folder.")
            return

        if self.directory_input:
            self.directory_input.text = os.path.abspath(selected)
        popup.dismiss()

    def go_back(self) -> None:
        """Navigate back to dashboard."""
        self.navigate_to("dashboard")

    def select_format(self, format_type: str) -> None:
        """
        Select the export format.

        Args:
            format_type: 'json' or 'txt'
        """
        self.selected_format = format_type

        # Update button colors
        json_color = AppColors.SUCCESS if format_type == "json" else AppColors.MUTED
        txt_color = AppColors.SUCCESS if format_type == "txt" else AppColors.MUTED

        self._update_button_color(self.json_btn, json_color)
        self._update_button_color(self.txt_btn, txt_color)

    @staticmethod
    def _update_button_color(
        btn: Optional[Button], color: Tuple[float, float, float, float]
    ) -> None:
        """Update a button's background color."""
        if not btn:
            return

        btn.canvas.before.clear()
        with btn.canvas.before:
            Color(*color)
            btn._bg_rect = RoundedRectangle(
                pos=btn.pos,
                size=btn.size,
                radius=[dp(10)],
            )

    def generate_report(self, instance: Any) -> None:
        """Generate and export the report."""
        if not self.require_admin():
            return
        app = self.get_app()
        app.refresh_staff_list()
        app.refresh_attendance_data()

        if not app.staff_list:
            self.show_info("No staff data to export")
            return

        if not self.filename_input:
            return

        default_name = f'attendance_data_{datetime.now().strftime("%Y-%m-%d")}'
        raw_name = self.filename_input.text.strip() or default_name

        # Strip path traversal and characters invalid in filenames on
        # Windows/macOS/Linux so a stray ":" or "?" doesn't crash the save.
        safe_name = os.path.basename(raw_name).replace("..", "")
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", safe_name) or default_name

        export_dir = (
            self.directory_input.text.strip()
            if self.directory_input and self.directory_input.text.strip()
            else os.path.join(app.user_data_dir, AppConstants.EXPORT_DIR)
        )
        try:
            os.makedirs(export_dir, exist_ok=True)
            if self.selected_format == "json":
                filepath = os.path.join(export_dir, f"{safe_name}.json")
                with open(filepath, "w", encoding="utf-8") as file:
                    json.dump(
                        {
                            "staff_list": app.staff_list,
                            "attendance_today": app.attendance_data,
                            "attendance_records": app.db.all_attendance_records(),
                            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        },
                        file,
                        indent=2,
                    )
            else:
                filepath = os.path.join(export_dir, f"{safe_name}.txt")
                with open(filepath, "w", encoding="utf-8") as file:
                    file.write(self._format_data_as_text(app))
        except OSError as exc:
            self.show_error(f"Failed to save: {exc}")
            return

        if self.result_label:
            self.result_label.text = f"Saved to:\n{filepath}"
        self.show_success(f"Report saved to:\n{filepath}")

    @staticmethod
    def _format_data_as_text(app: "AsoloAttendanceApp") -> str:
        """
        Format today's attendance data as text.

        Args:
            app: Application instance

        Returns:
            Formatted text
        """
        lines = [
            "=" * 60,
            f"{app.school_name.upper()} - ATTENDANCE REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
        ]

        if not app.staff_list:
            lines.append("No staff registered.")
            return "\n".join(lines)

        for staff in app.staff_list:
            record = app.attendance_data.get(staff["id"])
            if record and isinstance(record, dict):
                clock_in = record.get("time", "N/A")
                clock_out = record.get("exit_time", "N/A")
                status = "LATE" if record.get("late") else "On time"
            else:
                clock_in = "N/A"
                clock_out = "N/A"
                status = "ABSENT"

            lines.append(
                f"Staff ID: {staff['id']} | Name: {staff['name']} | "
                f"Dept: {staff['department']} | Clock-In: {clock_in} | "
                f"Clock-Out: {clock_out} | Status: {status}"
            )

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"Total Staff: {len(app.staff_list)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Application Class
# ---------------------------------------------------------------------------
class AsoloAttendanceApp(App):
    """Main application class for the Asolo attendance system."""

    title = f"{AppConstants.APP_TITLE} v{AppConstants.APP_VERSION}"

    __version__ = AppConstants.APP_VERSION

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db: Optional[Any] = None
        self.shutdown_requested = False
        self.school_ids: List[str] = []
        self.active_school_id = ""
        self.selected_timezone = "Africa/Kampala"
        # In-memory caches, refreshed from the DB via refresh_staff_list()/
        # refresh_attendance_data() so screens can keep iterating over
        # plain lists/dicts without every read hitting SQLite directly.
        self.staff_list: List[Dict[str, Any]] = []
        self.attendance_data: Dict[str, Dict[str, Any]] = {}
        self.current_user: Optional[str] = None
        self.school_name = ""
        self.branding_logo_path = ""
        self.update_notice_shown = False

    def build(self) -> ScreenManager:
        """Build the application UI."""
        self.load_branding()
        cloud_config = self._read_cloud_config()
        supabase_url = cloud_config["url"]
        supabase_key = cloud_config["anon_key"]
        self.school_ids = cloud_config["school_ids"]
        self.active_school_id = self.school_ids[0] if self.school_ids else ""
        if supabase_url and supabase_key and self.active_school_id:
            if SupabaseDatabase is None:
                raise RuntimeError("Install the 'supabase' package for cloud mode.")
            self.db = SupabaseDatabase(
                supabase_url, supabase_key, self.active_school_id
            )
        else:
            db_path = self._prepare_database_path()
            self.db = Database(db_path)
        self.refresh_staff_list()
        self.refresh_attendance_data()
        self._set_window_icon()

        screen_manager = ScreenManager()
        screen_manager.add_widget(BrandingSetupScreen(name="setup"))
        screen_manager.add_widget(LoginScreen(name="login"))
        screen_manager.add_widget(RegisterScreen(name="register"))
        screen_manager.add_widget(ChangeInfoScreen(name="change_info"))
        screen_manager.add_widget(DashboardScreen(name="dashboard"))
        screen_manager.add_widget(ActivityLogScreen(name="activity_log"))
        screen_manager.add_widget(RegisterStaffScreen(name="register_staff"))
        screen_manager.add_widget(ViewStaffScreen(name="view_staff"))
        screen_manager.add_widget(AttendanceScreen(name="attendance"))
        screen_manager.add_widget(ExitAttendanceScreen(name="exit_attendance"))
        screen_manager.add_widget(ViewAttendanceScreen(name="view_attendance"))
        screen_manager.add_widget(AbsentStaffScreen(name="absent_staff"))
        screen_manager.add_widget(ReportScreen(name="report"))
        screen_manager.add_widget(DeleteStaffScreen(name="delete_staff"))
        screen_manager.add_widget(PrintReportScreen(name="print_report"))
        screen_manager.add_widget(PDFReportScreen(name="pdf_report"))

        Clock.schedule_once(self.check_remote_status, 0.5)
        Clock.schedule_interval(self.check_remote_status, 60)
        Clock.schedule_once(self.check_for_updates, 2)

        screen_manager.current = "login" if self.has_branding() else "setup"

        return screen_manager

    def check_for_updates(self, *args: Any) -> None:
        """Check GitHub for a newer release without delaying app startup."""
        repository = os.environ.get(
            "ASOLO_RELEASE_REPOSITORY", AppConstants.RELEASE_REPOSITORY
        ).strip()
        if not repository or self.update_notice_shown:
            return

        threading.Thread(
            target=self._fetch_latest_release,
            args=(repository,),
            daemon=True,
        ).start()

    def _fetch_latest_release(self, repository: str) -> None:
        """Fetch the latest public GitHub release and return to the UI thread."""
        api_url = f"https://api.github.com/repos/{repository}/releases/latest"
        request = urllib.request.Request(
            api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "AsoloAttendanceUpdateChecker",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                release = json.loads(response.read().decode("utf-8"))
            tag_name = str(release.get("tag_name", "")).lstrip("vV")
            release_url = str(release.get("html_url", "")).strip()
            if (
                self._is_newer_version(tag_name, AppConstants.APP_VERSION)
                and release_url
            ):
                Clock.schedule_once(
                    partial(self._show_update_notice, tag_name, release_url)
                )
        except (OSError, ValueError, json.JSONDecodeError):
            return

    @staticmethod
    def _is_newer_version(candidate: str, current: str) -> bool:
        """Compare dotted numeric versions while ignoring prerelease suffixes."""

        def parts(version: str) -> Tuple[int, ...]:
            numbers = re.findall(r"\d+", version)
            return tuple(int(number) for number in numbers) or (0,)

        return parts(candidate) > parts(current)

    def _show_update_notice(
        self, latest_version: str, release_url: str, *_args: Any
    ) -> None:
        """Tell the user about a release once and provide its download page."""
        if self.update_notice_shown:
            return
        self.update_notice_shown = True
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))
        message = Label(
            text=(
                f"A newer version ({latest_version}) is available.\n"
                f"You are using version {AppConstants.APP_VERSION}."
            ),
            color=AppColors.TEXT,
            halign="center",
            valign="middle",
        )
        message.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        content.add_widget(message)
        actions = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(46))
        download_btn = make_button(
            "Download update", bg_color=AppColors.SUCCESS, bold=True
        )
        later_btn = make_button("Later", bg_color=AppColors.MUTED)
        actions.add_widget(download_btn)
        actions.add_widget(later_btn)
        content.add_widget(actions)
        popup = Popup(
            title="Update available",
            content=content,
            size_hint=(0.78, None),
            height=dp(210),
            auto_dismiss=False,
        )
        download_btn.bind(
            on_press=lambda *_: (webbrowser.open(release_url), popup.dismiss())
        )
        later_btn.bind(on_press=popup.dismiss)
        popup.open()

    def has_branding(self) -> bool:
        """Return whether both required school branding values are configured."""
        return bool(self.school_name.strip() and self.branding_logo_path)

    def load_branding(self) -> None:
        """Load school branding saved in the app's user data directory."""
        branding_path = os.path.join(self.user_data_dir, "school_branding.json")
        try:
            with open(branding_path, "r", encoding="utf-8") as file:
                branding = json.load(file)
            school_name = str(branding.get("school_name", "")).strip()
            logo_path = str(branding.get("logo_path", "")).strip()
            if school_name and os.path.isfile(logo_path):
                self.school_name = school_name
                self.branding_logo_path = logo_path
        except (OSError, json.JSONDecodeError, AttributeError):
            self.school_name = ""
            self.branding_logo_path = ""

    def save_branding(self, school_name: str, logo_source: str) -> bool:
        """Copy the selected logo and persist the school branding."""
        branding_dir = self.user_data_dir
        branding_path = os.path.join(branding_dir, "school_branding.json")
        logo_extension = os.path.splitext(logo_source)[1].lower()
        if logo_extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            return False
        try:
            os.makedirs(branding_dir, exist_ok=True)
            logo_path = os.path.join(branding_dir, f"school_logo{logo_extension}")
            shutil.copy2(logo_source, logo_path)
            with open(branding_path, "w", encoding="utf-8") as file:
                json.dump(
                    {"school_name": school_name.strip(), "logo_path": logo_path},
                    file,
                    indent=2,
                )
        except OSError:
            return False
        self.school_name = school_name.strip()
        self.branding_logo_path = logo_path
        return True

    def refresh_branding_screens(self) -> None:
        """Rebuild the login screen after branding setup is completed."""
        if not self.root:
            return
        login = self.root.get_screen("login")
        login.clear_widgets()
        login.build_ui()

    def check_remote_status(self, *args: Any) -> None:
        """Close cloud-connected copies when the builder disables the app."""
        if (
            self.shutdown_requested
            or SupabaseDatabase is None
            or not isinstance(self.db, SupabaseDatabase)
        ):
            return
        status = self.db.get_app_status()
        if not status or status.get("enabled", True):
            return

        self.shutdown_requested = True
        message = str(
            status.get(
                "message",
                "This application has been disabled by the administrator.",
            )
        )
        info_popup("Application Disabled", message)
        Clock.schedule_once(lambda _dt: self.stop(), 2)

    @staticmethod
    def _read_cloud_config() -> Dict[str, str]:
        """Read cloud settings from environment variables or a sidecar file."""
        configured_school_ids = [
            school_id.strip()
            for school_id in os.environ.get("ASOLO_SCHOOL_IDS", "").split(",")
            if school_id.strip()
        ]
        legacy_school_id = os.environ.get("ASOLO_SCHOOL_ID", "").strip()
        if legacy_school_id and legacy_school_id not in configured_school_ids:
            configured_school_ids.insert(0, legacy_school_id)
        config = {
            "url": os.environ.get("ASOLO_SUPABASE_URL", "").strip(),
            "anon_key": os.environ.get("ASOLO_SUPABASE_ANON_KEY", "").strip(),
            "school_ids": configured_school_ids,
        }
        if config["url"] and config["anon_key"] and config["school_ids"]:
            return config

        config_paths = [
            os.path.join(
                os.path.dirname(os.path.abspath(sys.executable)), "asolo_config.json"
            ),
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "asolo_config.json"
            ),
        ]
        for config_path in config_paths:
            if not os.path.isfile(config_path):
                continue
            try:
                with open(config_path, "r", encoding="utf-8") as file:
                    file_config = json.load(file)
                config["url"] = (
                    config["url"] or str(file_config.get("supabase_url", "")).strip()
                )
                config["anon_key"] = (
                    config["anon_key"]
                    or str(file_config.get("supabase_anon_key", "")).strip()
                )
                file_school_ids = file_config.get("school_ids", [])
                if not isinstance(file_school_ids, list):
                    file_school_ids = []
                config["school_ids"] = config["school_ids"] or [
                    str(school_id).strip()
                    for school_id in file_school_ids
                    if str(school_id).strip()
                ]
                legacy_school_id = str(file_config.get("school_id", "")).strip()
                if legacy_school_id and legacy_school_id not in config["school_ids"]:
                    config["school_ids"].insert(0, legacy_school_id)
            except (OSError, json.JSONDecodeError):
                continue
            break
        return config

    def select_school(self, school_id: str) -> bool:
        """Select an authorized cloud school and refresh its data."""
        if school_id not in self.school_ids or not isinstance(
            self.db, SupabaseDatabase
        ):
            return False
        if self.current_user and not self.db.switch_school(
            school_id, self.current_user
        ):
            return False
        self.active_school_id = school_id
        self.log_activity("school_selected", {"school_id": school_id})
        return True

    def log_activity(
        self, action: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Write a cloud audit event for the signed-in user."""
        if (
            SupabaseDatabase is not None
            and isinstance(self.db, SupabaseDatabase)
            and self.current_user
        ):
            self.db.log_event(self.current_user, action, details)

    def _prepare_database_path(self) -> str:
        """Choose a persistent database path and migrate an older local copy."""
        data_dir = os.path.join(os.path.expanduser("~"), "AsoloAttendanceApp")
        os.makedirs(data_dir, exist_ok=True)
        database_path = os.path.join(data_dir, DB_FILENAME)

        if os.path.exists(database_path):
            return database_path

        legacy_paths = [
            os.path.join(self.user_data_dir, DB_FILENAME),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME),
        ]
        for legacy_path in legacy_paths:
            if not os.path.isfile(legacy_path):
                continue
            if os.path.abspath(legacy_path) == os.path.abspath(database_path):
                return database_path
            shutil.copy2(legacy_path, database_path)
            break

        return database_path

    def _set_window_icon(self) -> None:
        """Set the window icon from logo file."""
        logo_path = get_logo_path()
        if os.path.exists(logo_path):
            try:
                self.icon = logo_path
            except Exception:
                pass

    def refresh_staff_list(self) -> None:
        """Reload the in-memory staff cache from the database."""
        if self.db:
            self.staff_list = self.db.list_staff()

    def refresh_attendance_data(self) -> None:
        """Reload today's in-memory attendance cache from the database."""
        if self.db:
            self.attendance_data = self.db.get_today_attendance()


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    """Start the attendance application."""
    AsoloAttendanceApp().run()


if __name__ == "__main__":
    main()
