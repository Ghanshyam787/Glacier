"""
Glacier - text / voice terminal mode.
  python main.py            -> keyboard se baat
  python main.py --voice    -> mic se baat (har baar Enter dabao, ya --wake se hamesha sunta rahe)
  python main.py --doctor   -> health check
"""

import sys

import brain
import config
import services
import voice


def main():
    if "--doctor" in sys.argv:
        import doctor
        sys.exit(doctor.main())
    if not services.acquire_single_instance():
        print("Glacier pehle se chal raha hai (tray / background mein). Wo band karke dobara chalao.")
        return
    use_voice = "--voice" in sys.argv

    def on_wake(text):
        reply = brain.ask_glacier(text)
        print(f"\n{config.ASSISTANT_NAME}: {reply}\n")
        voice.speak_if_enabled(reply)

    services.start_all(on_wake_command=on_wake if use_voice else None)
    print(f"{config.ASSISTANT_NAME} ready. ('exit' likho band karne ke liye, 'reset' = nayi baat-cheet)")
    if not config.has_api_key():
        print("NOTE: GEMINI_API_KEY .env mein nahi hai - python doctor.py chalao.")
    while True:
        try:
            if use_voice:
                input("[Enter dabao aur bolo] ")
                text = voice.listen()
                if not text:
                    print("(kuchh sunai nahi diya)")
                    continue
                print(f"You (voice): {text}")
            else:
                text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("exit", "quit", "bye"):
            break
        if text.lower() == "reset":
            brain.reset_session("local")
            print("Nayi baat-cheet.")
            continue
        reply = brain.ask_glacier(text)
        print(f"\n{config.ASSISTANT_NAME}: {reply}\n")
        voice.speak_if_enabled(reply)
    voice.stop_speaking()


if __name__ == "__main__":
    main()
