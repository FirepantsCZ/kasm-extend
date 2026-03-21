from datetime import datetime, UTC
from os import getenv

from dotenv import load_dotenv

from kasmapi.exceptions import UsageQuotaReachedError
from kasmapi.kasm import Kasm

DEFAULT_HOURS = 6

load_dotenv()

BASE_URL = "https://kasm.krabice.online"  # e.g. https://kasm.example.com
API_KEY = getenv("API_KEY")
API_KEY_SECRET = getenv("API_KEY_SECRET")


def main() -> None:
    if BASE_URL and API_KEY and API_KEY_SECRET:
        kasm = Kasm(BASE_URL, API_KEY, API_KEY_SECRET)
    else:
        print("Incorrect API configuration.")
        return

    # Fetch sessions
    sessions = kasm.get_sessions()

    if not sessions:
        print("No active or paused sessions found.")
        return

    # Display list
    print("\nAvailable sessions:")
    for i, s in enumerate(sessions, 1):
        exp_date = datetime.strptime(s.expiration_date, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=UTC).astimezone()
        exp_eta = int((exp_date - datetime.now().astimezone()).total_seconds())

        start_date_str = datetime.strptime(s.start_date, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        exp_date_str = exp_date.strftime("%Y-%m-%d %H:%M:%S")
        exp_eta_str = f"{exp_eta // 3600:02}:{exp_eta % 3600 // 60:02}:{exp_eta % 60:02}"
        print(
            f"[{i}] {start_date_str} - {s.image.friendly_name} (state: {s.operational_status}, expiration: {exp_date_str} ({exp_eta_str} remaining))",
        )

    choice = input("\nSelect session to extend (number)[1]: ")
    session = sessions[int(choice) - 1 if choice else 0]

    # Get the user of the chosen session
    user_group = next(session.user.groups)

    # Fetch default session expiration time
    keepalive_setting = user_group.get_setting("keepalive_expiration")

    if not keepalive_setting:
        print("ERROR: Could not find keepalive_expiration setting.")
        return

    old_keepalive = keepalive_setting.value

    # Ask how many hours to extend
    while extra_hours := input(f"\nNew expiration time (in hours)[{DEFAULT_HOURS}]: "):
        try:
            extra_hours = float(extra_hours)
            break
        except ValueError:
            print("ERROR: Invalid input. Please enter a number.")

    keepalive_setting.set_value(
        int((extra_hours if extra_hours else DEFAULT_HOURS) * 60 * 60),
    )

    # Reset keepalive for session
    try:
        session.keepalive()
    except UsageQuotaReachedError:
        print("ERROR: Session not modified, usage quota reached!")
        keepalive_setting.set_value(old_keepalive)
        return

    keepalive_setting.set_value(old_keepalive)

    print("\n✅ Session expiration updated successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        exit()
